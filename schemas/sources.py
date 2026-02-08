from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class SourceCreateRequest(BaseModel):
    url: HttpUrl
    name: str | None = Field(default=None, max_length=120)


class SourceResponse(BaseModel):
    id: str
    url: HttpUrl
    name: str | None = None
