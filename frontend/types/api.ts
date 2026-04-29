// TypeScript interfaces matching backend API models

export interface DashboardStats {
  due_today: number;
  streak_days: number;
  total_captures: number;
  total_questions: number;
  retention_rate: number;
  reviews_today: number;
  reflection_completed_today: boolean;
  reflection_streak: number;
  active_teach_session: string | null;
}

export interface CaptureListItem {
  id: string;
  raw_text: string;
  source_type: string;
  facts_count: number;
  tags: string[];
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
  tags: string[];
  created_at: string;
  facts: Fact[];
  questions: Question[];
}

export interface CaptureRequest {
  raw_text: string;
  source_type: "text" | "voice" | "url";
  why_it_matters?: string;
  tags?: string[];
}

export interface TagItem {
  id: string;
  name: string;
  count: number;
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
  score: "correct" | "partial" | "wrong";
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

// Knowledge Search
export interface SearchRequest {
  query: string;
  limit?: number;
  min_similarity?: number;
}

export interface SearchSource {
  index: number;
  capture_id: string;
  content: string;
  content_type: string;
  similarity: number;
  captured_at: string;
}

export interface SearchResponse {
  answer: string;
  has_answer: boolean;
  result_count: number;
  sources: SearchSource[];
}

// Phase 3: Teach Me Mode
export interface TeachStartRequest {
  topic: string;
}

export interface TeachStartResponse {
  session_id: string;
  topic: string;
  total_chunks: number;
  current_chunk: number;
  chunk_title: string;
  chunk_content: string;
  chunk_analogy: string | null;
  recall_question: string;
}

export interface TeachRespondRequest {
  session_id: string;
  answer: string;
}

export interface TeachRespondResponse {
  feedback: string;
  score: "correct" | "partial" | "wrong";
  is_complete: boolean;
  current_chunk?: number;
  chunk_title?: string;
  chunk_content?: string;
  chunk_analogy?: string | null;
  recall_question?: string;
  summary?: string;
  capture_id?: string;
}

export interface TeachSessionResponse {
  session_id: string;
  topic: string;
  total_chunks: number;
  current_chunk: number;
  chunk_title: string;
  chunk_content: string;
  chunk_analogy: string | null;
  recall_question: string;
  is_complete: boolean;
}

// Phase 3: Evening Reflection
export interface ReflectionRequest {
  content: string;
}

export interface ReflectionResponse {
  reflection_id: string;
  capture_id: string | null;
  facts_count: number;
  questions_count: number;
  streak_days: number;
  message: string | null;
}

export interface ReflectionStatusResponse {
  completed_today: boolean;
  streak_days: number;
  last_reflection_at: string | null;
}

export interface ReflectionListItem {
  id: string;
  content: string;
  capture_id: string | null;
  created_at: string;
}

// Phase 3: URL Ingestion
export interface URLCaptureRequest {
  url: string;
  why_it_matters?: string;
}

// Question Bank
export interface QuestionListItem {
  id: string;
  question_text: string;
  answer_text: string;
  question_type: string;
  technique_used?: string;
  mnemonic_hint?: string;
  state: number;
  due: string;
  stability?: number;
  difficulty?: number;
  last_review?: string;
  created_at: string;
  capture_id?: string;
  review_count: number;
  last_rating?: number;
  source_text?: string;
}

export interface QuestionDetail extends QuestionListItem {
  accuracy_rate?: number;
  extracted_point_content?: string;
  capture_raw_text?: string;
  review_logs: ReviewLogEntry[];
}

export interface ReviewLogEntry {
  rating: number;
  user_answer?: string;
  ai_feedback?: string;
  reviewed_at: string;
}

export interface QuestionListResponse {
  questions: QuestionListItem[];
  total: number;
}

export interface QuestionStatsSummary {
  total_questions: number;
  by_type: { question_type: string; count: number }[];
  by_state: { state: number; count: number }[];
  avg_difficulty?: number;
  avg_stability?: number;
  most_failed: { id: string; question_text: string; accuracy_rate: number }[];
}
