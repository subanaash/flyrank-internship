import os
import json
from enum import Enum
from typing import List
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
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


# ---- Input schema ----
class EnrichRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(default="", max_length=2000)


# ---- Output schema (closed lists as enums) ----
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


def call_model(payload: EnrichRequest) -> str:
    user_content = json.dumps({
        "title": payload.title,
        "description": payload.description,
    })

    response = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    return response.choices[0].message.content


@app.post("/enrich", response_model=EnrichResponse)
def enrich(payload: EnrichRequest):
    if os.getenv("LLM_STUB") == "1":
        return get_stub_response()

    raw_text = call_model(payload)
    print("RAW MODEL OUTPUT:", raw_text)

    # Stage 3 will add proper parsing, validation, and repair here.
    # For now, just try a naive parse so we can see it work end to end.
    try:
        data = json.loads(raw_text)
        return EnrichResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Model returned unparseable output: {e}")