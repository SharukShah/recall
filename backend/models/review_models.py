"""Pydantic models for review endpoints and LLM evaluation."""
import uuid as uuid_module
from pydantic import BaseModel, Field, field_validator
from models.common import ScoreType


# --- API Request/Response ---

class ReviewQuestion(BaseModel):
    question_id: str
    question_text: str
    question_type: str
    mnemonic_hint: str | None
    technique_used: str | None


class DueResponse(BaseModel):
    questions: list[ReviewQuestion]
    total_due: int


class EvaluateRequest(BaseModel):
    question_id: str
    user_answer: str = Field(..., min_length=1, max_length=10000)

    @field_validator("question_id")
    @classmethod
    def validate_uuid(cls, v):
        try:
            uuid_module.UUID(v)
        except ValueError:
            raise ValueError("Invalid question ID format")
        return v


class EvaluateResponse(BaseModel):
    correct_answer: str
    score: ScoreType
    feedback: str
    suggested_rating: int = Field(..., ge=1, le=4)


class RateRequest(BaseModel):
    question_id: str
    rating: int = Field(..., ge=1, le=4)
    user_answer: str | None = Field(default=None, max_length=10000)
    ai_feedback: str | None = Field(default=None, max_length=5000)

    @field_validator("question_id")
    @classmethod
    def validate_uuid(cls, v):
        try:
            uuid_module.UUID(v)
        except ValueError:
            raise ValueError("Invalid question ID format")
        return v


class RateResponse(BaseModel):
    next_due: str  # ISO datetime
    interval_days: float
    state: int  # 0=New, 1=Learning, 2=Review, 3=Relearning
    state_label: str


# --- LLM Structured Output ---

class AnswerEvaluation(BaseModel):
    score: ScoreType
    feedback: str
    suggested_rating: int = Field(..., ge=1, le=4)
