import os
import re
import json
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = FastAPI()

client = OpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
)

PROMPT_PATH = Path(__file__).parent / "prompts" / "enrich-v1.md"
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")
PROMPT_VERSION = "enrich-v1"

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
QUARANTINE_PATH = LOG_DIR / "quarantine.jsonl"


#  Input schema 
class EnrichRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(default="", max_length=2000)


# Output schema 
class Category(str, Enum):
    # fiction = "fiction"
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


def build_user_message(payload: EnrichRequest) -> str:
    return json.dumps({"title": payload.title, "description": payload.description})


def call_model(system_prompt: str, user_content: str) -> str:
    response = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    return response.choices[0].message.content


def extract_json(raw_text: str) -> Optional[dict]:
    """Strip code fences / stray text and try to find a JSON object."""
    text = raw_text.strip()
    # Strip ```json ... ``` or ``` ... ``` fences if present
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)

    # Find the first { ... last } as a fallback if there's stray text around it
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
    """Returns (response, None) on success, or (None, error_message) on failure."""
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

    user_content = build_user_message(payload)

    # First attempt
    raw_text = call_model(SYSTEM_PROMPT, user_content)
    result, error = parse_and_validate(raw_text)
    if result is not None:
        return result

    # Repair retry: give the model its own broken output + the error, ask once more
    repair_user_content = (
        f"{user_content}\n\n"
        f"Your previous answer was rejected for this reason: {error}\n"
        f"Your previous answer was: {raw_text}\n"
        f"Return only corrected JSON matching the schema."
    )
    raw_text_2 = call_model(SYSTEM_PROMPT, repair_user_content)
    result_2, error_2 = parse_and_validate(raw_text_2)
    if result_2 is not None:
        return result_2

    # Give up cleanly
    quarantine(payload, raw_text_2, error_2 or "unknown error after repair attempt")
    raise HTTPException(
        status_code=422,
        detail="Model output could not be validated after one repair attempt. See logs/quarantine.jsonl.",
    )