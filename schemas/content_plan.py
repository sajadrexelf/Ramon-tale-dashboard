from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from services.content_planner import PlanWindow


class ContentPlanSlotInput(BaseModel):
    slot_id: str = Field(min_length=1, max_length=64)
    post_type: str = Field(min_length=1, max_length=64)
    window: PlanWindow


class NewsItemInput(BaseModel):
    news_id: str = Field(min_length=1, max_length=64)
    headline: str = Field(min_length=1, max_length=200)
    is_breaking: bool = False
    published_at: datetime | None = None


class ContentPlanRequest(BaseModel):
    plan_slots: list[ContentPlanSlotInput] = Field(min_length=1)
    news_items: list[NewsItemInput] = Field(min_length=1)


class ContentTaskResponse(BaseModel):
    slot_id: str
    post_type: str
    news_id: str
    headline: str


class ContentPlanResponse(BaseModel):
    tasks: list[ContentTaskResponse]
