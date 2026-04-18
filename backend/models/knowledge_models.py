"""Pydantic models for knowledge/search endpoints (Phase 2 — stubs)."""
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)


class KnowledgeItem(BaseModel):
    content: str
    content_type: str
    capture_date: str
    source_type: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[KnowledgeItem]
