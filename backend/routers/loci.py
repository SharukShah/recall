"""Method of Loci endpoints - memory palace walkthroughs."""
from fastapi import APIRouter, Request, HTTPException, Depends, Query
import logging

from models.loci_models import (
    LociCreateRequest,
    LociCreateResponse,
    LociRecallRequest,
    LociRecallResponse,
    LociListItem,
)
from services.loci_service import LociService
from core.rate_limiter import rate_limit
from core.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


def get_loci_service(request: Request) -> LociService:
    """Dependency injection for LociService."""
    return LociService(
        request.app.state.db_pool,
        request.app.state.openai,
        request.app.state.scheduler,
    )


@router.post("/create", response_model=LociCreateResponse, dependencies=[Depends(rate_limit(10, 3600))])  # 10 per hour
async def create_loci_session(
    data: LociCreateRequest,
    service: LociService = Depends(get_loci_service),
    user = Depends(get_current_user),
):
    """Create a new memory palace walkthrough."""
    try:
        # Check session count limit
        async with service.db_pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM loci_sessions"
            )
            if count >= 50:
                raise HTTPException(
                    status_code=400,
                    detail="Maximum 50 loci sessions reached. Delete old sessions first."
                )
        
        return await service.create(data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create loci session: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate memory palace",
        )


@router.get("/{session_id}", response_model=LociCreateResponse)
async def get_loci_session(
    session_id: str,
    service: LociService = Depends(get_loci_service),
    user = Depends(get_current_user),
):
    """Get a loci session by ID."""
    session = await service.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/recall", response_model=LociRecallResponse, dependencies=[Depends(rate_limit(30, 3600))])  # 30 per hour
async def submit_loci_recall(
    session_id: str,
    data: LociRecallRequest,
    service: LociService = Depends(get_loci_service),
    user = Depends(get_current_user),
):
    """Submit a recall attempt and get evaluation."""
    try:
        return await service.recall(session_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to evaluate recall: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to evaluate recall",
        )


@router.get("/", response_model=list[LociListItem])
async def list_loci_sessions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: LociService = Depends(get_loci_service),
    user = Depends(get_current_user),
):
    """List all loci sessions."""
    return await service.list(limit, offset)
