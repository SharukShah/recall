"""Pydantic models for Teach Me Mode endpoints and LLM structured outputs."""
import uuid
from pydantic import BaseModel, Field
from typing import Literal


# --- LLM Structured Output ---

class TeachChunk(BaseModel):
    chunk_index: int
    title: str
    content: str
    analogy: str | None = None
    recall_question: str


class TeachPlan(BaseModel):
    topic: str
    total_chunks: int
    chunks: list[TeachChunk]


# --- API Request/Response ---

class TeachStartRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=500)


class TeachStartResponse(BaseModel):
    session_id: str
    topic: str
    total_chunks: int
    current_chunk: int
    chunk_title: str
    chunk_content: str
    chunk_analogy: str | None
    recall_question: str


class TeachRespondRequest(BaseModel):
    session_id: uuid.UUID
    answer: str = Field(..., min_length=1, max_length=5000)


class TeachRespondResponse(BaseModel):
    feedback: str
    score: Literal["correct", "partial", "wrong"]
    is_complete: bool
    current_chunk: int | None = None
    chunk_title: str | None = None
    chunk_content: str | None = None
    chunk_analogy: str | None = None
    recall_question: str | None = None
    summary: str | None = None
    capture_id: str | None = None


class TeachSessionResponse(BaseModel):
    session_id: str
    topic: str
    total_chunks: int
    current_chunk: int
    chunk_title: str
    chunk_content: str
    chunk_analogy: str | None
    recall_question: str
    is_complete: bool


# --- LLM Evaluation Output ---

class TeachAnswerEvaluation(BaseModel):
    score: Literal["correct", "partial", "wrong"]
    feedback: str
