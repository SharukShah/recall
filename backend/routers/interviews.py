"""
Interviews router — mock interview sessions.
POST /           → start a mock interview
GET  /           → list past interviews
GET  /{id}       → interview detail
GET  /{id}/summary → interview summary with answers
POST /{id}/answer/{order} → submit answer for evaluation
POST /{id}/follow-up/{order} → submit follow-up answer
POST /{id}/complete → end and summarize interview
"""
import uuid as uuid_module

from fastapi import APIRouter, Request, HTTPException, Query, Depends
from core.rate_limiter import rate_limit
from models.interview_models import (
    StartInterviewRequest,
    StartInterviewResponse,
    InterviewQuestion,
    SubmitInterviewAnswerRequest,
    SubmitInterviewAnswerResponse,
    InterviewSummary,
    InterviewListItem,
    InterviewListResponse,
)
from services.interview_service import InterviewService

router = APIRouter()


def _validate_uuid(value: str, label: str = "ID") -> None:
    try:
        uuid_module.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {label} format")


def _serialize_dt(val) -> str | None:
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


def _get_service(request: Request) -> InterviewService:
    return InterviewService(
        db_pool=request.app.state.db_pool,
        openai_client=request.app.state.openai,
        scheduler=request.app.state.scheduler,
    )


@router.post("/", dependencies=[Depends(rate_limit(5))])
async def start_interview(body: StartInterviewRequest, request: Request):
    """Start a new mock interview session."""
    service = _get_service(request)
    try:
        result = await service.start_interview(
            body.topic, body.difficulty, body.duration_minutes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    first_q = result.get("first_question")
    return StartInterviewResponse(
        interview_id=result["interview_id"],
        topic=result["topic"],
        difficulty=result["difficulty"],
        duration_minutes=result["duration_minutes"],
        total_questions=result["total_questions"],
        first_question=InterviewQuestion(
            question_id=first_q["question_id"] if first_q else None,
            question_text=first_q["question_text"] if first_q else "",
            question_order=first_q["question_order"] if first_q else 1,
        ),
    )


@router.get("/", response_model=InterviewListResponse)
async def list_interviews(
    request: Request,
    topic: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    """List past mock interview sessions."""
    service = _get_service(request)
    data = await service.list_interviews(topic, limit, offset)
    return InterviewListResponse(
        interviews=[
            InterviewListItem(
                id=str(i["id"]),
                topic=i["topic"],
                difficulty=i["difficulty"],
                overall_score=float(i["overall_score"]) if i.get("overall_score") is not None else None,
                total_questions=i.get("total_questions") or 0,
                correct_count=i.get("correct_count") or 0,
                status=i["status"],
                started_at=_serialize_dt(i["started_at"]) or "",
                completed_at=_serialize_dt(i.get("completed_at")),
            )
            for i in data["interviews"]
        ],
        total=data["total"],
    )


@router.get("/{interview_id}")
async def get_interview(interview_id: str, request: Request):
    """Get interview session details."""
    _validate_uuid(interview_id, "interview ID")
    service = _get_service(request)
    try:
        return await service.get_interview_summary(interview_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{interview_id}/summary", response_model=InterviewSummary)
async def get_interview_summary(interview_id: str, request: Request):
    """Get interview summary with scores and answers."""
    _validate_uuid(interview_id, "interview ID")
    service = _get_service(request)
    try:
        data = await service.get_interview_summary(interview_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return InterviewSummary(**data)


@router.post(
    "/{interview_id}/answer/{question_order}",
    dependencies=[Depends(rate_limit(30))],
)
async def submit_answer(
    interview_id: str,
    question_order: int,
    body: SubmitInterviewAnswerRequest,
    request: Request,
):
    """Submit an answer for evaluation during a mock interview."""
    _validate_uuid(interview_id, "interview ID")
    service = _get_service(request)
    try:
        result = await service.evaluate_interview_answer(
            interview_id, question_order, body.user_answer
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    next_q = result.get("next_question")
    return SubmitInterviewAnswerResponse(
        score=result["score"],
        feedback=result["feedback"],
        follow_up_question=result.get("follow_up_question"),
        next_question=InterviewQuestion(**next_q) if next_q else None,
        done=result["done"],
    )


@router.post(
    "/{interview_id}/follow-up/{question_order}",
    dependencies=[Depends(rate_limit(30))],
)
async def submit_follow_up(
    interview_id: str,
    question_order: int,
    body: SubmitInterviewAnswerRequest,
    request: Request,
):
    """Submit a follow-up answer."""
    _validate_uuid(interview_id, "interview ID")
    service = _get_service(request)
    try:
        result = await service.evaluate_follow_up(
            interview_id, question_order, body.user_answer
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    next_q = result.get("next_question")
    return {
        "follow_up_feedback": result["follow_up_feedback"],
        "next_question": next_q,
        "done": result["done"],
    }


@router.post("/{interview_id}/complete")
async def complete_interview(interview_id: str, request: Request):
    """Complete a mock interview and get summary."""
    _validate_uuid(interview_id, "interview ID")
    service = _get_service(request)
    try:
        return await service.complete_interview(interview_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
