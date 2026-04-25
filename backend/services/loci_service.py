"""
Method of Loci service - memory palace walkthrough generation and recall testing.
"""
import logging
import uuid
import json
from openai import AsyncOpenAI
from fsrs import Scheduler
import asyncpg

from core import llm
from services.capture_service import CaptureService
from models.loci_models import (
    LociCreateRequest,
    LociCreateResponse,
    LociWalkthrough,
    LociRecallRequest,
    LociRecallResponse,
    LociRecallDetail,
    LociListItem,
)

logger = logging.getLogger(__name__)


class LociService:
    def __init__(self, db_pool: asyncpg.Pool, openai_client: AsyncOpenAI, scheduler: Scheduler):
        self.db_pool = db_pool
        self.openai = openai_client
        self.scheduler = scheduler

    async def create(self, request: LociCreateRequest) -> LociCreateResponse:
        """Generate a memory palace walkthrough for the given items."""
        # Generate walkthrough using LLM
        walkthrough = await llm.generate_loci_walkthrough(
            self.openai,
            request.items,
            request.palace_theme,
        )
        
        # Build full narration
        narration_parts = [walkthrough.introduction]
        for loc in walkthrough.locations:
            narration_parts.append(loc.narration)
        narration_parts.append(walkthrough.conclusion)
        full_narration = "\n\n".join(narration_parts)
        
        # Auto-create capture for FSRS scheduling
        capture_service = CaptureService(self.db_pool, self.openai, self.scheduler)
        items_text = "\n".join([f"{i+1}. {item}" for i, item in enumerate(request.items)])
        capture_raw_text = f"{request.title}\n\n{items_text}"
        
        try:
            from models.capture_models import CaptureRequest
            capture_response = await capture_service.process(
                CaptureRequest(
                    raw_text=capture_raw_text,
                    source_type="loci",
                    why_it_matters=None,
                )
            )
            capture_id = capture_response.capture_id if capture_response.status == "complete" else None
        except Exception as e:
            logger.error(f"Failed to create capture for loci: {e}")
            capture_id = None
        
        # Store session in DB
        session_id = str(uuid.uuid4())
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO loci_sessions (
                    id, title, items, palace_theme, walkthrough_json, full_narration, capture_id
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                uuid.UUID(session_id),
                request.title,
                json.dumps(request.items),
                walkthrough.palace_theme,
                json.dumps(walkthrough.model_dump()),
                full_narration,
                uuid.UUID(capture_id) if capture_id else None,
            )
        
        return LociCreateResponse(
            session_id=session_id,
            title=request.title,
            palace_theme=walkthrough.palace_theme,
            total_locations=len(walkthrough.locations),
            walkthrough=walkthrough,
            full_narration=full_narration,
            capture_id=capture_id,
        )

    async def get(self, session_id: str) -> LociCreateResponse | None:
        """Get a loci session by ID."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, title, items, palace_theme, walkthrough_json, 
                       full_narration, capture_id, created_at
                FROM loci_sessions WHERE id = $1
                """,
                uuid.UUID(session_id),
            )
        
        if not row:
            return None
        
        walkthrough_data = json.loads(row["walkthrough_json"])
        walkthrough = LociWalkthrough(**walkthrough_data)
        
        return LociCreateResponse(
            session_id=str(row["id"]),
            title=row["title"],
            palace_theme=row["palace_theme"],
            total_locations=len(walkthrough.locations),
            walkthrough=walkthrough,
            full_narration=row["full_narration"],
            capture_id=str(row["capture_id"]) if row["capture_id"] else None,
        )

    async def recall(self, session_id: str, request: LociRecallRequest) -> LociRecallResponse:
        """Evaluate a recall attempt."""
        # Get the session
        session = await self.get(session_id)
        if not session:
            raise ValueError("Session not found")
        
        # Get original items
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT items FROM loci_sessions WHERE id = $1",
                uuid.UUID(session_id),
            )
        
        original_items = json.loads(row["items"])
        recalled_items = request.recalled_items
        
        # Compare items (position-sensitive, case-insensitive)
        details = []
        correct_count = 0
        
        for i, expected in enumerate(original_items):
            recalled = recalled_items[i] if i < len(recalled_items) else None
            correct = (
                recalled is not None 
                and recalled.strip().lower() == expected.strip().lower()
            )
            if correct:
                correct_count += 1
            
            # Get location hint from walkthrough
            location = session.walkthrough.locations[i]
            location_hint = f"At {location.location_name}"
            
            details.append(
                LociRecallDetail(
                    position=i + 1,
                    expected=expected,
                    recalled=recalled,
                    correct=correct,
                    location_hint=location_hint,
                )
            )
        
        # Generate feedback using LLM
        feedback = await llm.evaluate_loci_recall(
            self.openai,
            original_items,
            recalled_items,
            correct_count,
            len(original_items),
        )
        
        # Update last_recall_score
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE loci_sessions
                SET last_recall_score = $1, updated_at = NOW()
                WHERE id = $2
                """,
                correct_count,
                uuid.UUID(session_id),
            )
        
        return LociRecallResponse(
            score=correct_count,
            total=len(original_items),
            feedback=feedback,
            correct_order=original_items,
            details=details,
        )

    async def list(self, limit: int = 20, offset: int = 0) -> list[LociListItem]:
        """List all loci sessions."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, title, palace_theme, items, last_recall_score, created_at
                FROM loci_sessions
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
        
        return [
            LociListItem(
                session_id=str(row["id"]),
                title=row["title"],
                palace_theme=row["palace_theme"],
                total_locations=len(json.loads(row["items"])),
                last_recall_score=row["last_recall_score"],
                created_at=row["created_at"].isoformat(),
            )
            for row in rows
        ]
