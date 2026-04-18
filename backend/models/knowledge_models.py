"""Pydantic models for knowledge search endpoints."""
from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.3, ge=0.0, le=1.0)

    @field_validator("query")
    @classmethod
    def query_not_whitespace(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Query must not be empty or whitespace-only")
        return stripped


class SearchSource(BaseModel):
    index: int
    capture_id: str
    content: str
    content_type: str
    similarity: float
    captured_at: str


class SearchResponse(BaseModel):
    answer: str
    sources: list[SearchSource]
    has_answer: bool
    result_count: int
