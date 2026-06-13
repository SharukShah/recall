"""Pydantic models for Memory Gym endpoints."""
from typing import Any
from pydantic import BaseModel, Field

# Allowed exercise keys (must match the frontend exercise keys).
GYM_EXERCISES = {"dual_n_back", "span", "math_ladder", "pattern", "name_face"}


class GymSessionRequest(BaseModel):
    exercise: str = Field(..., min_length=1, max_length=32)
    score: int = Field(..., ge=0, le=100000)
    max_score: int | None = Field(default=None, ge=0, le=100000)
    level: int | None = Field(default=None, ge=0, le=1000)
    duration_seconds: int | None = Field(default=None, ge=0, le=86400)
    detail: dict[str, Any] | None = None


class GymSessionResponse(BaseModel):
    session_id: str
    created_at: str
    is_best: bool


class GymSessionListItem(BaseModel):
    id: str
    exercise: str
    score: int
    max_score: int | None
    level: int | None
    duration_seconds: int | None
    detail: dict[str, Any] | None
    created_at: str


class GymExerciseStat(BaseModel):
    exercise: str
    best_score: int
    best_level: int | None
    sessions: int
    last_played_at: str | None


class GymStatsResponse(BaseModel):
    total_sessions: int
    exercises: list[GymExerciseStat]
