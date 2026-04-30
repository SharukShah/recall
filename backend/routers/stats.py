"""
Stats router — dashboard data + interview prep analytics.
GET /dashboard        → due count, total captures, total questions, reviews today, streak
GET /analytics        → detailed analytics summary
GET /retention-curve  → retention trend over weeks
GET /weak-areas       → weak question areas
GET /activity         → daily activity heatmap data
GET /topic-coverage   → question coverage per category
GET /weak-categories  → category-level weakness
GET /streak-info      → streak milestones and risk
"""
from fastapi import APIRouter, Request, Query
from core.db_queries import get_dashboard_stats
from services.stats_service import StatsService
from models.analytics_models import (
    AnalyticsResponse,
    RetentionCurveResponse,
    WeakAreasResponse,
    ActivityResponse,
    TopicCoverageResponse,
    WeakCategoriesResponse,
    StreakInfoResponse,
)

router = APIRouter()


@router.get("/dashboard")
async def dashboard(request: Request):
    """Get dashboard statistics."""
    stats = await get_dashboard_stats(request.app.state.db_pool)
    return stats


@router.get("/topic-coverage", response_model=TopicCoverageResponse)
async def topic_coverage(request: Request):
    """Get question coverage stats per category."""
    service = StatsService(db_pool=request.app.state.db_pool)
    return await service.get_topic_coverage()


@router.get("/weak-categories", response_model=WeakCategoriesResponse)
async def weak_categories(request: Request):
    """Get category-level weakness aggregation."""
    service = StatsService(db_pool=request.app.state.db_pool)
    return await service.get_weak_categories()


@router.get("/streak-info", response_model=StreakInfoResponse)
async def streak_info(request: Request):
    """Get current streak, milestones, and risk status."""
    service = StatsService(db_pool=request.app.state.db_pool)
    return await service.get_streak_info()


@router.get("/analytics", response_model=AnalyticsResponse)
async def analytics(request: Request):
    """Get detailed analytics summary."""
    service = StatsService(db_pool=request.app.state.db_pool)
    return await service.get_analytics()


@router.get("/retention-curve", response_model=RetentionCurveResponse)
async def retention_curve(request: Request, weeks: int = Query(12, ge=1, le=52)):
    """Get retention trend over weeks."""
    service = StatsService(db_pool=request.app.state.db_pool)
    return await service.get_retention_curve(weeks=weeks)


@router.get("/weak-areas", response_model=WeakAreasResponse)
async def weak_areas(request: Request, limit: int = Query(10, ge=1, le=50)):
    """Get weakest question areas."""
    service = StatsService(db_pool=request.app.state.db_pool)
    return await service.get_weak_areas(limit=limit)


@router.get("/activity", response_model=ActivityResponse)
async def activity(request: Request, days: int = Query(90, ge=1, le=365)):
    """Get daily activity data for heatmap."""
    service = StatsService(db_pool=request.app.state.db_pool)
    return await service.get_activity(days=days)
