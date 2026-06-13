"""
Memory Gym router — record training sessions, list history, report stats.
POST /          → record a completed exercise session
GET  /          → list past sessions (optional ?exercise= filter)
GET  /stats     → per-exercise bests + counts
"""
from fastapi import APIRouter, Request, HTTPException, Query, Depends
from core.rate_limiter import rate_limit
from models.gym_models import (
    GymSessionRequest, GymSessionResponse,
    GymSessionListItem, GymStatsResponse, GYM_EXERCISES,
)
from services.gym_service import GymService

router = APIRouter()


def _service(request: Request) -> GymService:
    return GymService(
        db_pool=request.app.state.db_pool,
        openai_client=request.app.state.openai,
        scheduler=request.app.state.scheduler,
    )


@router.post("/", response_model=GymSessionResponse, dependencies=[Depends(rate_limit(60))])
async def record_session(body: GymSessionRequest, request: Request):
    """Record a completed gym exercise session."""
    if body.exercise not in GYM_EXERCISES:
        raise HTTPException(status_code=422, detail=f"Unknown exercise: {body.exercise}")
    return await _service(request).record(body)


@router.get("/stats", response_model=GymStatsResponse)
async def gym_stats(request: Request):
    """Per-exercise best scores and session counts."""
    return await _service(request).stats()


@router.get("/", response_model=list[GymSessionListItem])
async def list_sessions(
    request: Request,
    exercise: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List past gym sessions, newest first."""
    if exercise is not None and exercise not in GYM_EXERCISES:
        raise HTTPException(status_code=422, detail=f"Unknown exercise: {exercise}")
    return await _service(request).list(exercise, limit, offset)
