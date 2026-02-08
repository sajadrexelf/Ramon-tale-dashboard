from __future__ import annotations

from pydantic import BaseModel, Field

from services.content_generator import ContentType


class ContentGenerationRequest(BaseModel):
    headline: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=4000)
    key_facts: list[str] = Field(min_length=1, max_length=12)
    content_type: ContentType


class ContentGenerationResponse(BaseModel):
    lead: str
    body: str
    analysis: str
    cta: str
