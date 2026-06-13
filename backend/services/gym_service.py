"""
Memory Gym service — record training sessions and report bests/history.
"""
import json
import logging
import asyncpg
from openai import AsyncOpenAI
from fsrs import Scheduler

from core.db_queries import (
    insert_gym_session,
    get_gym_best_score,
    list_gym_sessions,
    get_gym_stats,
)
from models.gym_models import (
    GymSessionRequest, GymSessionResponse,
    GymSessionListItem, GymStatsResponse, GymExerciseStat,
)

logger = logging.getLogger(__name__)


def _parse_detail(value):
    """asyncpg returns jsonb as a str; normalize to dict | None."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return None


class GymService:
    def __init__(self, db_pool: asyncpg.Pool, openai_client: AsyncOpenAI, scheduler: Scheduler):
        self.db_pool = db_pool
        self.openai = openai_client
        self.scheduler = scheduler

    async def record(self, request: GymSessionRequest) -> GymSessionResponse:
        """Record a completed exercise session. Flags whether it's a new best."""
        prev_best = await get_gym_best_score(self.db_pool, request.exercise)
        session_id, created_at = await insert_gym_session(
            self.db_pool,
            request.exercise,
            request.score,
            request.max_score,
            request.level,
            request.duration_seconds,
            request.detail,
        )
        is_best = prev_best is None or request.score > prev_best
        return GymSessionResponse(
            session_id=session_id,
            created_at=created_at.isoformat(),
            is_best=is_best,
        )

    async def list(self, exercise: str | None, limit: int, offset: int) -> list[GymSessionListItem]:
        rows = await list_gym_sessions(self.db_pool, exercise, limit, offset)
        return [
            GymSessionListItem(
                id=str(r["id"]),
                exercise=r["exercise"],
                score=r["score"],
                max_score=r["max_score"],
                level=r["level"],
                duration_seconds=r["duration_seconds"],
                detail=_parse_detail(r["detail"]),
                created_at=r["created_at"].isoformat(),
            )
            for r in rows
        ]

    async def stats(self) -> GymStatsResponse:
        total, rows = await get_gym_stats(self.db_pool)
        return GymStatsResponse(
            total_sessions=total,
            exercises=[
                GymExerciseStat(
                    exercise=r["exercise"],
                    best_score=r["best_score"],
                    best_level=r["best_level"],
                    sessions=r["sessions"],
                    last_played_at=r["last_played_at"].isoformat() if r["last_played_at"] else None,
                )
                for r in rows
            ],
        )
