from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from services.content_generator import ContentGenerationError, ContentGeneratorService, ContentType
from services.content_planner import ContentPlanSlot, ContentPlannerService, ContentPlanningError, NewsItem
from services.rss_fetcher import RSSFetchError, RSSFetcherService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContentPlanConfig:
    plan_slots: list[ContentPlanSlot]


@dataclass(frozen=True)
class SchedulerConfig:
    feed_urls: list[str]
    plan: ContentPlanConfig
    output_path: Path


class OutputStore:
    """Persist generated outputs to a JSONL file."""

    def __init__(self, output_path: Path) -> None:
        self._output_path = output_path
        self._output_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, payload: dict[str, object]) -> None:
        with self._output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


class DailyJobRunner:
    """Run daily content automation via APScheduler."""

    def __init__(self, config: SchedulerConfig) -> None:
        self._config = config
        self._rss_fetcher = RSSFetcherService()
        self._planner = ContentPlannerService()
        self._store = OutputStore(config.output_path)

    async def run_daily(self) -> None:
        logger.info("Starting daily automation job")
        if not self._config.feed_urls:
            logger.warning("No feed URLs configured; skipping job")
            return

        try:
            news_items = []
            for feed_url in self._config.feed_urls:
                articles = await self._rss_fetcher.fetch_latest(feed_url)
                for article in articles:
                    news_items.append(
                        NewsItem(
                            news_id=article.url,
                            headline=article.title,
                            is_breaking=False,
                            published_at=article.published_at,
                        )
                    )
        except RSSFetchError as exc:
            logger.exception("Failed to fetch RSS feeds: %s", exc)
            return

        try:
            tasks = self._planner.create_tasks(
                plan_slots=self._config.plan.plan_slots,
                news_items=news_items,
            )
        except ContentPlanningError as exc:
            logger.exception("Content planning failed: %s", exc)
            return

        api_key = os.getenv("ECONCONTENT_OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key missing; storing planned tasks only")
            for task in tasks:
                self._store.write(
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "task": asdict(task),
                        "status": "planned",
                    }
                )
            return

        generator = ContentGeneratorService(api_key=api_key)
        for task in tasks:
            started_at = time.perf_counter()
            try:
                content = await generator.generate(
                    headline=task.headline,
                    summary=task.headline,
                    key_facts=[task.headline],
                    content_type=ContentType.short,
                )
            except ContentGenerationError as exc:
                logger.warning("Content generation failed for %s: %s", task.news_id, exc)
                processing_time_seconds = time.perf_counter() - started_at
                self._store.write(
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "task": asdict(task),
                        "status": "failed",
                        "error": str(exc),
                        "processing_time_seconds": processing_time_seconds,
                    }
                )
                continue

            processing_time_seconds = time.perf_counter() - started_at
            self._store.write(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "task": asdict(task),
                    "status": "completed",
                    "content": asdict(content),
                    "processing_time_seconds": processing_time_seconds,
                }
            )

        logger.info("Daily automation job completed")


def start_scheduler(config: SchedulerConfig) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    runner = DailyJobRunner(config)
    scheduler.add_job(runner.run_daily, "cron", hour=7, minute=0)
    scheduler.start()
    return scheduler
