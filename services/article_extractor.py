from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx
from readability import Document
from lxml import html
from lxml.etree import ParserError

logger = logging.getLogger(__name__)


class ArticleExtractionError(RuntimeError):
    """Raised when an article cannot be fetched or parsed."""


@dataclass(frozen=True)
class ArticleContent:
    url: str
    title: str
    text: str


class ArticleExtractorService:
    """Extract clean text content from an article URL."""

    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout = timeout

    async def extract(self, url: str) -> ArticleContent:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ArticleExtractionError(f"Failed to fetch article: {url}") from exc

        try:
            document = Document(response.text)
            summary_html = document.summary(html_partial=True)
            title = document.short_title()
            parsed = html.fromstring(summary_html)
            for element in parsed.xpath("//script|//style"):
                parent = element.getparent()
                if parent is not None:
                    parent.remove(element)
            text = parsed.text_content()
        except (ValueError, TypeError, ParserError) as exc:
            raise ArticleExtractionError(f"Failed to extract content: {url}") from exc

        clean_text = re.sub(r"\s+", " ", text).strip()
        if not clean_text:
            raise ArticleExtractionError(f"Empty article content extracted: {url}")

        return ArticleContent(url=url, title=title or "", text=clean_text)
