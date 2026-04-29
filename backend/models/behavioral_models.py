"""Pydantic models for behavioral interview (STAR stories) endpoints and LLM outputs."""
from pydantic import BaseModel, Field


class BehavioralCaptureRequest(BaseModel):
    narrative: str = Field(..., min_length=50, max_length=5000)
    competency: str


class StarStory(BaseModel):
    id: str
    capture_id: str | None = None
    title: str
    situation: str
    task: str
    action: str
    result: str
    competency: str
    strength_rating: int
    times_practiced: int
    last_practiced_at: str | None = None
    created_at: str


class StarStoryListItem(BaseModel):
    id: str
    title: str
    competency: str
    strength_rating: int
    times_practiced: int
    created_at: str


class StarStoryListResponse(BaseModel):
    stories: list[StarStoryListItem]
    total: int


class StarStoryUpdateRequest(BaseModel):
    title: str | None = None
    situation: str | None = None
    task: str | None = None
    action: str | None = None
    result: str | None = None
    competency: str | None = None
    strength_rating: int | None = Field(default=None, ge=1, le=5)


class BehavioralCaptureResponse(BaseModel):
    story_id: str
    capture_id: str
    title: str
    situation: str
    task: str
    action: str
    result: str
    competency: str
    strength_rating: int


class PracticeQuestionResponse(BaseModel):
    question: str
    competency: str
    tips: str


class BehavioralEvaluation(BaseModel):
    situation_score: int = Field(..., ge=1, le=5)
    task_score: int = Field(..., ge=1, le=5)
    action_score: int = Field(..., ge=1, le=5)
    result_score: int = Field(..., ge=1, le=5)
    overall_score: int = Field(..., ge=1, le=5)
    feedback: str
    suggestions: list[str]


class BehavioralEvaluateRequest(BaseModel):
    competency: str
    question: str
    answer: str = Field(..., min_length=10, max_length=10000)


class CompetencyCoverage(BaseModel):
    competency: str
    story_count: int
    avg_strength: float | None = None
    last_practiced: str | None = None


class BehavioralCoverageResponse(BaseModel):
    competencies: list[CompetencyCoverage]
    total_competencies: int
    covered_competencies: int


# --- LLM Structured Output Schemas ---

class StarExtraction(BaseModel):
    title: str
    situation: str
    task: str
    action: str
    result: str


class BehavioralEvaluationLLM(BaseModel):
    situation_score: int = Field(..., ge=1, le=5)
    task_score: int = Field(..., ge=1, le=5)
    action_score: int = Field(..., ge=1, le=5)
    result_score: int = Field(..., ge=1, le=5)
    overall_score: int = Field(..., ge=1, le=5)
    feedback: str
    suggestions: list[str]
