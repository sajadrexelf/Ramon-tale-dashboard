from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class DailyReportResponse(BaseModel):
    date: date
    tasks_planned: int
    notes: str


class KPIResponse(BaseModel):
    date: date
    generated_posts: int
    failure_rate: float
    average_processing_time_seconds: float | None
    content_type_distribution: dict[str, int]
    total_tasks: int
    failed_tasks: int
