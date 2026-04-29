"""
Behavioral router — STAR story management and practice.
POST /capture        → capture a behavioral story
GET  /stories        → list stories
GET  /stories/{id}   → get story
PUT  /stories/{id}   → update story
DELETE /stories/{id} → delete story
GET  /practice       → get a practice question
POST /practice/evaluate → evaluate a behavioral answer
GET  /coverage       → competency coverage
"""
import uuid as uuid_module

from fastapi import APIRouter, Request, HTTPException, Query, Depends
from core.rate_limiter import rate_limit
from models.behavioral_models import (
    BehavioralCaptureRequest,
    BehavioralCaptureResponse,
    StarStory,
    StarStoryListItem,
    StarStoryListResponse,
    StarStoryUpdateRequest,
    PracticeQuestionResponse,
    BehavioralEvaluation,
    BehavioralEvaluateRequest,
    BehavioralCoverageResponse,
    CompetencyCoverage,
)
from services.behavioral_service import BehavioralService

router = APIRouter()


def _validate_uuid(value: str, label: str = "ID") -> None:
    try:
        uuid_module.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {label} format")


def _serialize_dt(val) -> str | None:
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


def _get_service(request: Request) -> BehavioralService:
    return BehavioralService(
        db_pool=request.app.state.db_pool,
        openai_client=request.app.state.openai,
    )


@router.post("/capture", response_model=BehavioralCaptureResponse, dependencies=[Depends(rate_limit(10))])
async def capture_story(body: BehavioralCaptureRequest, request: Request):
    """Capture a behavioral story and extract STAR components."""
    service = _get_service(request)
    try:
        result = await service.capture_story(body.narrative, body.competency)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return BehavioralCaptureResponse(**result)


@router.get("/stories", response_model=StarStoryListResponse)
async def list_stories(
    request: Request,
    competency: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    """List STAR stories with optional competency filter."""
    service = _get_service(request)
    data = await service.list_stories(competency, limit, offset)
    return StarStoryListResponse(
        stories=[
            StarStoryListItem(
                id=str(s["id"]),
                title=s["title"],
                competency=s["competency"],
                strength_rating=s["strength_rating"],
                times_practiced=s["times_practiced"],
                created_at=_serialize_dt(s["created_at"]) or "",
            )
            for s in data["stories"]
        ],
        total=data["total"],
    )


@router.get("/stories/{story_id}", response_model=StarStory)
async def get_story(story_id: str, request: Request):
    """Get a single STAR story."""
    _validate_uuid(story_id, "story ID")
    service = _get_service(request)
    story = await service.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return StarStory(
        id=str(story["id"]),
        capture_id=str(story["capture_id"]) if story.get("capture_id") else None,
        title=story["title"],
        situation=story["situation"],
        task=story["task"],
        action=story["action"],
        result=story["result"],
        competency=story["competency"],
        strength_rating=story["strength_rating"],
        times_practiced=story["times_practiced"],
        last_practiced_at=_serialize_dt(story.get("last_practiced_at")),
        created_at=_serialize_dt(story["created_at"]) or "",
    )


@router.put("/stories/{story_id}", response_model=StarStory)
async def update_story(story_id: str, body: StarStoryUpdateRequest, request: Request):
    """Update a STAR story."""
    _validate_uuid(story_id, "story ID")
    service = _get_service(request)
    updates = body.model_dump(exclude_none=True)
    story = await service.update_story(story_id, updates)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return StarStory(
        id=str(story["id"]),
        capture_id=str(story["capture_id"]) if story.get("capture_id") else None,
        title=story["title"],
        situation=story["situation"],
        task=story["task"],
        action=story["action"],
        result=story["result"],
        competency=story["competency"],
        strength_rating=story["strength_rating"],
        times_practiced=story["times_practiced"],
        last_practiced_at=_serialize_dt(story.get("last_practiced_at")),
        created_at=_serialize_dt(story["created_at"]) or "",
    )


@router.delete("/stories/{story_id}")
async def delete_story(story_id: str, request: Request):
    """Delete a STAR story."""
    _validate_uuid(story_id, "story ID")
    service = _get_service(request)
    deleted = await service.delete_story(story_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Story not found")
    return {"message": "Story deleted"}


@router.get("/practice", response_model=PracticeQuestionResponse)
async def get_practice_question(
    request: Request,
    competency: str | None = Query(default=None),
):
    """Get a random behavioral interview practice question."""
    service = _get_service(request)
    try:
        result = await service.get_practice_question(competency)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PracticeQuestionResponse(**result)


@router.post("/practice/evaluate", response_model=BehavioralEvaluation, dependencies=[Depends(rate_limit(10))])
async def evaluate_practice_answer(body: BehavioralEvaluateRequest, request: Request):
    """Evaluate a behavioral interview answer using STAR framework."""
    service = _get_service(request)
    try:
        result = await service.evaluate_practice_answer(
            body.competency, body.question, body.answer
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return BehavioralEvaluation(**result)


@router.get("/coverage", response_model=BehavioralCoverageResponse)
async def get_coverage(request: Request):
    """Get competency coverage summary."""
    service = _get_service(request)
    data = await service.get_coverage()
    return BehavioralCoverageResponse(
        competencies=[
            CompetencyCoverage(
                competency=c["competency"],
                story_count=c["story_count"],
                avg_strength=float(c["avg_strength"]) if c.get("avg_strength") is not None else None,
                last_practiced=_serialize_dt(c.get("last_practiced")),
            )
            for c in data["competencies"]
        ],
        total_competencies=data["total_competencies"],
        covered_competencies=data["covered_competencies"],
    )
