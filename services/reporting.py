from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)


class ReportingError(RuntimeError):
    """Raised when KPI reporting cannot be produced."""


@dataclass(frozen=True)
class DailyKPIs:
    date: date
    generated_posts: int
    failure_rate: float
    average_processing_time_seconds: float | None
    content_type_distribution: dict[str, int]
    total_tasks: int
    failed_tasks: int


class ReportingService:
    """Compute daily KPIs from stored automation outputs."""

    def __init__(self, output_path: Path) -> None:
        self._output_path = output_path

    def _iter_records(self) -> Iterable[dict[str, object]]:
        if not self._output_path.exists():
            raise ReportingError(f"Output store not found at {self._output_path}.")

        with self._output_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("Skipping invalid JSONL line in %s", self._output_path)
                    continue

    @staticmethod
    def _record_date(payload: dict[str, object]) -> date | None:
        timestamp = payload.get("timestamp")
        if not isinstance(timestamp, str):
            return None
        try:
            parsed = datetime.fromisoformat(timestamp)
        except ValueError:
            return None
        return parsed.date()

    def get_daily_kpis(self, target_date: date) -> DailyKPIs:
        total_tasks = 0
        completed_tasks = 0
        failed_tasks = 0
        processing_times: list[float] = []
        content_type_distribution: dict[str, int] = {}

        for record in self._iter_records():
            if self._record_date(record) != target_date:
                continue

            total_tasks += 1
            status = record.get("status")
            if status == "completed":
                completed_tasks += 1
            elif status == "failed":
                failed_tasks += 1

            processing_time = record.get("processing_time_seconds")
            if isinstance(processing_time, (int, float)):
                processing_times.append(float(processing_time))

            task = record.get("task")
            if status == "completed" and isinstance(task, dict):
                post_type = task.get("post_type")
                if isinstance(post_type, str) and post_type.strip():
                    key = post_type.strip()
                else:
                    key = "unknown"
                content_type_distribution[key] = content_type_distribution.get(key, 0) + 1

        total_completed_or_failed = completed_tasks + failed_tasks
        failure_rate = (
            failed_tasks / total_completed_or_failed
            if total_completed_or_failed
            else 0.0
        )
        average_processing_time = (
            sum(processing_times) / len(processing_times)
            if processing_times
            else None
        )

        return DailyKPIs(
            date=target_date,
            generated_posts=completed_tasks,
            failure_rate=failure_rate,
            average_processing_time_seconds=average_processing_time,
            content_type_distribution=content_type_distribution,
            total_tasks=total_tasks,
            failed_tasks=failed_tasks,
        )
