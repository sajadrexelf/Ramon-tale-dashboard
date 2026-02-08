from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from schemas.reports import DailyReportResponse, KPIResponse
from services.reporting import ReportingError, ReportingService

router = APIRouter(tags=["reports"])


@router.get("/daily-report", response_model=DailyReportResponse)
async def get_daily_report() -> DailyReportResponse:
    today = date.today()
    return DailyReportResponse(
        date=today,
        tasks_planned=0,
        notes="Daily report generation is not configured yet.",
    )


@router.get("/kpis", response_model=KPIResponse)
async def get_kpis(
    report_date: date | None = Query(default=None, alias="date"),
    output_path: str | None = Query(default=None),
) -> KPIResponse:
    target_date = report_date or date.today()
    resolved_path = Path(
        output_path or os.getenv("ECONCONTENT_OUTPUT_PATH", "data/output.jsonl")
    )
    service = ReportingService(resolved_path)
    try:
        kpis = service.get_daily_kpis(target_date)
    except ReportingError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return KPIResponse(
        date=kpis.date,
        generated_posts=kpis.generated_posts,
        failure_rate=kpis.failure_rate,
        average_processing_time_seconds=kpis.average_processing_time_seconds,
        content_type_distribution=kpis.content_type_distribution,
        total_tasks=kpis.total_tasks,
        failed_tasks=kpis.failed_tasks,
    )
