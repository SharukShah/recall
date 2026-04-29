"""Pydantic models for capture endpoints and LLM structured outputs."""
import re
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from models.common import ContentType, QuestionType, TechniqueType

_TAG_PATTERN = re.compile(r'^[a-zA-Z0-9\-_ ]+$')


# --- API Request/Response ---

class CaptureRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=50000)
    source_type: Literal["text", "voice", "url", "reflection"] = "text"
    why_it_matters: str | None = Field(default=None, max_length=1000)
    tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v):
        validated = []
        for tag in v:
            tag = tag.strip()
            if not tag:
                continue
            if len(tag) > 50:
                raise ValueError(f"Tag '{tag[:20]}...' exceeds 50 characters")
            if not _TAG_PATTERN.match(tag):
                raise ValueError(f"Tag '{tag}' contains invalid characters. Only alphanumeric, hyphens, underscores, and spaces are allowed.")
            validated.append(tag)
        return validated


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
    tags: list[str] = []
    created_at: str


class CaptureDetail(BaseModel):
    id: str
    raw_text: str
    source_type: str
    why_it_matters: str | None
    tags: list[str] = []
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
