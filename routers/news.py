from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException

from schemas.news import ArticleResponse, FetchNewsRequest, FetchNewsResponse
from services.rss_fetcher import RSSFetcherService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["news"])


@router.post("/fetch-news", response_model=FetchNewsResponse)
async def fetch_news(payload: FetchNewsRequest) -> FetchNewsResponse:
    service = RSSFetcherService()
    tasks = [service.fetch_latest(str(url), limit=payload.limit) for url in payload.source_urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    articles: list[ArticleResponse] = []
    for url, result in zip(payload.source_urls, results, strict=False):
        if isinstance(result, Exception):
            logger.warning("Failed to fetch RSS feed %s: %s", url, result)
            continue
        for item in result:
            articles.append(
                ArticleResponse(
                    url=item.url,
                    title=item.title,
                    published_at=item.published_at,
                )
            )

    if not articles:
        raise HTTPException(status_code=502, detail="Unable to fetch news from sources.")

    return FetchNewsResponse(articles=articles)
