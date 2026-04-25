"""
Knowledge graph router — visualization data.
GET /graph/data → nodes + edges
GET /graph/node/{point_id} → node details
"""
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from services.graph_service import GraphService
from core.rate_limiter import rate_limit
from core.auth import get_current_user

router = APIRouter()


@router.get("/graph/data", dependencies=[Depends(rate_limit(10, 60))])  # 10 per minute
async def get_graph_data(
    request: Request,
    min_similarity: float = Query(0.7, ge=0.5, le=1.0),
    limit: int = Query(200, ge=1, le=200),
    user = Depends(get_current_user),
):
    """Get graph visualization data (nodes + edges)."""
    service = GraphService(request.app.state.db_pool)
    return await service.get_graph_data(min_similarity, limit)


@router.get("/graph/node/{point_id}")
async def get_node_detail(
    request: Request,
    point_id: str,
    user = Depends(get_current_user),
):
    """Get detailed information for a specific node."""
    service = GraphService(request.app.state.db_pool)
    detail = await service.get_node_detail(point_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Node not found")
    return detail
