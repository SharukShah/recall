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
    category: str | None = None,
) -> str:
    """Insert a question with FSRS initial state and return its UUID."""
    question_id = str(uuid.uuid4())
    async with await _acquire(pool_or_conn) as conn:
        await conn.execute(
            """
            INSERT INTO questions (
                id, extracted_point_id, question_text, answer_text,
                question_type, technique_used, mnemonic_hint,
                due, stability, difficulty, step, state, last_review,
                category
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
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
            category,
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

        tags = await conn.fetch(
            """
            SELECT t.name
            FROM tags t
            JOIN capture_tags ct ON ct.tag_id = t.id
            WHERE ct.capture_id = $1
            ORDER BY t.name
            """,
            uid,
        )

    return {
        "capture": dict(capture),
        "facts": [dict(f) for f in facts],
        "questions": [dict(q) for q in questions],
        "tags": [r["name"] for r in tags],
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
    vec_str = "[" + ",".join(str(f) for f in embedding) + "]"
    async with await _acquire(pool_or_conn) as conn:
        await conn.execute(
            "UPDATE extracted_points SET embedding = $1::text::vector WHERE id = $2",
            vec_str,
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
        vec_str = "[" + ",".join(str(f) for f in query_embedding) + "]"
        rows = await conn.fetch(
            """
            SELECT
                ep.id,
                ep.content,
                ep.content_type,
                ep.capture_id,
                ep.created_at,
                1 - (ep.embedding <=> $1::text::vector) AS similarity,
                c.raw_text AS capture_raw_text,
                c.source_type AS capture_source_type,
                c.created_at AS capture_created_at
            FROM extracted_points ep
            JOIN captures c ON c.id = ep.capture_id
            WHERE ep.embedding IS NOT NULL
              AND 1 - (ep.embedding <=> $1::text::vector) >= $3
            ORDER BY ep.embedding <=> $1::text::vector
            LIMIT $2
            """,
            vec_str,
            limit,
            min_similarity,
        )
        return [dict(row) for row in rows]


# ============================================================
# QUESTION MANAGEMENT QUERIES
# ============================================================

_ALLOWED_SORT_FIELDS = {"created_at", "due", "stability", "difficulty"}
_ALLOWED_ORDERS = {"asc", "desc"}


def _build_question_filters(
    search: str | None,
    question_type: str | None,
    state: int | None,
    capture_id: str | None,
    tag: str | None,
) -> tuple[str, list]:
    """Build WHERE clause and params for question list/count queries."""
    conditions = []
    params: list = []
    idx = 1

    if search:
        conditions.append(f"(q.question_text ILIKE ${idx} OR q.answer_text ILIKE ${idx})")
        params.append(f"%{search}%")
        idx += 1

    if question_type:
        conditions.append(f"q.question_type = ${idx}")
        params.append(question_type)
        idx += 1

    if state is not None:
        conditions.append(f"q.state = ${idx}")
        params.append(state)
        idx += 1

    if capture_id:
        conditions.append(f"ep.capture_id = ${idx}")
        params.append(uuid.UUID(capture_id))
        idx += 1

    if tag:
        conditions.append(f"""EXISTS (
            SELECT 1 FROM capture_tags ct
            JOIN tags t ON t.id = ct.tag_id
            WHERE ct.capture_id = ep.capture_id AND t.name = ${idx}
        )""")
        params.append(tag)
        idx += 1

    where = " AND ".join(conditions) if conditions else "TRUE"
    return where, params


async def list_questions(
    pool: asyncpg.Pool,
    limit: int = 20,
    offset: int = 0,
    search: str | None = None,
    question_type: str | None = None,
    state: int | None = None,
    sort: str = "created_at",
    order: str = "desc",
    capture_id: str | None = None,
    tag: str | None = None,
) -> list[dict]:
    """List questions with filtering, sorting, and pagination."""
    sort_field = sort if sort in _ALLOWED_SORT_FIELDS else "created_at"
    sort_order = order.upper() if order.lower() in _ALLOWED_ORDERS else "DESC"

    where, params = _build_question_filters(search, question_type, state, capture_id, tag)
    next_idx = len(params) + 1

    sql = f"""
        SELECT q.id, q.question_text, q.answer_text, q.question_type,
               q.technique_used, q.mnemonic_hint,
               q.state, q.due, q.stability, q.difficulty, q.last_review, q.created_at,
               ep.capture_id,
               LEFT(c.raw_text, 100) AS source_text,
               COALESCE(rl_agg.review_count, 0) AS review_count,
               rl_agg.last_rating
        FROM questions q
        JOIN extracted_points ep ON q.extracted_point_id = ep.id
        JOIN captures c ON ep.capture_id = c.id
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS review_count,
                   (SELECT rating FROM review_logs
                    WHERE question_id = q.id
                    ORDER BY reviewed_at DESC LIMIT 1) AS last_rating
            FROM review_logs WHERE question_id = q.id
        ) rl_agg ON TRUE
        WHERE {where}
        ORDER BY q.{sort_field} {sort_order}
        LIMIT ${next_idx} OFFSET ${next_idx + 1}
    """
    params.extend([limit, offset])

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    return [dict(r) for r in rows]


async def count_questions(
    pool: asyncpg.Pool,
    search: str | None = None,
    question_type: str | None = None,
    state: int | None = None,
    capture_id: str | None = None,
    tag: str | None = None,
) -> int:
    """Count questions matching filters."""
    where, params = _build_question_filters(search, question_type, state, capture_id, tag)

    sql = f"""
        SELECT COUNT(*)
        FROM questions q
        JOIN extracted_points ep ON q.extracted_point_id = ep.id
        WHERE {where}
    """

    async with pool.acquire() as conn:
        return await conn.fetchval(sql, *params)


async def get_question_detail(pool: asyncpg.Pool, question_id: str) -> dict | None:
    """Get a single question with full stats, review logs, and capture info."""
    uid = uuid.UUID(question_id)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT q.id, q.question_text, q.answer_text, q.question_type,
                   q.technique_used, q.mnemonic_hint,
                   q.state, q.due, q.stability, q.difficulty, q.last_review, q.created_at,
                   ep.capture_id, ep.content AS extracted_point_content,
                   c.raw_text AS capture_raw_text,
                   LEFT(c.raw_text, 100) AS source_text
            FROM questions q
            JOIN extracted_points ep ON q.extracted_point_id = ep.id
            JOIN captures c ON ep.capture_id = c.id
            WHERE q.id = $1
            """,
            uid,
        )
        if not row:
            return None

        logs = await conn.fetch(
            """
            SELECT rating, user_answer, ai_feedback, reviewed_at
            FROM review_logs
            WHERE question_id = $1
            ORDER BY reviewed_at DESC
            """,
            uid,
        )

        review_count = len(logs)
        last_rating = logs[0]["rating"] if logs else None
        total_reviews = len(logs)
        good_reviews = sum(1 for l in logs if l["rating"] >= 3)
        accuracy_rate = round(good_reviews * 100.0 / total_reviews, 1) if total_reviews > 0 else None

    result = dict(row)
    result["review_logs"] = [dict(l) for l in logs]
    result["review_count"] = review_count
    result["last_rating"] = last_rating
    result["accuracy_rate"] = accuracy_rate
    return result


async def update_question_fields(
    pool: asyncpg.Pool,
    question_id: str,
    updates: dict,
) -> dict | None:
    """Partially update a question's editable fields. Returns updated row."""
    allowed = {"question_text", "answer_text", "mnemonic_hint", "question_type"}
    filtered = {k: v for k, v in updates.items() if k in allowed and v is not None}
    if not filtered:
        return await get_question_by_id(pool, question_id)

    set_parts = []
    params = [uuid.UUID(question_id)]
    for i, (col, val) in enumerate(filtered.items(), start=2):
        set_parts.append(f"{col} = ${i}")
        params.append(val)

    sql = f"""
        UPDATE questions SET {', '.join(set_parts)}
        WHERE id = $1
        RETURNING id, question_text, answer_text, question_type,
                  technique_used, mnemonic_hint,
                  due, stability, difficulty, step, state, last_review, created_at
    """

    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, *params)
    return dict(row) if row else None


async def delete_question(pool: asyncpg.Pool, question_id: str) -> bool:
    """Delete a single question. Returns True if deleted."""
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM questions WHERE id = $1",
            uuid.UUID(question_id),
        )
    return result == "DELETE 1"


async def bulk_delete_questions(pool: asyncpg.Pool, question_ids: list[str]) -> int:
    """Delete multiple questions. Returns count of deleted rows."""
    uuids = [uuid.UUID(qid) for qid in question_ids]
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM questions WHERE id = ANY($1::uuid[])",
            uuids,
        )
    # result looks like "DELETE N"
    return int(result.split(" ")[1])


async def reschedule_question(
    pool: asyncpg.Pool,
    question_id: str,
    due: datetime,
    state: int | None = None,
    step: int | None = None,
) -> dict | None:
    """Update FSRS scheduling fields for manual reschedule. Returns updated row."""
    uid = uuid.UUID(question_id)
    async with pool.acquire() as conn:
        if state is not None and step is not None:
            row = await conn.fetchrow(
                """
                UPDATE questions SET due = $2, state = $3, step = $4
                WHERE id = $1
                RETURNING id, question_text, answer_text, question_type,
                          technique_used, mnemonic_hint,
                          due, stability, difficulty, step, state, last_review, created_at
                """,
                uid, due, state, step,
            )
        else:
            row = await conn.fetchrow(
                """
                UPDATE questions SET due = $2
                WHERE id = $1
                RETURNING id, question_text, answer_text, question_type,
                          technique_used, mnemonic_hint,
                          due, stability, difficulty, step, state, last_review, created_at
                """,
                uid, due,
            )
    return dict(row) if row else None


async def get_question_stats_summary(pool: asyncpg.Pool) -> dict:
    """Get question bank overview stats."""
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM questions")

        by_type = await conn.fetch(
            "SELECT question_type, COUNT(*) AS count FROM questions GROUP BY question_type"
        )

        by_state = await conn.fetch(
            "SELECT state, COUNT(*) AS count FROM questions GROUP BY state"
        )

        avgs = await conn.fetchrow(
            "SELECT AVG(difficulty) AS avg_difficulty, AVG(stability) AS avg_stability FROM questions"
        )

        most_failed = await conn.fetch(
            """
            SELECT q.id, q.question_text,
                   ROUND(COUNT(*) FILTER (WHERE rl.rating >= 3) * 100.0 / NULLIF(COUNT(*), 0), 1) AS accuracy_rate
            FROM questions q
            JOIN review_logs rl ON rl.question_id = q.id
            GROUP BY q.id, q.question_text
            HAVING COUNT(*) >= 2
            ORDER BY accuracy_rate ASC
            LIMIT 5
            """
        )

    return {
        "total_questions": total or 0,
        "by_type": [dict(r) for r in by_type],
        "by_state": [dict(r) for r in by_state],
        "avg_difficulty": float(avgs["avg_difficulty"]) if avgs["avg_difficulty"] is not None else None,
        "avg_stability": float(avgs["avg_stability"]) if avgs["avg_stability"] is not None else None,
        "most_failed": [dict(r) for r in most_failed],
    }


# ============================================================
# TAG QUERIES
# ============================================================

async def list_all_tags(pool: asyncpg.Pool) -> list[dict]:
    """List all tags with usage counts."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT t.id, t.name, COUNT(ct.capture_id) AS count
            FROM tags t
            LEFT JOIN capture_tags ct ON ct.tag_id = t.id
            GROUP BY t.id, t.name
            ORDER BY count DESC, t.name ASC
            """
        )
    return [{"id": str(r["id"]), "name": r["name"], "count": r["count"]} for r in rows]


async def set_capture_tags(
    pool_or_conn: PoolOrConn,
    capture_id: str,
    tag_names: list[str],
) -> list[str]:
    """
    Set tags for a capture (replaces existing).
    Creates new tags if they don't exist.
    Returns the final list of tag names.
    """
    async with await _acquire(pool_or_conn) as conn:
        uid = uuid.UUID(capture_id)

        # Remove existing tags for this capture
        await conn.execute(
            "DELETE FROM capture_tags WHERE capture_id = $1", uid
        )

        if not tag_names:
            return []

        result_tags = []
        for name in tag_names:
            name = name.strip()
            if not name:
                continue
            # Upsert the tag
            tag_id = await conn.fetchval(
                """
                INSERT INTO tags (id, name)
                VALUES ($1, $2)
                ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                uuid.uuid4(), name,
            )
            # Link to capture
            await conn.execute(
                """
                INSERT INTO capture_tags (capture_id, tag_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                """,
                uid, tag_id,
            )
            result_tags.append(name)

        return result_tags


# ============================================================
# INTERVIEW PREP QUERIES
# ============================================================

async def get_topic_coverage(pool: asyncpg.Pool) -> dict:
    """Get question coverage stats grouped by category."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                q.category,
                COUNT(*) AS total_questions,
                COUNT(DISTINCT CASE WHEN rl.id IS NOT NULL THEN q.id END) AS reviewed_count,
                COUNT(CASE WHEN q.state = 2 THEN 1 END) AS mastered_count,
                COUNT(CASE WHEN recent_rl.retention < 0.7 THEN 1 END) AS weak_count,
                MAX(rl.reviewed_at) AS last_reviewed
            FROM questions q
            LEFT JOIN review_logs rl ON rl.question_id = q.id
            LEFT JOIN LATERAL (
                SELECT
                    CASE WHEN COUNT(*) > 0
                         THEN SUM(CASE WHEN rating >= 3 THEN 1 ELSE 0 END)::float / COUNT(*)
                         ELSE 1.0
                    END AS retention
                FROM review_logs
                WHERE question_id = q.id AND reviewed_at >= NOW() - INTERVAL '30 days'
            ) recent_rl ON true
            WHERE q.category IS NOT NULL
            GROUP BY q.category
            ORDER BY q.category
            """
        )
        uncategorized = await conn.fetchval(
            "SELECT COUNT(*) FROM questions WHERE category IS NULL"
        )
    return {
        "categories": [dict(r) for r in rows],
        "uncategorized_count": uncategorized or 0,
    }


async def get_weak_categories(pool: asyncpg.Pool) -> list[dict]:
    """Get categories with low retention for weakness detection."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH category_stats AS (
                SELECT
                    q.category,
                    COUNT(DISTINCT q.id) AS total_questions,
                    AVG(CASE WHEN rl.rating >= 3 THEN 1.0 ELSE 0.0 END) AS avg_retention,
                    AVG(CASE WHEN rl.rating = 1 THEN 1.0 ELSE 0.0 END) AS fail_rate
                FROM questions q
                JOIN review_logs rl ON rl.question_id = q.id
                WHERE q.category IS NOT NULL
                  AND rl.reviewed_at >= NOW() - INTERVAL '30 days'
                GROUP BY q.category
                HAVING COUNT(DISTINCT q.id) >= 3
            )
            SELECT
                category,
                total_questions,
                avg_retention,
                fail_rate,
                CASE
                    WHEN avg_retention >= 0.85 THEN 'You''re strong here'
                    WHEN avg_retention >= 0.70 THEN 'Review more'
                    ELSE 'Practice daily'
                END AS suggested_action
            FROM category_stats
            ORDER BY avg_retention ASC
            """
        )
    return [dict(r) for r in rows]


async def get_due_questions_by_category(
    pool: asyncpg.Pool,
    categories: list[str],
    limit: int = 10,
) -> list[dict]:
    """Get due questions filtered by categories."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, question_text, question_type, mnemonic_hint, technique_used,
                   state, due, category
            FROM questions
            WHERE (state IN (0, 1, 3) OR (state = 2 AND due <= NOW()))
              AND category = ANY($2)
            ORDER BY
                CASE state WHEN 3 THEN 1 WHEN 1 THEN 2 WHEN 0 THEN 3 WHEN 2 THEN 4 END,
                due ASC
            LIMIT $1
            """,
            limit, categories,
        )
    return [dict(r) for r in rows]


# -- Mock Interview Queries --

async def create_mock_interview(
    pool_or_conn: PoolOrConn,
    topic: str,
    difficulty: str,
    duration_minutes: int,
) -> str:
    """Create a mock interview session. Returns its UUID."""
    interview_id = str(uuid.uuid4())
    async with await _acquire(pool_or_conn) as conn:
        await conn.execute(
            """
            INSERT INTO mock_interviews (id, topic, difficulty, duration_minutes)
            VALUES ($1, $2, $3, $4)
            """,
            uuid.UUID(interview_id), topic, difficulty, duration_minutes,
        )
    return interview_id


async def insert_interview_answers(
    pool_or_conn: PoolOrConn,
    interview_id: str,
    questions: list[dict],
) -> None:
    """Bulk insert interview answer rows (question_text, expected_answer, order)."""
    async with await _acquire(pool_or_conn) as conn:
        for q in questions:
            await conn.execute(
                """
                INSERT INTO interview_answers
                    (id, interview_id, question_id, question_text, expected_answer, question_order)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                uuid.uuid4(),
                uuid.UUID(interview_id),
                uuid.UUID(q["question_id"]) if q.get("question_id") else None,
                q["question_text"],
                q["expected_answer"],
                q["question_order"],
            )


async def get_interview_answer(
    pool: asyncpg.Pool,
    interview_id: str,
    question_order: int,
) -> dict | None:
    """Fetch a specific answer row by interview + order."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, interview_id, question_id, question_text, expected_answer,
                   user_answer, score, feedback, follow_up_asked,
                   follow_up_answer, follow_up_feedback, question_order, answered_at
            FROM interview_answers
            WHERE interview_id = $1 AND question_order = $2
            """,
            uuid.UUID(interview_id), question_order,
        )
    return dict(row) if row else None


async def update_interview_answer(
    pool_or_conn: PoolOrConn,
    answer_id: str,
    user_answer: str | None = None,
    score: int | None = None,
    feedback: str | None = None,
    follow_up_asked: bool | None = None,
    follow_up_answer: str | None = None,
    follow_up_feedback: str | None = None,
) -> None:
    """Update an interview answer with score/feedback."""
    set_parts = []
    params: list = [uuid.UUID(answer_id)]
    idx = 2
    if user_answer is not None:
        set_parts.append(f"user_answer = ${idx}")
        params.append(user_answer)
        idx += 1
    if score is not None:
        set_parts.append(f"score = ${idx}")
        params.append(score)
        idx += 1
    if feedback is not None:
        set_parts.append(f"feedback = ${idx}")
        params.append(feedback)
        idx += 1
    if follow_up_asked is not None:
        set_parts.append(f"follow_up_asked = ${idx}")
        params.append(follow_up_asked)
        idx += 1
    if follow_up_answer is not None:
        set_parts.append(f"follow_up_answer = ${idx}")
        params.append(follow_up_answer)
        idx += 1
    if follow_up_feedback is not None:
        set_parts.append(f"follow_up_feedback = ${idx}")
        params.append(follow_up_feedback)
        idx += 1
    set_parts.append(f"answered_at = NOW()")

    if not set_parts:
        return
    sql = f"UPDATE interview_answers SET {', '.join(set_parts)} WHERE id = $1"
    async with await _acquire(pool_or_conn) as conn:
        await conn.execute(sql, *params)


async def complete_mock_interview(
    pool_or_conn: PoolOrConn,
    interview_id: str,
    overall_score: float,
    strengths: list,
    weaknesses: list,
    improvement_tips: list,
    total_questions: int,
    correct_count: int,
    partial_count: int,
    wrong_count: int,
) -> None:
    """Finalize a mock interview with scores and summary."""
    import json as _json
    async with await _acquire(pool_or_conn) as conn:
        await conn.execute(
            """
            UPDATE mock_interviews
            SET status = 'completed',
                overall_score = $2,
                strengths = $3,
                weaknesses = $4,
                improvement_tips = $5,
                total_questions = $6,
                correct_count = $7,
                partial_count = $8,
                wrong_count = $9,
                completed_at = NOW()
            WHERE id = $1
            """,
            uuid.UUID(interview_id),
            overall_score,
            _json.dumps(strengths),
            _json.dumps(weaknesses),
            _json.dumps(improvement_tips),
            total_questions,
            correct_count,
            partial_count,
            wrong_count,
        )


async def list_mock_interviews(
    pool: asyncpg.Pool,
    topic: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> dict:
    """List mock interviews with optional topic filter. Returns items + total."""
    async with pool.acquire() as conn:
        if topic:
            rows = await conn.fetch(
                """
                SELECT id, topic, difficulty, overall_score, total_questions,
                       correct_count, status, started_at, completed_at
                FROM mock_interviews
                WHERE topic = $3
                ORDER BY started_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit, offset, topic,
            )
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM mock_interviews WHERE topic = $1", topic,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, topic, difficulty, overall_score, total_questions,
                       correct_count, status, started_at, completed_at
                FROM mock_interviews
                ORDER BY started_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit, offset,
            )
            total = await conn.fetchval("SELECT COUNT(*) FROM mock_interviews")
    return {"interviews": [dict(r) for r in rows], "total": total or 0}


async def get_interview_detail(pool: asyncpg.Pool, interview_id: str) -> dict | None:
    """Fetch interview with all answers."""
    uid = uuid.UUID(interview_id)
    async with pool.acquire() as conn:
        interview = await conn.fetchrow(
            """
            SELECT id, topic, difficulty, duration_minutes, status, overall_score,
                   strengths, weaknesses, improvement_tips,
                   total_questions, correct_count, partial_count, wrong_count,
                   started_at, completed_at
            FROM mock_interviews WHERE id = $1
            """,
            uid,
        )
        if not interview:
            return None
        answers = await conn.fetch(
            """
            SELECT question_text, expected_answer, user_answer, score, feedback,
                   follow_up_asked, follow_up_answer, follow_up_feedback, question_order
            FROM interview_answers
            WHERE interview_id = $1
            ORDER BY question_order
            """,
            uid,
        )
    result = dict(interview)
    result["answers"] = [dict(a) for a in answers]
    return result


# -- Streak Queries --

async def get_streak_info(pool: asyncpg.Pool) -> dict:
    """Get current/longest streak and milestones."""
    async with pool.acquire() as conn:
        # Current streak
        current_streak = await conn.fetchval(
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
            WHERE grp = (SELECT grp FROM streak WHERE d = CURRENT_DATE LIMIT 1)
            """
        ) or 0

        # Longest streak
        longest_streak = await conn.fetchval(
            """
            WITH review_dates AS (
                SELECT DISTINCT reviewed_at::date AS review_date FROM review_logs ORDER BY review_date
            ),
            streak_groups AS (
                SELECT review_date,
                       review_date - (ROW_NUMBER() OVER (ORDER BY review_date))::int * INTERVAL '1 day' AS grp
                FROM review_dates
            ),
            streak_lengths AS (
                SELECT COUNT(*) AS streak_length FROM streak_groups GROUP BY grp
            )
            SELECT COALESCE(MAX(streak_length), 0) FROM streak_lengths
            """
        ) or 0

        # streak_at_risk: no reviews today
        reviews_today = await conn.fetchval(
            "SELECT COUNT(*) FROM review_logs WHERE reviewed_at::date = CURRENT_DATE"
        ) or 0
        streak_at_risk = reviews_today == 0

        # Milestones achieved
        milestones = await conn.fetch(
            "SELECT milestone, achieved_at FROM streak_milestones ORDER BY milestone"
        )

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "streak_at_risk": streak_at_risk,
        "milestones": [dict(m) for m in milestones],
    }


async def insert_streak_milestone(pool: asyncpg.Pool, milestone: int) -> None:
    """Insert a new streak milestone if not already achieved."""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO streak_milestones (id, milestone)
            VALUES ($1, $2)
            ON CONFLICT (milestone) DO NOTHING
            """,
            uuid.uuid4(), milestone,
        )


# -- STAR Story Queries --

async def create_star_story(
    pool_or_conn: PoolOrConn,
    capture_id: str | None,
    title: str,
    situation: str,
    task: str,
    action: str,
    result: str,
    competency: str,
    strength_rating: int,
) -> str:
    """Insert a STAR story. Returns its UUID."""
    story_id = str(uuid.uuid4())
    async with await _acquire(pool_or_conn) as conn:
        await conn.execute(
            """
            INSERT INTO star_stories
                (id, capture_id, title, situation, task, action, result, competency, strength_rating)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            uuid.UUID(story_id),
            uuid.UUID(capture_id) if capture_id else None,
            title, situation, task, action, result, competency, strength_rating,
        )
    return story_id


# ============================================================
# REFLECTION QUERIES
# ============================================================

async def insert_reflection(pool_or_conn: PoolOrConn, content: str) -> str:
    """Insert a new reflection. Returns its UUID."""
    reflection_id = str(uuid.uuid4())
    async with await _acquire(pool_or_conn) as conn:
        await conn.execute(
            "INSERT INTO reflections (id, content) VALUES ($1, $2)",
            uuid.UUID(reflection_id), content,
        )
    return reflection_id


async def update_reflection_capture(
    pool_or_conn: PoolOrConn, reflection_id: str, capture_id: str
) -> None:
    """Link a reflection to a capture."""
    async with await _acquire(pool_or_conn) as conn:
        await conn.execute(
            "UPDATE reflections SET capture_id = $1 WHERE id = $2",
            uuid.UUID(capture_id), uuid.UUID(reflection_id),
        )


async def has_reflected_today(pool_or_conn: PoolOrConn) -> bool:
    """Check if the user has already reflected today."""
    async with await _acquire(pool_or_conn) as conn:
        return await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM reflections WHERE date(created_at AT TIME ZONE 'UTC') = CURRENT_DATE)"
        )


async def get_reflection_streak(pool_or_conn: PoolOrConn) -> int:
    """Get consecutive days of reflection (including today)."""
    async with await _acquire(pool_or_conn) as conn:
        row = await conn.fetchval("""
            WITH reflection_dates AS (
                SELECT DISTINCT date(created_at AT TIME ZONE 'UTC') AS d FROM reflections
            ),
            numbered AS (
                SELECT d, d - (ROW_NUMBER() OVER (ORDER BY d DESC))::int AS grp
                FROM reflection_dates
                WHERE d <= CURRENT_DATE
            )
            SELECT COUNT(*) FROM numbered
            WHERE grp = (SELECT grp FROM numbered WHERE d = CURRENT_DATE LIMIT 1)
        """)
    return row or 0


async def get_last_reflection_at(pool_or_conn: PoolOrConn):
    """Get the timestamp of the most recent reflection."""
    async with await _acquire(pool_or_conn) as conn:
        return await conn.fetchval(
            "SELECT created_at FROM reflections ORDER BY created_at DESC LIMIT 1"
        )


async def list_reflections(pool_or_conn: PoolOrConn, limit: int, offset: int) -> list:
    """List reflections, newest first."""
    async with await _acquire(pool_or_conn) as conn:
        return await conn.fetch(
            "SELECT id, content, capture_id, created_at FROM reflections ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            limit, offset,
        )


# ============================================================
# TEACH SESSION QUERIES
# ============================================================

async def insert_teach_session(pool_or_conn: PoolOrConn, topic: str, plan_json: dict) -> str:
    """Insert a new teach session. Returns its UUID."""
    import json as _json
    session_id = str(uuid.uuid4())
    async with await _acquire(pool_or_conn) as conn:
        await conn.execute(
            "INSERT INTO teach_sessions (id, topic, plan_json) VALUES ($1, $2, $3::jsonb)",
            uuid.UUID(session_id), topic, _json.dumps(plan_json),
        )
    return session_id


async def get_teach_session(pool_or_conn: PoolOrConn, session_id: str):
    """Get a teach session by ID."""
    async with await _acquire(pool_or_conn) as conn:
        return await conn.fetchrow(
            "SELECT id, topic, plan_json, current_chunk, status, capture_id, created_at FROM teach_sessions WHERE id = $1",
            uuid.UUID(session_id),
        )


async def get_teach_session_for_update(conn: asyncpg.Connection, session_id: str):
    """Get a teach session with FOR UPDATE lock (use inside a transaction)."""
    return await conn.fetchrow(
        "SELECT id, topic, plan_json, current_chunk, status, capture_id, created_at FROM teach_sessions WHERE id = $1 FOR UPDATE",
        uuid.UUID(session_id),
    )


async def update_teach_session_chunk(conn: asyncpg.Connection, session_id: str, chunk_index: int) -> None:
    """Advance a teach session to a new chunk index."""
    await conn.execute(
        "UPDATE teach_sessions SET current_chunk = $2, updated_at = NOW() WHERE id = $1",
        uuid.UUID(session_id), chunk_index,
    )


async def complete_teach_session(conn: asyncpg.Connection, session_id: str, capture_id: str | None) -> None:
    """Mark a teach session as complete."""
    await conn.execute(
        "UPDATE teach_sessions SET status = 'complete', capture_id = $2, updated_at = NOW() WHERE id = $1",
        uuid.UUID(session_id), uuid.UUID(capture_id) if capture_id else None,
    )


async def list_star_stories(
    pool: asyncpg.Pool,
    competency: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """List STAR stories with optional competency filter. Returns items + total."""
    async with pool.acquire() as conn:
        if competency:
            rows = await conn.fetch(
                """
                SELECT id, title, competency, strength_rating, times_practiced, created_at
                FROM star_stories
                WHERE competency = $3
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit, offset, competency,
            )
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM star_stories WHERE competency = $1", competency,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, title, competency, strength_rating, times_practiced, created_at
                FROM star_stories
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit, offset,
            )
            total = await conn.fetchval("SELECT COUNT(*) FROM star_stories")
    return {"stories": [dict(r) for r in rows], "total": total or 0}


async def get_star_story(pool: asyncpg.Pool, story_id: str) -> dict | None:
    """Fetch a single STAR story."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, capture_id, title, situation, task, action, result,
                   competency, strength_rating, times_practiced, last_practiced_at,
                   created_at, updated_at
            FROM star_stories WHERE id = $1
            """,
            uuid.UUID(story_id),
        )
    return dict(row) if row else None


async def update_star_story(
    pool: asyncpg.Pool,
    story_id: str,
    updates: dict,
) -> dict | None:
    """Partially update a STAR story. Returns updated row."""
    allowed = {"title", "situation", "task", "action", "result", "competency", "strength_rating"}
    filtered = {k: v for k, v in updates.items() if k in allowed and v is not None}
    if not filtered:
        return await get_star_story(pool, story_id)

    set_parts = ["updated_at = NOW()"]
    params: list = [uuid.UUID(story_id)]
    for i, (col, val) in enumerate(filtered.items(), start=2):
        set_parts.append(f"{col} = ${i}")
        params.append(val)

    sql = f"""
        UPDATE star_stories SET {', '.join(set_parts)}
        WHERE id = $1
        RETURNING id, capture_id, title, situation, task, action, result,
                  competency, strength_rating, times_practiced, last_practiced_at,
                  created_at, updated_at
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, *params)
    return dict(row) if row else None


async def delete_star_story(pool: asyncpg.Pool, story_id: str) -> bool:
    """Delete a STAR story. Returns True if deleted."""
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM star_stories WHERE id = $1",
            uuid.UUID(story_id),
        )
    return result == "DELETE 1"


async def get_behavioral_coverage(pool: asyncpg.Pool) -> list[dict]:
    """Get competency coverage summary across all 8 competencies."""
    all_competencies = [
        "leadership", "teamwork", "conflict_resolution", "problem_solving",
        "communication", "adaptability", "initiative", "failure_handling",
    ]
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT competency,
                   COUNT(*) AS story_count,
                   AVG(strength_rating) AS avg_strength,
                   MAX(last_practiced_at) AS last_practiced
            FROM star_stories
            GROUP BY competency
            """
        )
    existing = {r["competency"]: dict(r) for r in rows}
    result = []
    for c in all_competencies:
        if c in existing:
            result.append(existing[c])
        else:
            result.append({
                "competency": c,
                "story_count": 0,
                "avg_strength": None,
                "last_practiced": None,
            })
    return result


async def increment_story_practice(pool: asyncpg.Pool, story_id: str) -> None:
    """Bump times_practiced and set last_practiced_at for a story."""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE star_stories
            SET times_practiced = times_practiced + 1,
                last_practiced_at = NOW()
            WHERE id = $1
            """,
            uuid.UUID(story_id),
        )
