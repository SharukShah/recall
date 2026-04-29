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


# --- Question Management ---

class QuestionListItem(BaseModel):
    id: str
    question_text: str
    answer_text: str
    question_type: str
    technique_used: str | None
    mnemonic_hint: str | None
    state: int
    due: str
    stability: float | None
    difficulty: float | None
    last_review: str | None
    created_at: str
    capture_id: str | None
    review_count: int
    last_rating: int | None
    source_text: str | None


class ReviewLogEntry(BaseModel):
    rating: int
    user_answer: str | None
    ai_feedback: str | None
    reviewed_at: str


class QuestionDetail(BaseModel):
    id: str
    question_text: str
    answer_text: str
    question_type: str
    technique_used: str | None
    mnemonic_hint: str | None
    state: int
    due: str
    stability: float | None
    difficulty: float | None
    last_review: str | None
    created_at: str
    capture_id: str | None
    review_count: int
    last_rating: int | None
    source_text: str | None
    accuracy_rate: float | None
    extracted_point_content: str | None
    capture_raw_text: str | None
    review_logs: list[ReviewLogEntry]


class QuestionListResponse(BaseModel):
    questions: list[QuestionListItem]
    total: int


class QuestionUpdateRequest(BaseModel):
    question_text: str | None = Field(default=None, min_length=1, max_length=10000)
    answer_text: str | None = Field(default=None, min_length=1, max_length=10000)
    mnemonic_hint: str | None = Field(default=None, max_length=5000)
    question_type: str | None = None

    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, v):
        if v is not None:
            allowed = {"recall", "cloze", "explain_back", "connection", "explain", "connect", "apply"}
            if v not in allowed:
                raise ValueError(f"question_type must be one of {allowed}")
        return v


class BulkDeleteRequest(BaseModel):
    question_ids: list[str] = Field(..., min_length=1, max_length=50)

    @field_validator("question_ids")
    @classmethod
    def validate_uuids(cls, v):
        for qid in v:
            try:
                uuid_module.UUID(qid)
            except ValueError:
                raise ValueError(f"Invalid UUID: {qid}")
        return v


class RescheduleRequest(BaseModel):
    action: str
    days: int | None = Field(default=None, ge=1, le=365)

    @field_validator("action")
    @classmethod
    def validate_action(cls, v):
        allowed = {"reset", "review_now", "postpone"}
        if v not in allowed:
            raise ValueError(f"action must be one of {allowed}")
        return v


class QuestionTypeCount(BaseModel):
    question_type: str
    count: int


class QuestionStateCount(BaseModel):
    state: int
    count: int


class FailedQuestion(BaseModel):
    id: str
    question_text: str
    accuracy_rate: float


class QuestionStatsSummary(BaseModel):
    total_questions: int
    by_type: list[QuestionTypeCount]
    by_state: list[QuestionStateCount]
    avg_difficulty: float | None
    avg_stability: float | None
    most_failed: list[FailedQuestion]
