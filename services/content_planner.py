from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PlanWindow(str, Enum):
    daily = "daily"
    weekly = "weekly"


@dataclass(frozen=True)
class ContentPlanSlot:
    slot_id: str
    post_type: str
    window: PlanWindow


@dataclass(frozen=True)
class NewsItem:
    news_id: str
    headline: str
    is_breaking: bool
    published_at: datetime | None = None


@dataclass(frozen=True)
class ContentTask:
    slot_id: str
    post_type: str
    news_id: str
    headline: str


class ContentPlanningError(RuntimeError):
    """Raised when content planning fails due to invalid inputs."""


class ContentPlannerService:
    """Match plan slots with news items without duplicates and breaking-news priority."""

    def create_tasks(
        self,
        plan_slots: list[ContentPlanSlot],
        news_items: list[NewsItem],
    ) -> list[ContentTask]:
        if not plan_slots:
            raise ContentPlanningError("At least one plan slot is required.")
        if not news_items:
            raise ContentPlanningError("At least one news item is required.")

        sorted_news = sorted(
            news_items,
            key=lambda item: (
                not item.is_breaking,
                -(item.published_at.timestamp()) if item.published_at else float("inf"),
            ),
        )

        tasks: list[ContentTask] = []
        used_news_ids: set[str] = set()

        for slot in plan_slots:
            matched = next(
                (
                    item
                    for item in sorted_news
                    if item.news_id not in used_news_ids
                ),
                None,
            )
            if not matched:
                logger.warning("No available news item for slot %s", slot.slot_id)
                continue

            used_news_ids.add(matched.news_id)
            tasks.append(
                ContentTask(
                    slot_id=slot.slot_id,
                    post_type=slot.post_type,
                    news_id=matched.news_id,
                    headline=matched.headline,
                )
            )

        return tasks
