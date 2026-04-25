"""Pydantic models for Method of Loci endpoints."""
from pydantic import BaseModel, Field
from typing import Annotated


class LociCreateRequest(BaseModel):
    items: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(..., min_length=3, max_length=20)
    title: str = Field(..., min_length=1, max_length=200)
    palace_theme: str | None = Field(default=None, max_length=100)


class LociLocation(BaseModel):
    position: int
    location_name: str
    item: str
    vivid_image: str
    narration: str


class LociWalkthrough(BaseModel):
    palace_theme: str
    introduction: str
    locations: list[LociLocation]
    conclusion: str


class LociCreateResponse(BaseModel):
    session_id: str
    title: str
    palace_theme: str
    total_locations: int
    walkthrough: LociWalkthrough
    full_narration: str
    capture_id: str | None


class LociRecallRequest(BaseModel):
    recalled_items: list[str]


class LociRecallDetail(BaseModel):
    position: int
    expected: str
    recalled: str | None
    correct: bool
    location_hint: str


class LociRecallResponse(BaseModel):
    score: int
    total: int
    feedback: str
    correct_order: list[str]
    details: list[LociRecallDetail]


class LociListItem(BaseModel):
    session_id: str
    title: str
    palace_theme: str
    total_locations: int
    last_recall_score: int | None
    created_at: str
