"""
Stats router — dashboard + analytics data.
"""
from fastapi import APIRouter, Request, Query, Depends
from core.db_queries import get_dashboard_stats
from core.rate_limiter import rate_limit
from services.stats_service import StatsService

router = APIRouter()


@router.get("/dashboard")
async def dashboard(request: Request):
    """Get dashboard statistics."""
    stats = await get_dashboard_stats(request.app.state.db_pool)
    return stats


@router.get("/analytics", dependencies=[Depends(rate_limit(10, 60))])
async def analytics(request: Request):
    """Get comprehensive analytics data."""
    service = StatsService(request.app.state.db_pool)
    return await service.get_analytics()


@router.get("/analytics/retention", dependencies=[Depends(rate_limit(10, 60))])
async def retention_curve(request: Request, weeks: int = Query(12, ge=1, le=52)):
    """Get retention rate over time."""
    service = StatsService(request.app.state.db_pool)
    return await service.get_retention_curve(weeks)


@router.get("/analytics/weak-areas", dependencies=[Depends(rate_limit(10, 60))])
async def weak_areas(request: Request, limit: int = Query(10, ge=1, le=50)):
    """Get topics with lowest retention rates."""
    service = StatsService(request.app.state.db_pool)
    return await service.get_weak_areas(limit)


@router.get("/analytics/activity", dependencies=[Depends(rate_limit(10, 60))])
async def activity(request: Request, days: int = Query(90, ge=1, le=365)):
    """Get daily activity for last N days."""
    service = StatsService(request.app.state.db_pool)
    return await service.get_activity(days)
