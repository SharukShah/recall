"""
Reflections router — Evening Reflection endpoints.
POST /       → Submit a reflection
GET  /       → List past reflections
GET  /status → Check if today's reflection is done
"""
from fastapi import APIRouter, Request, HTTPException, Query, Depends
from core.rate_limiter import rate_limit
from models.reflection_models import (
    ReflectionRequest, ReflectionResponse,
    ReflectionStatusResponse, ReflectionListItem,
)
from services.reflection_service import ReflectionService

router = APIRouter()


@router.post("/", response_model=ReflectionResponse, dependencies=[Depends(rate_limit(10))])
async def submit_reflection(body: ReflectionRequest, request: Request):
    """Submit an evening reflection."""
    service = ReflectionService(
        db_pool=request.app.state.db_pool,
        openai_client=request.app.state.openai,
        scheduler=request.app.state.scheduler,
    )
    result = await service.create(body)
    if result.message == "Already reflected today.":
        raise HTTPException(status_code=409, detail="Already reflected today.")
    return result


@router.get("/status", response_model=ReflectionStatusResponse)
async def reflection_status(request: Request):
    """Check if today's reflection is done and get streak."""
    service = ReflectionService(
        db_pool=request.app.state.db_pool,
        openai_client=request.app.state.openai,
        scheduler=request.app.state.scheduler,
    )
    return await service.status()


@router.get("/", response_model=list[ReflectionListItem])
async def list_reflections(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List past reflections."""
    service = ReflectionService(
        db_pool=request.app.state.db_pool,
        openai_client=request.app.state.openai,
        scheduler=request.app.state.scheduler,
    )
    return await service.list(limit, offset)
