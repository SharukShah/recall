"""
Reviews router — due questions, answer evaluation, FSRS rating.
GET  /due      → get questions due for review
POST /evaluate → evaluate user's answer with LLM
POST /rate     → apply FSRS rating (user's final choice)
"""
from fastapi import APIRouter, Request, HTTPException, Query, Depends
from core.rate_limiter import rate_limit
from models.review_models import (
    DueResponse, EvaluateRequest, EvaluateResponse,
    RateRequest, RateResponse,
)
from services.review_service import ReviewService

router = APIRouter()


@router.get("/due", response_model=DueResponse)
async def get_due_questions(
    request: Request,
    limit: int = Query(default=20, ge=1, le=50),
):
    """Get questions due for review, ordered by priority."""
    service = ReviewService(
        db_pool=request.app.state.db_pool,
        openai_client=request.app.state.openai,
        scheduler=request.app.state.scheduler,
    )
    return await service.get_due(limit)


@router.post("/evaluate", response_model=EvaluateResponse, dependencies=[Depends(rate_limit(30))])
async def evaluate_answer(body: EvaluateRequest, request: Request):
    """Evaluate user's answer against expected answer using LLM."""
    service = ReviewService(
        db_pool=request.app.state.db_pool,
        openai_client=request.app.state.openai,
        scheduler=request.app.state.scheduler,
    )
    try:
        return await service.evaluate_answer(body)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/rate", response_model=RateResponse)
async def rate_question(body: RateRequest, request: Request):
    """Apply FSRS rating to a question (1=Again, 2=Hard, 3=Good, 4=Easy)."""
    service = ReviewService(
        db_pool=request.app.state.db_pool,
        openai_client=request.app.state.openai,
        scheduler=request.app.state.scheduler,
    )
    try:
        return await service.rate(body)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
