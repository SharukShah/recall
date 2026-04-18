"""
Capture service — full capture pipeline.
validate → store raw → LLM extract → store facts → LLM questions + technique (parallel) → store questions → response
"""
import asyncio
import logging
import time
from openai import AsyncOpenAI
from fsrs import Scheduler
import asyncpg

from core import llm
from core.embedder import embed_texts
from core.fsrs_engine import create_new_card, card_to_db_dict
from core.db_queries import insert_capture, insert_extracted_point, insert_question, update_point_embedding
from models.capture_models import CaptureRequest, CaptureResponse

logger = logging.getLogger(__name__)


class CaptureService:
    def __init__(self, db_pool: asyncpg.Pool, openai_client: AsyncOpenAI, scheduler: Scheduler):
        self.db_pool = db_pool
        self.openai = openai_client
        self.scheduler = scheduler

    async def process(self, request: CaptureRequest) -> CaptureResponse:
        """
        Full capture pipeline:
        1. LLM extract facts (before any DB writes — prevents orphans)
        2. All DB writes in a single transaction
        3. LLM generate questions + technique (parallel)
        4. Store questions in same transaction
        5. Return response
        """
        start_time = time.time()
        raw_text = request.raw_text.strip()
        why_it_matters = request.why_it_matters.strip() if request.why_it_matters else None

        # Step 1: LLM extract facts BEFORE any DB writes
        try:
            extracted = await llm.extract_facts(
                self.openai, raw_text, why_it_matters,
            )
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            elapsed_ms = int((time.time() - start_time) * 1000)
            return CaptureResponse(
                capture_id="",
                facts_count=0,
                questions_count=0,
                status="extraction_failed",
                processing_time_ms=elapsed_ms,
                message="Extraction failed. No data was saved.",
            )

        if not extracted.facts:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return CaptureResponse(
                capture_id="",
                facts_count=0,
                questions_count=0,
                status="no_facts",
                processing_time_ms=elapsed_ms,
                message="No reviewable facts found. Try being more specific.",
            )

        # Step 2: LLM generate questions + select technique + embed facts (parallel, before DB)
        facts_dicts = [f.model_dump() for f in extracted.facts]
        questions_result = None
        technique_result = None
        embeddings_result = None

        try:
            questions_task = llm.generate_questions(self.openai, facts_dicts)
            technique_task = llm.select_technique(self.openai, facts_dicts)
            embed_task = embed_texts(self.openai, [f.content for f in extracted.facts])
            questions_result, technique_result, embeddings_result = await asyncio.gather(
                questions_task, technique_task, embed_task, return_exceptions=True,
            )
        except Exception as e:
            logger.error(f"Parallel LLM calls failed: {e}")

        if isinstance(questions_result, Exception):
            logger.error(f"Question generation failed: {questions_result}")
            questions_result = None
        if isinstance(technique_result, Exception):
            logger.error(f"Technique selection failed: {technique_result}")
            technique_result = None
        if isinstance(embeddings_result, Exception):
            logger.warning(f"Embedding failed (non-fatal): {embeddings_result}")
            embeddings_result = None

        # Step 3: All DB writes in a single transaction
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                capture_id = await insert_capture(
                    conn, raw_text, request.source_type, why_it_matters,
                )
                logger.info(f"Capture stored: {capture_id}")

                point_ids = []
                for fact in extracted.facts:
                    point_id = await insert_extracted_point(
                        conn, capture_id, fact.content, fact.content_type,
                    )
                    point_ids.append(point_id)
                logger.info(f"Stored {len(point_ids)} facts for capture {capture_id}")

                # Write embeddings if available
                if embeddings_result and len(embeddings_result) == len(point_ids):
                    for point_id, embedding in zip(point_ids, embeddings_result):
                        await update_point_embedding(conn, point_id, embedding)
                    logger.info(f"Embedded {len(embeddings_result)} points for capture {capture_id}")

                if not questions_result or not questions_result.questions:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    return CaptureResponse(
                        capture_id=capture_id,
                        facts_count=len(extracted.facts),
                        questions_count=0,
                        status="complete",
                        processing_time_ms=elapsed_ms,
                        message="Facts extracted but no questions generated.",
                    )

                technique_name = technique_result.technique if technique_result else None
                mnemonic_hint = technique_result.instructions if technique_result else None
                if technique_name == "none":
                    technique_name = None
                    mnemonic_hint = None

                questions_stored = 0
                for question in questions_result.questions[:5]:
                    fact_idx = question.fact_index if 0 <= question.fact_index < len(point_ids) else 0
                    point_id = point_ids[fact_idx] if point_ids else None
                    if not point_id:
                        continue

                    card = create_new_card()
                    fsrs_state = card_to_db_dict(card)

                    try:
                        await insert_question(
                            conn,
                            point_id,
                            question.question_text,
                            question.answer_text,
                            question.question_type,
                            technique_name,
                            mnemonic_hint,
                            fsrs_state,
                        )
                        questions_stored += 1
                    except Exception as e:
                        logger.error(f"Failed to store question: {e}")
                        continue

        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            f"Capture {capture_id} complete: {len(extracted.facts)} facts, "
            f"{questions_stored} questions in {elapsed_ms}ms"
        )

        return CaptureResponse(
            capture_id=capture_id,
            facts_count=len(extracted.facts),
            questions_count=questions_stored,
            status="complete",
            processing_time_ms=elapsed_ms,
        )
