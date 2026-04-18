"""Pydantic models for capture endpoints and LLM structured outputs."""
from pydantic import BaseModel, Field
from typing import Literal
from models.common import ContentType, QuestionType, TechniqueType


# --- API Request/Response ---

class CaptureRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=50000)
    source_type: Literal["text", "voice", "url"] = "text"
    why_it_matters: str | None = Field(default=None, max_length=1000)


class CaptureResponse(BaseModel):
    capture_id: str
    facts_count: int
    questions_count: int
    status: str  # "complete" | "no_facts" | "extraction_failed"
    processing_time_ms: int
    message: str | None = None


class CaptureListItem(BaseModel):
    id: str
    raw_text: str
    source_type: str
    facts_count: int
    created_at: str


class CaptureDetail(BaseModel):
    id: str
    raw_text: str
    source_type: str
    why_it_matters: str | None
    created_at: str
    facts: list["FactItem"]
    questions: list["QuestionItem"]


class FactItem(BaseModel):
    id: str
    content: str
    content_type: str
    created_at: str


class QuestionItem(BaseModel):
    id: str
    question_text: str
    answer_text: str
    question_type: str
    technique_used: str | None
    mnemonic_hint: str | None
    state: int
    due: str


# --- LLM Structured Output Schemas ---

class Fact(BaseModel):
    content: str
    content_type: ContentType


class ExtractedFacts(BaseModel):
    topic: str
    facts: list[Fact]


class GeneratedQuestion(BaseModel):
    question_text: str
    answer_text: str
    question_type: QuestionType
    fact_index: int = 0


class GeneratedQuestions(BaseModel):
    questions: list[GeneratedQuestion]


class TechniqueSelection(BaseModel):
    technique: TechniqueType
    instructions: str
