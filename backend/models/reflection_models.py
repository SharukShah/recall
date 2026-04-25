"""Pydantic models for Evening Reflection endpoints."""
from pydantic import BaseModel, Field


class ReflectionRequest(BaseModel):
    content: str = Field(..., min_length=5, max_length=10000)


class ReflectionResponse(BaseModel):
    reflection_id: str
    capture_id: str | None
    facts_count: int
    questions_count: int
    streak_days: int
    message: str | None = None


class ReflectionStatusResponse(BaseModel):
    completed_today: bool
    streak_days: int
    last_reflection_at: str | None


class ReflectionListItem(BaseModel):
    id: str
    content: str
    capture_id: str | None
    created_at: str
