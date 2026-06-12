"""
Captures router — create, list, and detail endpoints.
POST /  → create capture (trigger full pipeline)
GET /   → list recent captures
GET /{capture_id} → capture with facts and questions
"""
import uuid as uuid_module
from fastapi import APIRouter, Request, HTTPException, Query, Depends
from core.rate_limiter import rate_limit
from models.capture_models import CaptureRequest, CaptureResponse, CaptureListItem, CaptureDetail, FactItem, QuestionItem
from services.capture_service import CaptureService

router = APIRouter()


@router.post("/", response_model=CaptureResponse, dependencies=[Depends(rate_limit(10))])
async def create_capture(body: CaptureRequest, request: Request):
    """Create a new capture — triggers full extraction + question generation pipeline."""
    service = CaptureService(
        db_pool=request.app.state.db_pool,
        openai_client=request.app.state.openai,
        scheduler=request.app.state.scheduler,
    )
    return await service.process(body)


@router.get("/", response_model=list[CaptureListItem])
async def list_captures(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List recent captures with fact count."""
    from core.db_queries import list_captures as db_list_captures
    rows = await db_list_captures(request.app.state.db_pool, limit, offset)
    return [
        CaptureListItem(
            id=str(r["id"]),
            raw_text=r["raw_text"][:200],  # Truncate for list view
            source_type=r["source_type"],
            facts_count=r["facts_count"],
            created_at=r["created_at"].isoformat(),
        )
        for r in rows
    ]


@router.get("/{capture_id}", response_model=CaptureDetail)
async def get_capture(capture_id: str, request: Request):
    """Get a capture with its extracted facts and generated questions."""
    try:
        uuid_module.UUID(capture_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid capture ID format")
    from core.db_queries import get_capture_detail
    result = await get_capture_detail(request.app.state.db_pool, capture_id)
    if not result:
        raise HTTPException(status_code=404, detail="Capture not found")

    c = result["capture"]
    return CaptureDetail(
        id=str(c["id"]),
        raw_text=c["raw_text"],
        source_type=c["source_type"],
        why_it_matters=c.get("why_it_matters"),
        created_at=c["created_at"].isoformat(),
        facts=[
            FactItem(
                id=str(f["id"]),
                content=f["content"],
                content_type=f["content_type"],
                created_at=f["created_at"].isoformat(),
            )
            for f in result["facts"]
        ],
        questions=[
            QuestionItem(
                id=str(q["id"]),
                question_text=q["question_text"],
                answer_text=q["answer_text"],
                question_type=q["question_type"],
                technique_used=q.get("technique_used"),
                mnemonic_hint=q.get("mnemonic_hint"),
                state=q["state"],
                due=q["due"].isoformat(),
            )
            for q in result["questions"]
        ],
    )
