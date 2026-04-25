"""
Stats service — analytics queries.
"""
from asyncpg import Pool
from datetime import datetime, timedelta, timezone
from models.analytics_models import (
    AnalyticsResponse,
    MasteryDistribution,
    LearningVelocity,
    ReviewConsistency,
    AnalyticsSummary,
    RetentionCurveResponse,
    RetentionCurvePoint,
    WeakAreasResponse,
    WeakArea,
    ActivityResponse,
    ActivityDay,
)


class StatsService:
    """Service for generating analytics data."""

    def __init__(self, db_pool: Pool):
        self.db_pool = db_pool

    async def get_analytics(self) -> AnalyticsResponse:
        """Get comprehensive analytics data."""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # Mastery distribution
                mastery_query = """
                    SELECT 
                        COALESCE(SUM(CASE WHEN state = 0 THEN 1 ELSE 0 END), 0) as new,
                        COALESCE(SUM(CASE WHEN state = 1 THEN 1 ELSE 0 END), 0) as learning,
                        COALESCE(SUM(CASE WHEN state = 2 THEN 1 ELSE 0 END), 0) as review,
                        COALESCE(SUM(CASE WHEN state = 3 THEN 1 ELSE 0 END), 0) as relearning
                    FROM questions
                """
                mastery_row = await conn.fetchrow(mastery_query)
                mastery = MasteryDistribution(
                    new=mastery_row["new"],
                    learning=mastery_row["learning"],
                    review=mastery_row["review"],
                    relearning=mastery_row["relearning"],
                    )

            # Learning velocity
            now = datetime.now(timezone.utc)
            week_ago = now - timedelta(days=7)
            two_weeks_ago = now - timedelta(days=14)

            velocity_query = """
                SELECT
                    (SELECT COUNT(*) FROM captures WHERE created_at >= $1) as captures_this_week,
                    (SELECT COUNT(*) FROM captures WHERE created_at >= $2 AND created_at < $1) as captures_last_week,
                    (SELECT COUNT(*) FROM review_logs WHERE reviewed_at >= $1) as reviews_this_week,
                    (SELECT COUNT(*) FROM review_logs WHERE reviewed_at >= $2 AND reviewed_at < $1) as reviews_last_week,
                    (SELECT COUNT(*) FROM questions WHERE created_at >= $1) as questions_this_week
            """
            velocity_row = await conn.fetchrow(velocity_query, week_ago, two_weeks_ago)
            velocity = LearningVelocity(
                captures_this_week=velocity_row["captures_this_week"],
                captures_last_week=velocity_row["captures_last_week"],
                reviews_this_week=velocity_row["reviews_this_week"],
                reviews_last_week=velocity_row["reviews_last_week"],
                questions_generated_this_week=velocity_row["questions_this_week"],
            )

            # Review consistency
            thirty_days_ago = now - timedelta(days=30)
            
            # Current streak (reuse existing logic)
            streak_query = """
                WITH review_dates AS (
                    SELECT DISTINCT reviewed_at::date as review_date
                    FROM review_logs
                    ORDER BY review_date DESC
                ),
                date_diffs AS (
                    SELECT 
                        review_date,
                        LAG(review_date) OVER (ORDER BY review_date DESC) as prev_date
                    FROM review_dates
                )
                SELECT 
                    COUNT(*) as streak
                FROM date_diffs
                WHERE prev_date IS NULL 
                    OR review_date = prev_date - INTERVAL '1 day'
            """
            current_streak = await conn.fetchval(streak_query) or 0

            # Longest streak
            longest_streak_query = """
                WITH review_dates AS (
                    SELECT DISTINCT reviewed_at::date as review_date
                    FROM review_logs
                    ORDER BY review_date
                ),
                streak_groups AS (
                    SELECT 
                        review_date,
                        review_date - (ROW_NUMBER() OVER (ORDER BY review_date))::int * INTERVAL '1 day' as grp
                    FROM review_dates
                ),
                streak_lengths AS (
                    SELECT COUNT(*) as streak_length
                    FROM streak_groups
                    GROUP BY grp
                )
                SELECT COALESCE(MAX(streak_length), 0) as longest
                FROM streak_lengths
            """
            longest_streak = await conn.fetchval(longest_streak_query) or 0

            # Review days last 30
            review_days_query = """
                SELECT COUNT(DISTINCT reviewed_at::date)
                FROM review_logs
                WHERE reviewed_at >= $1
            """
            review_days_last_30 = await conn.fetchval(review_days_query, thirty_days_ago) or 0

            # Avg reviews per day
            total_reviews_last_30 = await conn.fetchval(
                "SELECT COUNT(*) FROM review_logs WHERE reviewed_at >= $1", thirty_days_ago
            ) or 0
            avg_reviews_per_day = total_reviews_last_30 / 30.0

            consistency = ReviewConsistency(
                current_streak=current_streak,
                longest_streak=longest_streak,
                review_days_last_30=review_days_last_30,
                avg_reviews_per_day=avg_reviews_per_day,
            )

            # Summary
            summary_query = """
                SELECT
                    COUNT(*) as total_reviews,
                    AVG(rating) as avg_score
                FROM review_logs
            """
            summary_row = await conn.fetchrow(summary_query)
            total_reviews = summary_row["total_reviews"] or 0
            avg_score = float(summary_row["avg_score"]) if summary_row["avg_score"] else None
            estimate_minutes = int(total_reviews * 0.5)  # ~30 seconds per review

            summary = AnalyticsSummary(
                total_reviews_all_time=total_reviews,
                avg_score=avg_score,
                total_time_studying_estimate_minutes=estimate_minutes,
            )

            return AnalyticsResponse(
                mastery_distribution=mastery,
                learning_velocity=velocity,
                review_consistency=consistency,
                summary=summary,
            )

    async def get_retention_curve(self, weeks: int = 12) -> RetentionCurveResponse:
        """Get retention rate over time (weekly buckets)."""
        async with self.db_pool.acquire() as conn:
            query = """
                WITH weekly_reviews AS (
                    SELECT 
                        DATE_TRUNC('week', reviewed_at) as week_start,
                        COUNT(*) as total_reviews,
                        SUM(CASE WHEN rating >= 3 THEN 1 ELSE 0 END) as good_reviews
                    FROM review_logs
                    WHERE reviewed_at >= NOW() - ($1 * INTERVAL '1 week')
                    GROUP BY week_start
                    ORDER BY week_start
                )
                SELECT 
                    week_start,
                    total_reviews,
                    CASE 
                        WHEN total_reviews > 0 
                        THEN (good_reviews::float / total_reviews::float) 
                        ELSE 0 
                    END as retention_rate
                FROM weekly_reviews
            """
            rows = await conn.fetch(query, weeks)
            
            data_points = [
                RetentionCurvePoint(
                    week_start=row["week_start"].isoformat(),
                    retention_rate=float(row["retention_rate"]),
                    total_reviews=row["total_reviews"],
                )
                for row in rows
            ]
            
            return RetentionCurveResponse(data_points=data_points)

    async def get_weak_areas(self, limit: int = 10) -> WeakAreasResponse:
        """Get topics with lowest retention rates."""
        async with self.db_pool.acquire() as conn:
            query = """
                WITH topic_stats AS (
                    SELECT 
                        c.id::text as capture_id,
                        LEFT(c.raw_text, 50) as topic,
                        COUNT(rl.id) as total_reviews,
                        SUM(CASE WHEN rl.rating >= 3 THEN 1 ELSE 0 END) as good_reviews,
                        SUM(CASE WHEN rl.rating = 1 THEN 1 ELSE 0 END) as lapsed_count,
                        AVG(rl.rating) as avg_rating
                    FROM captures c
                    JOIN extracted_points ep ON c.id = ep.capture_id
                    JOIN questions q ON ep.id = q.extracted_point_id
                    JOIN review_logs rl ON q.id = rl.question_id
                    WHERE rl.reviewed_at >= NOW() - INTERVAL '30 days'
                    GROUP BY c.id, c.raw_text
                    HAVING COUNT(rl.id) >= 3
                )
                SELECT 
                    capture_id,
                    topic,
                    total_reviews,
                    CASE 
                        WHEN total_reviews > 0 
                        THEN (good_reviews::float / total_reviews::float) 
                        ELSE 0 
                    END as retention_rate,
                    avg_rating,
                    lapsed_count
                FROM topic_stats
                ORDER BY retention_rate ASC, total_reviews DESC
                LIMIT $1
            """
            rows = await conn.fetch(query, limit)
            
            weak_areas = [
                WeakArea(
                    topic=row["topic"],
                    capture_id=row["capture_id"],
                    total_reviews=row["total_reviews"],
                    retention_rate=float(row["retention_rate"]),
                    avg_rating=float(row["avg_rating"]),
                    lapsed_count=row["lapsed_count"],
                )
                for row in rows
            ]
            
            return WeakAreasResponse(weak_areas=weak_areas)

    async def get_activity(self, days: int = 90) -> ActivityResponse:
        """Get daily activity (captures + reviews) for last N days."""
        async with self.db_pool.acquire() as conn:
            query = """
                WITH date_series AS (
                    SELECT generate_series(
                        CURRENT_DATE - $1::int,
                        CURRENT_DATE,
                        '1 day'::interval
                    )::date as date
                )
                SELECT 
                    ds.date,
                    COALESCE(c.capture_count, 0) as captures,
                    COALESCE(r.review_count, 0) as reviews
                FROM date_series ds
                LEFT JOIN (
                    SELECT created_at::date as date, COUNT(*) as capture_count
                    FROM captures
                    GROUP BY created_at::date
                ) c ON ds.date = c.date
                LEFT JOIN (
                    SELECT reviewed_at::date as date, COUNT(*) as review_count
                    FROM review_logs
                    GROUP BY reviewed_at::date
                ) r ON ds.date = r.date
                ORDER BY ds.date
            """
            rows = await conn.fetch(query, days)
            
            activity_days = [
                ActivityDay(
                    date=row["date"].isoformat(),
                    captures=row["captures"],
                    reviews=row["reviews"],
                )
                for row in rows
            ]
            
            return ActivityResponse(days=activity_days)
