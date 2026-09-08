import os
from enum import Enum
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()


#Input schema
class EnrichRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(default="", max_length=2000)


#Output schema (closed lists as enums) 
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


#Stub mode 
def get_stub_response() -> EnrichResponse:
    return EnrichResponse(
        category=Category.other,
        summary="This is a stub response for local development.",
        quality_flags=[],
    )


@app.post("/enrich", response_model=EnrichResponse)
def enrich(payload: EnrichRequest):
    if os.getenv("LLM_STUB") == "1":
        return get_stub_response()

    # Stage 2 will add the real model call here.
    raise HTTPException(status_code=501, detail="Real model call not implemented yet")