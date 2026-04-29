"""
Questions router — question bank management, filtering, stats.
GET  /              → list questions with filters
GET  /stats/summary → question bank overview
GET  /{question_id} → single question detail
PATCH /{question_id} → edit a question
DELETE /{question_id} → delete a question
POST /bulk-delete    → delete multiple questions
POST /{question_id}/reschedule → manual FSRS override
"""
import uuid as uuid_module
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Request, HTTPException, Query

from core.db_queries import (
    list_questions,
    count_questions,
    get_question_detail,
    update_question_fields,
    delete_question,
    bulk_delete_questions,
    reschedule_question,
    get_question_stats_summary,
)
from models.review_models import (
    QuestionListItem,
    QuestionListResponse,
    QuestionDetail,
    ReviewLogEntry,
    QuestionUpdateRequest,
    BulkDeleteRequest,
    RescheduleRequest,
    QuestionStatsSummary,
    QuestionTypeCount,
    QuestionStateCount,
    FailedQuestion,
)

router = APIRouter()


def _validate_uuid(value: str, label: str = "ID") -> None:
    try:
        uuid_module.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {label} format")


def _serialize_dt(val) -> str | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


@router.get("/stats/summary", response_model=QuestionStatsSummary)
async def question_stats_summary(request: Request):
    """Question bank overview stats."""
    data = await get_question_stats_summary(request.app.state.db_pool)
    return QuestionStatsSummary(
        total_questions=data["total_questions"],
        by_type=[QuestionTypeCount(**r) for r in data["by_type"]],
        by_state=[QuestionStateCount(**r) for r in data["by_state"]],
        avg_difficulty=data["avg_difficulty"],
        avg_stability=data["avg_stability"],
        most_failed=[FailedQuestion(
            id=str(r["id"]),
            question_text=r["question_text"],
            accuracy_rate=float(r["accuracy_rate"]),
        ) for r in data["most_failed"]],
    )


@router.get("/", response_model=QuestionListResponse)
async def list_all_questions(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=200),
    question_type: str | None = Query(default=None),
    state: int | None = Query(default=None, ge=0, le=3),
    sort: str = Query(default="created_at"),
    order: str = Query(default="desc"),
    capture_id: str | None = Query(default=None),
    tag: str | None = Query(default=None, max_length=100),
):
    """List all questions with filtering, sorting, and pagination."""
    if capture_id:
        _validate_uuid(capture_id, "capture_id")

    pool = request.app.state.db_pool
    questions = await list_questions(
        pool, limit, offset, search, question_type, state, sort, order, capture_id, tag,
    )
    total = await count_questions(pool, search, question_type, state, capture_id, tag)

    items = [
        QuestionListItem(
            id=str(q["id"]),
            question_text=q["question_text"],
            answer_text=q["answer_text"],
            question_type=q["question_type"],
            technique_used=q.get("technique_used"),
            mnemonic_hint=q.get("mnemonic_hint"),
            state=q["state"],
            due=_serialize_dt(q["due"]),
            stability=q.get("stability"),
            difficulty=q.get("difficulty"),
            last_review=_serialize_dt(q.get("last_review")),
            created_at=_serialize_dt(q["created_at"]),
            capture_id=str(q["capture_id"]) if q.get("capture_id") else None,
            review_count=q["review_count"],
            last_rating=q.get("last_rating"),
            source_text=q.get("source_text"),
        )
        for q in questions
    ]
    return QuestionListResponse(questions=items, total=total)


@router.get("/{question_id}", response_model=QuestionDetail)
async def get_single_question(question_id: str, request: Request):
    """Get a single question with full stats and review history."""
    _validate_uuid(question_id, "question_id")
    data = await get_question_detail(request.app.state.db_pool, question_id)
    if not data:
        raise HTTPException(status_code=404, detail="Question not found")

    return QuestionDetail(
        id=str(data["id"]),
        question_text=data["question_text"],
        answer_text=data["answer_text"],
        question_type=data["question_type"],
        technique_used=data.get("technique_used"),
        mnemonic_hint=data.get("mnemonic_hint"),
        state=data["state"],
        due=_serialize_dt(data["due"]),
        stability=data.get("stability"),
        difficulty=data.get("difficulty"),
        last_review=_serialize_dt(data.get("last_review")),
        created_at=_serialize_dt(data["created_at"]),
        capture_id=str(data["capture_id"]) if data.get("capture_id") else None,
        review_count=data["review_count"],
        last_rating=data.get("last_rating"),
        source_text=data.get("source_text"),
        accuracy_rate=data.get("accuracy_rate"),
        extracted_point_content=data.get("extracted_point_content"),
        capture_raw_text=data.get("capture_raw_text"),
        review_logs=[
            ReviewLogEntry(
                rating=log["rating"],
                user_answer=log.get("user_answer"),
                ai_feedback=log.get("ai_feedback"),
                reviewed_at=_serialize_dt(log["reviewed_at"]),
            )
            for log in data["review_logs"]
        ],
    )


@router.patch("/{question_id}")
async def edit_question(question_id: str, body: QuestionUpdateRequest, request: Request):
    """Edit a question's text, answer, hint, or type."""
    _validate_uuid(question_id, "question_id")
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await update_question_fields(request.app.state.db_pool, question_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Question not found")

    return {
        "id": str(result["id"]),
        "question_text": result["question_text"],
        "answer_text": result["answer_text"],
        "question_type": result["question_type"],
        "technique_used": result.get("technique_used"),
        "mnemonic_hint": result.get("mnemonic_hint"),
        "state": result["state"],
        "due": _serialize_dt(result["due"]),
    }


@router.delete("/{question_id}")
async def delete_single_question(question_id: str, request: Request):
    """Delete a single question."""
    _validate_uuid(question_id, "question_id")
    deleted = await delete_question(request.app.state.db_pool, question_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"deleted": True}


@router.post("/bulk-delete")
async def bulk_delete(body: BulkDeleteRequest, request: Request):
    """Delete multiple questions at once (max 50)."""
    count = await bulk_delete_questions(request.app.state.db_pool, body.question_ids)
    return {"deleted_count": count}


@router.post("/{question_id}/reschedule")
async def reschedule(question_id: str, body: RescheduleRequest, request: Request):
    """Manual FSRS override: reset, review_now, or postpone."""
    _validate_uuid(question_id, "question_id")

    now = datetime.now(timezone.utc)

    if body.action == "reset":
        result = await reschedule_question(
            request.app.state.db_pool, question_id, due=now, state=0, step=0,
        )
    elif body.action == "review_now":
        result = await reschedule_question(
            request.app.state.db_pool, question_id, due=now,
        )
    elif body.action == "postpone":
        if body.days is None:
            raise HTTPException(status_code=400, detail="days is required for postpone action")
        result = await reschedule_question(
            request.app.state.db_pool, question_id, due=now + timedelta(days=body.days),
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    if not result:
        raise HTTPException(status_code=404, detail="Question not found")

    return {
        "id": str(result["id"]),
        "question_text": result["question_text"],
        "state": result["state"],
        "due": _serialize_dt(result["due"]),
        "step": result["step"],
    }
