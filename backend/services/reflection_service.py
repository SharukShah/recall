"""
Reflection service — Evening Reflection feature.
Submit reflections, check status, list past reflections.
"""
import logging
from openai import AsyncOpenAI
from fsrs import Scheduler
import asyncpg

from core.db_queries import (
    insert_reflection,
    update_reflection_capture,
    has_reflected_today,
    get_reflection_streak,
    get_last_reflection_at,
    list_reflections,
)
from models.capture_models import CaptureRequest
from models.reflection_models import (
    ReflectionRequest, ReflectionResponse,
    ReflectionStatusResponse, ReflectionListItem,
)

logger = logging.getLogger(__name__)


class ReflectionService:
    def __init__(self, db_pool: asyncpg.Pool, openai_client: AsyncOpenAI, scheduler: Scheduler):
        self.db_pool = db_pool
        self.openai = openai_client
        self.scheduler = scheduler

    async def create(self, request: ReflectionRequest) -> ReflectionResponse:
        """Submit a daily reflection. Runs through capture pipeline."""
        # Check if already reflected today
        already_done = await has_reflected_today(self.db_pool)
        if already_done:
            streak = await get_reflection_streak(self.db_pool)
            return ReflectionResponse(
                reflection_id="",
                capture_id=None,
                facts_count=0,
                questions_count=0,
                streak_days=streak,
                message="Already reflected today.",
            )

        # Store the reflection — UNIQUE index prevents race condition duplicates
        try:
            reflection_id = await insert_reflection(self.db_pool, request.content)
        except Exception as e:
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                streak = await get_reflection_streak(self.db_pool)
                return ReflectionResponse(
                    reflection_id="",
                    capture_id=None,
                    facts_count=0,
                    questions_count=0,
                    streak_days=streak,
                    message="Already reflected today.",
                )
            raise

        # Run through capture pipeline
        from services.capture_service import CaptureService
        capture_service = CaptureService(self.db_pool, self.openai, self.scheduler)
        capture_request = CaptureRequest(
            raw_text=request.content,
            source_type="reflection",
            why_it_matters=None,
        )

        capture_id = None
        facts_count = 0
        questions_count = 0
        message = None

        try:
            capture_result = await capture_service.process(capture_request)
            if capture_result.capture_id and capture_result.status == "complete":
                capture_id = capture_result.capture_id
                facts_count = capture_result.facts_count
                questions_count = capture_result.questions_count
                await update_reflection_capture(self.db_pool, reflection_id, capture_id)
            elif capture_result.status == "no_facts":
                message = "Reflection saved! No specific facts to review."
        except Exception as e:
            logger.error(f"Reflection capture pipeline failed: {e}")
            message = "Reflection saved but fact extraction failed."

        streak = await get_reflection_streak(self.db_pool)

        return ReflectionResponse(
            reflection_id=reflection_id,
            capture_id=capture_id,
            facts_count=facts_count,
            questions_count=questions_count,
            streak_days=streak,
            message=message,
        )

    async def status(self) -> ReflectionStatusResponse:
        """Check if today's reflection is done and current streak."""
        completed = await has_reflected_today(self.db_pool)
        streak = await get_reflection_streak(self.db_pool)
        last_at = await get_last_reflection_at(self.db_pool)

        return ReflectionStatusResponse(
            completed_today=completed,
            streak_days=streak,
            last_reflection_at=last_at.isoformat() if last_at else None,
        )

    async def list(self, limit: int = 20, offset: int = 0) -> list[ReflectionListItem]:
        """List past reflections."""
        rows = await list_reflections(self.db_pool, limit, offset)
        return [
            ReflectionListItem(
                id=str(r["id"]),
                content=r["content"],
                capture_id=str(r["capture_id"]) if r["capture_id"] else None,
                created_at=r["created_at"].isoformat(),
            )
            for r in rows
        ]
