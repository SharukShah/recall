-- ReCall MVP Database Schema
-- PostgreSQL 16+
-- No pgvector, no embeddings

-- Captures (raw text input)
CREATE TABLE captures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_text TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'text',
    why_it_matters TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI-extracted knowledge points
CREATE TABLE extracted_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capture_id UUID NOT NULL REFERENCES captures(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    content_type TEXT NOT NULL, -- 'fact' | 'concept' | 'list' | 'comparison' | 'procedure'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Review questions with FSRS state
CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extracted_point_id UUID NOT NULL REFERENCES extracted_points(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    question_type TEXT NOT NULL, -- 'recall' | 'cloze' | 'explain' | 'connect' | 'apply'
    technique_used TEXT,
    mnemonic_hint TEXT,

    -- FSRS state (per question = per card)
    due TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stability FLOAT,
    difficulty FLOAT,
    step INT NOT NULL DEFAULT 0,
    state SMALLINT NOT NULL DEFAULT 1,   -- 1=Learning, 2=Review, 3=Relearning
    last_review TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Review history for FSRS optimizer + analytics
CREATE TABLE review_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    rating SMALLINT NOT NULL,            -- 1=Again, 2=Hard, 3=Good, 4=Easy
    state SMALLINT NOT NULL,             -- Card state at review time
    stability FLOAT,
    difficulty FLOAT,
    user_answer TEXT,
    ai_feedback TEXT,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_questions_due ON questions (state, due);
CREATE INDEX idx_review_logs_question ON review_logs (question_id, reviewed_at DESC);
CREATE INDEX idx_captures_created ON captures (created_at DESC);
