"""
Stats router — dashboard data.
GET /dashboard → due count, total captures, total questions, reviews today, streak
"""
from fastapi import APIRouter, Request
from core.db_queries import get_dashboard_stats

router = APIRouter()


@router.get("/dashboard")
async def dashboard(request: Request):
    """Get dashboard statistics."""
    stats = await get_dashboard_stats(request.app.state.db_pool)
    return stats
