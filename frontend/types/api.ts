// TypeScript interfaces matching backend API models

export interface DashboardStats {
  due_today: number;
  streak_days: number;
  total_captures: number;
  total_questions: number;
  retention_rate: number;
  reviews_today: number;
}

export interface CaptureListItem {
  id: string;
  raw_text: string;
  source_type: string;
  facts_count: number;
  created_at: string;
}

export interface Fact {
  id: string;
  content: string;
  content_type: string;
  created_at: string;
}

export interface Question {
  id: string;
  question_text: string;
  answer_text: string;
  question_type: string;
  technique_used?: string;
  mnemonic_hint?: string;
  state: number;
  due: string;
}

export interface CaptureDetail {
  id: string;
  raw_text: string;
  source_type: string;
  why_it_matters?: string;
  created_at: string;
  facts: Fact[];
  questions: Question[];
}

export interface CaptureRequest {
  raw_text: string;
  source_type: "text" | "voice" | "url";
  why_it_matters?: string;
}

export interface CaptureResponse {
  capture_id: string;
  facts_count: number;
  questions_count: number;
  status: "complete" | "no_facts" | "extraction_failed";
  processing_time_ms: number;
  message?: string;
}

export interface ReviewQuestion {
  question_id: string;
  question_text: string;
  question_type: string;
  mnemonic_hint?: string;
  technique_used?: string;
}

export interface DueQuestionsResponse {
  questions: ReviewQuestion[];
  total_due: number;
}

export interface EvaluateRequest {
  question_id: string;
  user_answer: string;
}

export interface EvaluateResponse {
  correct_answer: string;
  score: "correct" | "partial" | "incorrect";
  feedback: string;
  suggested_rating: number;
}

export interface RateRequest {
  question_id: string;
  rating: number;
  user_answer?: string;
  ai_feedback?: string;
}

export interface RateResponse {
  next_due: string;
  interval_days: number;
  state: number;
  state_label: string;
}
