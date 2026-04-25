export interface MasteryDistribution {
  new: number;
  learning: number;
  review: number;
  relearning: number;
}

export interface LearningVelocity {
  captures_this_week: number;
  captures_last_week: number;
  reviews_this_week: number;
  reviews_last_week: number;
  questions_generated_this_week: number;
}

export interface ReviewConsistency {
  current_streak: number;
  longest_streak: number;
  review_days_last_30: number;
  avg_reviews_per_day: number;
}

export interface AnalyticsSummary {
  total_reviews_all_time: number;
  avg_score: number | null;
  total_time_studying_estimate_minutes: number;
}

export interface RetentionCurvePoint {
  week_start: string;
  retention_rate: number;
  total_reviews: number;
}

export interface RetentionCurveResponse {
  data_points: RetentionCurvePoint[];
}

export interface WeakArea {
  topic: string;
  capture_id: string;
  total_reviews: number;
  retention_rate: number;
  avg_rating: number;
  lapsed_count: number;
}

export interface WeakAreasResponse {
  weak_areas: WeakArea[];
}

export interface ActivityDay {
  date: string;
  captures: number;
  reviews: number;
}

export interface ActivityResponse {
  days: ActivityDay[];
}

export interface AnalyticsResponse {
  mastery_distribution: MasteryDistribution;
  learning_velocity: LearningVelocity;
  review_consistency: ReviewConsistency;
  summary: AnalyticsSummary;
}
