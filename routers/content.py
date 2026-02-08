from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException

from schemas.content_generation import ContentGenerationRequest, ContentGenerationResponse
from schemas.content_plan import ContentPlanRequest, ContentPlanResponse, ContentTaskResponse
from services.content_generator import ContentGenerationError, ContentGeneratorService
from services.content_planner import ContentPlanSlot, ContentPlannerService, ContentPlanningError, NewsItem

router = APIRouter(tags=["content"])


@router.post("/content-plan", response_model=ContentPlanResponse)
async def create_content_plan(payload: ContentPlanRequest) -> ContentPlanResponse:
    service = ContentPlannerService()
    plan_slots = [
        ContentPlanSlot(
            slot_id=slot.slot_id,
            post_type=slot.post_type,
            window=slot.window,
        )
        for slot in payload.plan_slots
    ]
    news_items = [
        NewsItem(
            news_id=item.news_id,
            headline=item.headline,
            is_breaking=item.is_breaking,
            published_at=item.published_at,
        )
        for item in payload.news_items
    ]

    try:
        tasks = service.create_tasks(plan_slots=plan_slots, news_items=news_items)
    except ContentPlanningError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ContentPlanResponse(
        tasks=[
            ContentTaskResponse(
                slot_id=task.slot_id,
                post_type=task.post_type,
                news_id=task.news_id,
                headline=task.headline,
            )
            for task in tasks
        ]
    )


@router.post("/generate-content", response_model=ContentGenerationResponse)
async def generate_content(payload: ContentGenerationRequest) -> ContentGenerationResponse:
    api_key = os.getenv("ECONCONTENT_OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key is not configured.")

    service = ContentGeneratorService(api_key=api_key)
    try:
        content = await service.generate(
            headline=payload.headline,
            summary=payload.summary,
            key_facts=payload.key_facts,
            content_type=payload.content_type,
        )
    except ContentGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ContentGenerationResponse(
        lead=content.lead,
        body=content.body,
        analysis=content.analysis,
        cta=content.cta,
    )
