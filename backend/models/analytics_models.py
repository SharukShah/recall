"""Pydantic models for Analytics Dashboard endpoints."""
from pydantic import BaseModel


class MasteryDistribution(BaseModel):
    new: int  # state = 0
    learning: int  # state = 1
    review: int  # state = 2 (mastered)
    relearning: int  # state = 3


class LearningVelocity(BaseModel):
    captures_this_week: int
    captures_last_week: int
    reviews_this_week: int
    reviews_last_week: int
    questions_generated_this_week: int


class ReviewConsistency(BaseModel):
    current_streak: int
    longest_streak: int
    review_days_last_30: int  # Days with at least one review in last 30
    avg_reviews_per_day: float  # Over last 30 days


class AnalyticsSummary(BaseModel):
    total_reviews_all_time: int
    avg_score: float | None  # Average rating (1-4) over all reviews
    total_time_studying_estimate_minutes: int  # reviews * ~30s each


class RetentionCurvePoint(BaseModel):
    week_start: str  # ISO date
    retention_rate: float  # % of reviews rated ≥3
    total_reviews: int


class RetentionCurveResponse(BaseModel):
    data_points: list[RetentionCurvePoint]


class WeakArea(BaseModel):
    topic: str
    capture_id: str
    total_reviews: int
    retention_rate: float  # % rated ≥3
    avg_rating: float
    lapsed_count: int  # Times rated "Again"


class WeakAreasResponse(BaseModel):
    weak_areas: list[WeakArea]  # Sorted by retention_rate ascending


class ActivityDay(BaseModel):
    date: str  # ISO date
    captures: int
    reviews: int


class ActivityResponse(BaseModel):
    days: list[ActivityDay]  # Last 90 days


class AnalyticsResponse(BaseModel):
    mastery_distribution: MasteryDistribution
    learning_velocity: LearningVelocity
    review_consistency: ReviewConsistency
    summary: AnalyticsSummary
