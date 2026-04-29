"""Pydantic models for mock interview endpoints and LLM structured outputs."""
from pydantic import BaseModel, Field


class StartInterviewRequest(BaseModel):
    topic: str
    difficulty: str = "medium"
    duration_minutes: int = 30


class InterviewQuestion(BaseModel):
    question_id: str | None = None
    question_text: str
    question_order: int


class StartInterviewResponse(BaseModel):
    interview_id: str
    topic: str
    difficulty: str
    duration_minutes: int
    total_questions: int
    first_question: InterviewQuestion


class SubmitInterviewAnswerRequest(BaseModel):
    user_answer: str = Field(..., min_length=1, max_length=10000)


class SubmitInterviewAnswerResponse(BaseModel):
    score: int = Field(..., ge=1, le=5)
    feedback: str
    follow_up_question: str | None = None
    next_question: InterviewQuestion | None = None
    done: bool


class InterviewSummary(BaseModel):
    interview_id: str
    topic: str
    difficulty: str
    overall_score: float
    total_questions: int
    correct_count: int
    partial_count: int
    wrong_count: int
    strengths: list[str]
    weaknesses: list[str]
    improvement_tips: list[str]
    answers: list[dict]
    duration_seconds: int | None = None


class InterviewListItem(BaseModel):
    id: str
    topic: str
    difficulty: str
    overall_score: float | None = None
    total_questions: int
    correct_count: int
    status: str
    started_at: str
    completed_at: str | None = None


class InterviewListResponse(BaseModel):
    interviews: list[InterviewListItem]
    total: int


# --- LLM Structured Output Schemas ---

class GeneratedInterviewQuestion(BaseModel):
    question_text: str
    expected_answer: str
    follow_up: str


class GeneratedInterviewQuestions(BaseModel):
    questions: list[GeneratedInterviewQuestion]


class InterviewAnswerEvaluation(BaseModel):
    score: int = Field(..., ge=1, le=5)
    feedback: str
    needs_follow_up: bool
    follow_up_question: str


class InterviewSummaryLLM(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    improvement_tips: list[str]
