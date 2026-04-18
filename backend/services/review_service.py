"""
Review service — due questions, answer evaluation, FSRS rating.
Follows orchestrator-logic.md Section 3C exactly.
"""
import logging
from openai import AsyncOpenAI
from fsrs import Scheduler
import asyncpg

from core import llm
from core.fsrs_engine import card_from_db_row, card_to_db_dict, review_card, get_state_label, get_scheduled_days
from core.db_queries import (
    get_due_questions,
    count_due_questions,
    get_question_by_id,
    get_question_for_update,
    update_question_fsrs_state,
    insert_review_log,
)
from models.review_models import (
    ReviewQuestion, DueResponse, EvaluateRequest, EvaluateResponse,
    RateRequest, RateResponse,
)

logger = logging.getLogger(__name__)


class ReviewService:
    def __init__(self, db_pool: asyncpg.Pool, openai_client: AsyncOpenAI, scheduler: Scheduler):
        self.db_pool = db_pool
        self.openai = openai_client
        self.scheduler = scheduler

    async def get_due(self, limit: int = 20) -> DueResponse:
        """Get questions due for review, ordered by priority."""
        questions = await get_due_questions(self.db_pool, limit)
        total = await count_due_questions(self.db_pool)

        return DueResponse(
            questions=[
                ReviewQuestion(
                    question_id=str(q["id"]),
                    question_text=q["question_text"],
                    question_type=q["question_type"],
                    mnemonic_hint=q.get("mnemonic_hint"),
                    technique_used=q.get("technique_used"),
                )
                for q in questions
            ],
            total_due=total,
        )

    async def evaluate_answer(self, request: EvaluateRequest) -> EvaluateResponse:
        """
        Evaluate user's answer with LLM.
        Returns correct answer, score, feedback, and suggested rating.
        """
        # Fetch question from DB
        question = await get_question_by_id(self.db_pool, request.question_id)
        if not question:
            raise ValueError(f"Question not found: {request.question_id}")

        # LLM evaluation
        try:
            evaluation = await llm.evaluate_answer(
                self.openai,
                question["question_text"],
                question["answer_text"],
                request.user_answer.strip(),
            )
            return EvaluateResponse(
                correct_answer=question["answer_text"],
                score=evaluation.score,
                feedback=evaluation.feedback,
                suggested_rating=evaluation.suggested_rating,
            )
        except Exception as e:
            logger.error(f"LLM evaluation failed for question {request.question_id}: {e}")
            # Fallback: simple word overlap comparison
            expected_words = set(question["answer_text"].lower().split())
            user_words = set(request.user_answer.lower().split())
            overlap = len(expected_words & user_words) / max(len(expected_words), 1)

            if overlap >= 0.8:
                score, suggested = "correct", 3
            elif overlap >= 0.3:
                score, suggested = "partial", 2
            else:
                score, suggested = "wrong", 1

            return EvaluateResponse(
                correct_answer=question["answer_text"],
                score=score,
                feedback="Could not evaluate with AI. Compare with the correct answer.",
                suggested_rating=suggested,
            )

    async def rate(self, request: RateRequest) -> RateResponse:
        """
        Apply FSRS rating: reconstruct card from DB, apply rating, persist new state.
        Uses SELECT FOR UPDATE to prevent race conditions.
        """
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # Fetch current FSRS state with row lock
                question = await get_question_for_update(conn, request.question_id)
                if not question:
                    raise ValueError(f"Question not found: {request.question_id}")

                # Save old state for review log
                old_state = question["state"]
                old_stability = question["stability"]
                old_difficulty = question["difficulty"]

                # Reconstruct card from DB row
                card = card_from_db_row(question)

                # Apply FSRS rating
                updated_card, review_log = review_card(self.scheduler, card, request.rating)

                # Persist updated FSRS state
                new_state = card_to_db_dict(updated_card)
                await update_question_fsrs_state(conn, request.question_id, new_state)

                # Insert review log (records BEFORE state + rating)
                await insert_review_log(
                    conn,
                    request.question_id,
                    request.rating,
                    old_state,
                    old_stability,
                    old_difficulty,
                    user_answer=request.user_answer,
                    ai_feedback=request.ai_feedback,
                )

        interval_days = get_scheduled_days(updated_card)

        logger.info(
            f"Rated question {request.question_id}: rating={request.rating}, "
            f"next_due={updated_card.due}, interval={interval_days:.1f}d"
        )

        return RateResponse(
            next_due=updated_card.due.isoformat(),
            interval_days=interval_days,
            state=new_state["state"],
            state_label=get_state_label(new_state["state"]),
        )
