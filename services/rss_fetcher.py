from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import httpx

logger = logging.getLogger(__name__)


class RSSFetchError(RuntimeError):
    """Raised when an RSS feed cannot be fetched or parsed."""


def _parse_published(entry: dict[str, Any]) -> datetime | None:
    published = entry.get("published") or entry.get("updated")
    if not published:
        return None
    try:
        return parsedate_to_datetime(published)
    except (TypeError, ValueError):
        logger.debug("Unable to parse published date: %s", published)
        return None


@dataclass(frozen=True)
class RSSArticle:
    url: str
    title: str
    published_at: datetime | None


class RSSFetcherService:
    """Fetch RSS feed entries and return normalized article metadata."""

    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout = timeout

    async def fetch_latest(self, feed_url: str, limit: int = 20) -> list[RSSArticle]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(feed_url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RSSFetchError(f"Failed to fetch RSS feed: {feed_url}") from exc

        feed = feedparser.parse(response.text)
        if feed.bozo:
            raise RSSFetchError(f"Invalid RSS feed: {feed_url}")

        articles: list[RSSArticle] = []
        for entry in feed.entries[:limit]:
            url = entry.get("link")
            title = entry.get("title")
            if not url or not title:
                continue
            articles.append(
                RSSArticle(
                    url=url,
                    title=title,
                    published_at=_parse_published(entry),
                )
            )

        return articles
