"""
Teach service — Teach Me Mode with chunked teaching and active recall checks.
"""
import json
import logging
import uuid as uuid_module
from openai import AsyncOpenAI
from fsrs import Scheduler
import asyncpg

from core import llm
from core.db_queries import (
    insert_teach_session,
    get_teach_session,
    get_teach_session_for_update,
    update_teach_session_chunk,
    complete_teach_session,
)
from models.teach_models import (
    TeachStartRequest, TeachStartResponse,
    TeachRespondRequest, TeachRespondResponse,
    TeachSessionResponse,
)
from models.capture_models import CaptureRequest

logger = logging.getLogger(__name__)


class TeachService:
    def __init__(self, db_pool: asyncpg.Pool, openai_client: AsyncOpenAI, scheduler: Scheduler):
        self.db_pool = db_pool
        self.openai = openai_client
        self.scheduler = scheduler

    async def start(self, request: TeachStartRequest) -> TeachStartResponse:
        """Start a new teaching session on a topic."""
        # Generate teaching plan via LLM
        plan = await llm.generate_teach_plan(self.openai, request.topic)

        # Store session in DB
        plan_dict = plan.model_dump()

        if not plan.chunks:
            raise ValueError("LLM returned an empty teaching plan. Try a different topic.")

        session_id = await insert_teach_session(
            self.db_pool, plan.topic, plan_dict,
        )

        first_chunk = plan.chunks[0]
        return TeachStartResponse(
            session_id=session_id,
            topic=plan.topic,
            total_chunks=plan.total_chunks,
            current_chunk=0,
            chunk_title=first_chunk.title,
            chunk_content=first_chunk.content,
            chunk_analogy=first_chunk.analogy,
            recall_question=first_chunk.recall_question,
        )

    async def respond(self, request: TeachRespondRequest) -> TeachRespondResponse:
        """Submit answer to recall check, get feedback and next chunk or summary."""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                session = await get_teach_session_for_update(conn, request.session_id)
                if not session:
                    raise ValueError(f"Teaching session not found: {request.session_id}")
                if session["status"] == "complete":
                    raise ValueError("This teaching session is already complete.")

                plan_data = session["plan_json"] if isinstance(session["plan_json"], dict) else json.loads(session["plan_json"])
                chunks = plan_data["chunks"]
                if not chunks:
                    raise ValueError("Teaching plan has no chunks.")
                current_idx = session["current_chunk"]
                current_chunk = chunks[current_idx]

                # Evaluate answer against current chunk's recall question
                try:
                    evaluation = await llm.evaluate_teach_answer(
                        self.openai,
                        current_chunk["recall_question"],
                        current_chunk["content"],
                        request.answer,
                    )
                    score = evaluation.score
                    feedback = evaluation.feedback
                except Exception as e:
                    logger.error(f"Teach answer evaluation failed: {e}")
                    score = "partial"
                    feedback = "Could not evaluate. Review the chunk content above."

                next_idx = current_idx + 1
                is_complete = next_idx >= len(chunks)

                if is_complete:
                    # Auto-capture: concatenate all chunk contents
                    all_content = "\n\n".join(
                        f"## {c['title']}\n{c['content']}" for c in chunks
                    )

                    # Mark session complete (within the transaction)
                    capture_id = None
                    await complete_teach_session(conn, request.session_id, capture_id)

                # Advance to next chunk (within the transaction)
                if not is_complete:
                    await update_teach_session_chunk(conn, request.session_id, next_idx)

        # Auto-capture outside the transaction (it does its own transaction)
        if is_complete:
            from services.capture_service import CaptureService
            capture_service = CaptureService(self.db_pool, self.openai, self.scheduler)
            capture_request = CaptureRequest(
                raw_text=all_content[:50000],
                source_type="text",
                why_it_matters=None,
            )

            try:
                capture_result = await capture_service.process(capture_request)
                if capture_result.capture_id:
                    capture_id = capture_result.capture_id
                    # Update session with capture_id
                    async with self.db_pool.acquire() as conn:
                        await conn.execute(
                            "UPDATE teach_sessions SET capture_id = $1 WHERE id = $2",
                            uuid_module.UUID(capture_id), uuid_module.UUID(request.session_id),
                        )
            except Exception as e:
                logger.error(f"Auto-capture from teach session failed: {e}")

            summary = f"Great job! You've completed the lesson on '{plan_data['topic']}'. "
            summary += f"We covered {len(chunks)} concepts. "
            if capture_id:
                summary += "Your learning has been captured and review questions have been scheduled."

            return TeachRespondResponse(
                feedback=feedback,
                score=score,
                is_complete=True,
                summary=summary,
                capture_id=capture_id,
            )
        else:
            next_chunk = chunks[next_idx]
            return TeachRespondResponse(
                feedback=feedback,
                score=score,
                is_complete=False,
                current_chunk=next_idx,
                chunk_title=next_chunk["title"],
                chunk_content=next_chunk["content"],
                chunk_analogy=next_chunk.get("analogy"),
                recall_question=next_chunk["recall_question"],
            )

    async def get_session(self, session_id: str) -> TeachSessionResponse:
        """Get current state of a teaching session (for resume)."""
        session = await get_teach_session(self.db_pool, session_id)
        if not session:
            raise ValueError(f"Teaching session not found: {session_id}")

        plan_data = session["plan_json"] if isinstance(session["plan_json"], dict) else json.loads(session["plan_json"])
        chunks = plan_data["chunks"]
        current_idx = session["current_chunk"]
        is_complete = session["status"] == "complete"

        # If complete, show last chunk
        chunk_idx = min(current_idx, len(chunks) - 1)
        chunk = chunks[chunk_idx]

        return TeachSessionResponse(
            session_id=str(session["id"]),
            topic=plan_data["topic"],
            total_chunks=len(chunks),
            current_chunk=current_idx,
            chunk_title=chunk["title"],
            chunk_content=chunk["content"],
            chunk_analogy=chunk.get("analogy"),
            recall_question=chunk["recall_question"],
            is_complete=is_complete,
        )
