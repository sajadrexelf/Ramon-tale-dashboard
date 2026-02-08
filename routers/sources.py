from __future__ import annotations

import uuid

from fastapi import APIRouter

from schemas.sources import SourceCreateRequest, SourceResponse

router = APIRouter(tags=["sources"])


@router.post("/sources", response_model=SourceResponse)
async def create_source(payload: SourceCreateRequest) -> SourceResponse:
    source_id = uuid.uuid4().hex
    return SourceResponse(id=source_id, url=payload.url, name=payload.name)
