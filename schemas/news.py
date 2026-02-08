from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class FetchNewsRequest(BaseModel):
    source_urls: list[HttpUrl] = Field(min_length=1)
    limit: int = Field(default=20, ge=1, le=100)


class ArticleResponse(BaseModel):
    url: HttpUrl
    title: str
    published_at: datetime | None = None


class FetchNewsResponse(BaseModel):
    articles: list[ArticleResponse]
