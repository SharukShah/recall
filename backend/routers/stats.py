"""
Stats router — dashboard data + interview prep analytics.
GET /dashboard        → due count, total captures, total questions, reviews today, streak
GET /topic-coverage   → question coverage per category
GET /weak-categories  → category-level weakness
GET /streak-info      → streak milestones and risk
"""
from fastapi import APIRouter, Request
from core.db_queries import get_dashboard_stats
from services.stats_service import StatsService
from models.analytics_models import (
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
