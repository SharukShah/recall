"""
Teach router — Teach Me Mode endpoints.
POST /start        → Start a teaching session
POST /respond      → Submit answer to recall check
GET  /{session_id} → Resume/get session state
"""
import uuid as uuid_module
from fastapi import APIRouter, Request, HTTPException, Depends
from core.rate_limiter import rate_limit
from models.teach_models import (
    TeachStartRequest, TeachStartResponse,
    TeachRespondRequest, TeachRespondResponse,
    TeachSessionResponse,
)
from services.teach_service import TeachService

router = APIRouter()


@router.post("/start", response_model=TeachStartResponse, dependencies=[Depends(rate_limit(10))])
async def start_teach_session(body: TeachStartRequest, request: Request):
    """Start a new teaching session on a topic."""
    service = TeachService(
        db_pool=request.app.state.db_pool,
        openai_client=request.app.state.openai,
        scheduler=request.app.state.scheduler,
    )
    try:
        return await service.start(body)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate teaching plan. Try a different topic.")


@router.post("/respond", response_model=TeachRespondResponse, dependencies=[Depends(rate_limit(30))])
async def respond_to_teach(body: TeachRespondRequest, request: Request):
    """Submit answer to recall check, get next chunk or feedback."""
    service = TeachService(
        db_pool=request.app.state.db_pool,
        openai_client=request.app.state.openai,
        scheduler=request.app.state.scheduler,
    )
    try:
        return await service.respond(body)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{session_id}", response_model=TeachSessionResponse)
async def get_teach_session(session_id: str, request: Request):
    """Get current state of a teaching session (for resume)."""
    try:
        uuid_module.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid session ID format")

    service = TeachService(
        db_pool=request.app.state.db_pool,
        openai_client=request.app.state.openai,
        scheduler=request.app.state.scheduler,
    )
    try:
        return await service.get_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
