import os
import re
import json
import time
import random
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv
from openai import OpenAI, APITimeoutError, APIStatusError

load_dotenv()

app = FastAPI()

client = OpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
    timeout=30.0,      # real timeout — SDK default is 10 minutes, that's not a real timeout
    max_retries=0,     # we handle retries ourselves, explicitly, below
)

PROMPT_PATH = Path(__file__).parent / "prompts" / "enrich-v1.md"
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")
PROMPT_VERSION = "enrich-v1"

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
QUARANTINE_PATH = LOG_DIR / "quarantine.jsonl"
COST_LOG_PATH = LOG_DIR / "cost.jsonl"

MAX_RETRIES = 2  # retry attempts for timeout/429/5xx only


# ---- Input schema ----
class EnrichRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(default="", max_length=2000)


# ---- Output schema ----
class Category(str, Enum):
    fiction = "fiction"
    non_fiction = "non-fiction"
    poetry = "poetry"
    children = "children"
    biography = "biography"
    other = "other"


class QualityFlag(str, Enum):
    missing_description = "missing_description"
    very_short_description = "very_short_description"
    title_looks_truncated = "title_looks_truncated"


class EnrichResponse(BaseModel):
    category: Category
    summary: str = Field(..., max_length=200)
    quality_flags: List[QualityFlag] = []


def get_stub_response() -> EnrichResponse:
    return EnrichResponse(
        category=Category.other,
        summary="This is a stub response for local development.",
        quality_flags=[],
    )


def get_fallback_response() -> EnrichResponse:
    """Used when LLM_ENABLED=false — a safe, deterministic non-answer."""
    return EnrichResponse(
        category=Category.other,
        summary="Enrichment is currently disabled.",
        quality_flags=[],
    )


def build_user_message(payload: EnrichRequest) -> str:
    return json.dumps({"title": payload.title, "description": payload.description})


def log_cost(prompt_version: str, model: str, usage, duration_ms: float, needed_repair: bool):
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prompt_version": prompt_version,
        "model": model,
        "input_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
        "output_tokens": getattr(usage, "completion_tokens", None) if usage else None,
        "duration_ms": round(duration_ms, 1),
        "needed_repair": needed_repair,
    }
    with open(COST_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print("COST LOG:", entry)


def call_model_with_retries(system_prompt: str, user_content: str):
    """Calls the model with retries on timeout/429/5xx only, backoff+jitter.
    Never retries 400/401/403. Returns (raw_text, usage, duration_ms)."""
    attempt = 0
    while True:
        start = time.monotonic()
        try:
            response = client.chat.completions.create(
                model=os.environ["LLM_MODEL"],
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
            duration_ms = (time.monotonic() - start) * 1000
            return response.choices[0].message.content, response.usage, duration_ms

        except APITimeoutError:
            duration_ms = (time.monotonic() - start) * 1000
            attempt += 1
            if attempt > MAX_RETRIES:
                raise HTTPException(status_code=504, detail="Model call timed out after retries")
            _sleep_with_backoff(attempt)

        except APIStatusError as e:
            duration_ms = (time.monotonic() - start) * 1000
            status = e.status_code
            if status in (400, 401, 403):
                # Never retry these — a bad key or bad request stays bad
                raise HTTPException(status_code=502, detail=f"Model provider error ({status}), not retrying")
            if status == 429 or 500 <= status < 600:
                attempt += 1
                if attempt > MAX_RETRIES:
                    raise HTTPException(status_code=502, detail=f"Model provider error ({status}) after retries")
                retry_after = getattr(e.response, "headers", {}).get("Retry-After") if hasattr(e, "response") else None
                if retry_after:
                    time.sleep(float(retry_after))
                else:
                    _sleep_with_backoff(attempt)
            else:
                raise HTTPException(status_code=502, detail=f"Model provider error ({status})")


def _sleep_with_backoff(attempt: int):
    base = 2 ** (attempt - 1)  # 1s, 2s, 4s
    jitter = random.uniform(0, 0.5)
    time.sleep(base + jitter)


def extract_json(raw_text: str) -> Optional[dict]:
    text = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        text = brace_match.group(0)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def quarantine(payload: EnrichRequest, raw_text: str, error: str):
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prompt_version": PROMPT_VERSION,
        "input": payload.model_dump(),
        "raw_output": raw_text,
        "error": error,
    }
    with open(QUARANTINE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def parse_and_validate(raw_text: str) -> tuple[Optional[EnrichResponse], Optional[str]]:
    data = extract_json(raw_text)
    if data is None:
        return None, "Could not find valid JSON in model output"
    try:
        return EnrichResponse(**data), None
    except ValidationError as e:
        return None, str(e)


@app.post("/enrich", response_model=EnrichResponse)
def enrich(payload: EnrichRequest):
    if os.getenv("LLM_STUB") == "1":
        return get_stub_response()

    if os.getenv("LLM_ENABLED", "true").lower() == "false":
        return get_fallback_response()

    user_content = build_user_message(payload)

    # First attempt
    raw_text, usage, duration_ms = call_model_with_retries(SYSTEM_PROMPT, user_content)
    result, error = parse_and_validate(raw_text)
    if result is not None:
        log_cost(PROMPT_VERSION, os.environ["LLM_MODEL"], usage, duration_ms, needed_repair=False)
        return result

    # Repair retry
    repair_user_content = (
        f"{user_content}\n\n"
        f"Your previous answer was rejected for this reason: {error}\n"
        f"Your previous answer was: {raw_text}\n"
        f"Return only corrected JSON matching the schema."
    )
    raw_text_2, usage_2, duration_ms_2 = call_model_with_retries(SYSTEM_PROMPT, repair_user_content)
    result_2, error_2 = parse_and_validate(raw_text_2)
    if result_2 is not None:
        log_cost(PROMPT_VERSION, os.environ["LLM_MODEL"], usage_2, duration_ms_2, needed_repair=True)
        return result_2

    quarantine(payload, raw_text_2, error_2 or "unknown error after repair attempt")
    raise HTTPException(
        status_code=422,
        detail="Model output could not be validated after one repair attempt. See logs/quarantine.jsonl.",
    )