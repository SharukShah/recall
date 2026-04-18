"""
All raw SQL queries using asyncpg.
Parameterized queries only — no string concatenation.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Union
import asyncpg

# Type alias: functions accept either a Pool or a Connection
PoolOrConn = Union[asyncpg.Pool, asyncpg.Connection]


async def _acquire(pool_or_conn: PoolOrConn):
    """Context manager that acquires a connection from a pool, or yields the connection directly."""
    if isinstance(pool_or_conn, asyncpg.Pool):
        return pool_or_conn.acquire()
    # Wrap a raw connection in a passthrough async context manager
    class _PassThrough:
        async def __aenter__(self):
            return pool_or_conn
        async def __aexit__(self, *args):
            pass
    return _PassThrough()


# ============================================================
# CAPTURE QUERIES
# ============================================================

async def insert_capture(
    pool_or_conn: PoolOrConn,
    raw_text: str,
    source_type: str,
    why_it_matters: str | None,
) -> str:
    """Insert a raw capture and return its UUID."""
    capture_id = str(uuid.uuid4())
    async with await _acquire(pool_or_conn) as conn:
        await conn.execute(
            """
            INSERT INTO captures (id, raw_text, source_type, why_it_matters)
            VALUES ($1, $2, $3, $4)
            """,
            uuid.UUID(capture_id), raw_text, source_type, why_it_matters,
        )
    return capture_id


async def insert_extracted_point(
    pool_or_conn: PoolOrConn,
    capture_id: str,
    content: str,
    content_type: str,
) -> str:
    """Insert an extracted knowledge point and return its UUID."""
    point_id = str(uuid.uuid4())
    async with await _acquire(pool_or_conn) as conn:
        await conn.execute(
            """
            INSERT INTO extracted_points (id, capture_id, content, content_type)
            VALUES ($1, $2, $3, $4)
            """,
            uuid.UUID(point_id), uuid.UUID(capture_id), content, content_type,
        )
    return point_id


async def insert_question(
    pool_or_conn: PoolOrConn,
    extracted_point_id: str,
    question_text: str,
    answer_text: str,
    question_type: str,
    technique_used: str | None,
    mnemonic_hint: str | None,
    fsrs_state: dict,
) -> str:
    """Insert a question with FSRS initial state and return its UUID."""
    question_id = str(uuid.uuid4())
    async with await _acquire(pool_or_conn) as conn:
        await conn.execute(
            """
            INSERT INTO questions (
                id, extracted_point_id, question_text, answer_text,
                question_type, technique_used, mnemonic_hint,
                due, stability, difficulty, step, state, last_review
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """,
            uuid.UUID(question_id),
            uuid.UUID(extracted_point_id),
            question_text,
            answer_text,
            question_type,
            technique_used,
            mnemonic_hint,
            fsrs_state["due"],
            fsrs_state["stability"],
            fsrs_state["difficulty"],
            fsrs_state["step"],
            fsrs_state["state"],
            fsrs_state["last_review"],
        )
    return question_id


# ============================================================
# REVIEW QUERIES
# ============================================================

async def get_due_questions(pool: asyncpg.Pool, limit: int = 20) -> list[dict]:
    """
    Get questions due for review, ordered by priority.
    Relearning first, then Learning, then New, then Review.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, question_text, question_type, mnemonic_hint, technique_used,
                   state, due
            FROM questions
            WHERE state IN (0, 1, 3)
               OR (state = 2 AND due <= NOW())
            ORDER BY
                CASE state
                    WHEN 3 THEN 1
                    WHEN 1 THEN 2
                    WHEN 0 THEN 3
                    WHEN 2 THEN 4
                END,
                due ASC
            LIMIT $1
            """,
            limit,
        )
    return [dict(r) for r in rows]


async def count_due_questions(pool: asyncpg.Pool) -> int:
    """Count total questions currently due for review."""
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM questions
            WHERE state IN (0, 1, 3)
               OR (state = 2 AND due <= NOW())
            """
        )
    return count


async def get_question_by_id(pool: asyncpg.Pool, question_id: str) -> dict | None:
    """Fetch a single question by ID (includes FSRS state + answer)."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, question_text, answer_text, question_type,
                   technique_used, mnemonic_hint,
                   due, stability, difficulty, step, state, last_review
            FROM questions
            WHERE id = $1
            """,
            uuid.UUID(question_id),
        )
    return dict(row) if row else None


async def get_question_for_update(conn: asyncpg.Connection, question_id: str) -> dict | None:
    """Fetch a single question by ID with FOR UPDATE row lock (use inside a transaction)."""
    row = await conn.fetchrow(
        """
        SELECT id, question_text, answer_text, question_type,
               technique_used, mnemonic_hint,
               due, stability, difficulty, step, state, last_review
        FROM questions
        WHERE id = $1
        FOR UPDATE
        """,
        uuid.UUID(question_id),
    )
    return dict(row) if row else None


async def update_question_fsrs_state(
    pool_or_conn: PoolOrConn,
    question_id: str,
    fsrs_state: dict,
) -> None:
    """Update a question's FSRS state after a review."""
    async with await _acquire(pool_or_conn) as conn:
        await conn.execute(
            """
            UPDATE questions
            SET due = $2, stability = $3, difficulty = $4,
                step = $5, state = $6, last_review = $7
            WHERE id = $1
            """,
            uuid.UUID(question_id),
            fsrs_state["due"],
            fsrs_state["stability"],
            fsrs_state["difficulty"],
            fsrs_state["step"],
            fsrs_state["state"],
            fsrs_state["last_review"],
        )


async def insert_review_log(
    pool_or_conn: PoolOrConn,
    question_id: str,
    rating: int,
    old_state: int,
    old_stability: float | None,
    old_difficulty: float | None,
    user_answer: str | None = None,
    ai_feedback: str | None = None,
) -> None:
    """Insert a review log entry recording the BEFORE state + rating applied."""
    async with await _acquire(pool_or_conn) as conn:
        await conn.execute(
            """
            INSERT INTO review_logs (
                id, question_id, rating, state,
                stability, difficulty, user_answer, ai_feedback, reviewed_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            """,
            uuid.uuid4(),
            uuid.UUID(question_id),
            rating,
            old_state,
            old_stability,
            old_difficulty,
            user_answer,
            ai_feedback,
        )


# ============================================================
# STATS QUERIES
# ============================================================

async def get_dashboard_stats(pool: asyncpg.Pool) -> dict:
    """Get dashboard statistics."""
    async with pool.acquire() as conn:
        due_today = await conn.fetchval(
            """
            SELECT COUNT(*) FROM questions
            WHERE state IN (0, 1, 3)
               OR (state = 2 AND due <= NOW())
            """
        )
        total_captures = await conn.fetchval("SELECT COUNT(*) FROM captures")
        total_questions = await conn.fetchval("SELECT COUNT(*) FROM questions")
        reviews_today = await conn.fetchval(
            """
            SELECT COUNT(*) FROM review_logs
            WHERE reviewed_at >= CURRENT_DATE
            """
        )
        # Streak: count consecutive days with reviews going backwards from today
        streak = await conn.fetchval(
            """
            WITH review_dates AS (
                SELECT DISTINCT reviewed_at::date AS d FROM review_logs
            ),
            streak AS (
                SELECT d, d - (ROW_NUMBER() OVER (ORDER BY d DESC))::int AS grp
                FROM review_dates
                WHERE d <= CURRENT_DATE
            )
            SELECT COUNT(*) FROM streak
            WHERE grp = (
                SELECT grp FROM streak WHERE d = CURRENT_DATE
                LIMIT 1
            )
            """
        )
        # Retention rate: percentage of reviews rated >= 3 (Good or Easy)
        retention_rate = await conn.fetchval(
            """
            SELECT CASE
                WHEN COUNT(*) = 0 THEN NULL
                ELSE ROUND(COUNT(*) FILTER (WHERE rating >= 3) * 100.0 / COUNT(*), 1)
            END
            FROM review_logs
            """
        )

    return {
        "due_today": due_today or 0,
        "total_captures": total_captures or 0,
        "total_questions": total_questions or 0,
        "reviews_today": reviews_today or 0,
        "streak_days": streak or 0,
        "retention_rate": float(retention_rate) if retention_rate is not None else None,
    }


# ============================================================
# CAPTURE LIST/DETAIL QUERIES
# ============================================================

async def list_captures(pool: asyncpg.Pool, limit: int = 20, offset: int = 0) -> list[dict]:
    """List recent captures with fact count."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT c.id, c.raw_text, c.source_type, c.created_at,
                   COUNT(ep.id) AS facts_count
            FROM captures c
            LEFT JOIN extracted_points ep ON ep.capture_id = c.id
            GROUP BY c.id
            ORDER BY c.created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset,
        )
    return [dict(r) for r in rows]


async def get_capture_detail(pool: asyncpg.Pool, capture_id: str) -> dict | None:
    """Get a capture with its extracted facts and questions."""
    uid = uuid.UUID(capture_id)
    async with pool.acquire() as conn:
        capture = await conn.fetchrow(
            "SELECT id, raw_text, source_type, why_it_matters, created_at FROM captures WHERE id = $1",
            uid,
        )
        if not capture:
            return None

        facts = await conn.fetch(
            "SELECT id, content, content_type, created_at FROM extracted_points WHERE capture_id = $1",
            uid,
        )
        questions = await conn.fetch(
            """
            SELECT q.id, q.question_text, q.answer_text, q.question_type,
                   q.technique_used, q.mnemonic_hint, q.state, q.due
            FROM questions q
            JOIN extracted_points ep ON q.extracted_point_id = ep.id
            WHERE ep.capture_id = $1
            """,
            uid,
        )

    return {
        "capture": dict(capture),
        "facts": [dict(f) for f in facts],
        "questions": [dict(q) for q in questions],
    }


# ============================================================
# EMBEDDING / VECTOR SEARCH QUERIES
# ============================================================

async def update_point_embedding(
    pool_or_conn: PoolOrConn,
    point_id: str,
    embedding: list[float],
) -> None:
    """Set the embedding vector for an extracted_point."""
    async with await _acquire(pool_or_conn) as conn:
        await conn.execute(
            "UPDATE extracted_points SET embedding = $1 WHERE id = $2",
            embedding,
            uuid.UUID(point_id),
        )


async def search_similar_points(
    pool_or_conn: PoolOrConn,
    query_embedding: list[float],
    limit: int = 5,
    min_similarity: float = 0.3,
) -> list[dict]:
    """
    Cosine similarity search against extracted_points embeddings.
    Returns rows with similarity score, joined with capture metadata.
    """
    async with await _acquire(pool_or_conn) as conn:
        rows = await conn.fetch(
            """
            SELECT
                ep.id,
                ep.content,
                ep.content_type,
                ep.capture_id,
                ep.created_at,
                1 - (ep.embedding <=> $1::vector) AS similarity,
                c.raw_text AS capture_raw_text,
                c.source_type AS capture_source_type,
                c.created_at AS capture_created_at
            FROM extracted_points ep
            JOIN captures c ON c.id = ep.capture_id
            WHERE ep.embedding IS NOT NULL
              AND 1 - (ep.embedding <=> $1::vector) >= $3
            ORDER BY ep.embedding <=> $1::vector
            LIMIT $2
            """,
            query_embedding,
            limit,
            min_similarity,
        )
        return [dict(row) for row in rows]
