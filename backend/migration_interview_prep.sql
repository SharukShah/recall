-- Interview Prep Features Migration
-- Run after Phase 5 migration
-- Creates tables and columns for: Topic Categorization, Mock Interviews,
-- Streak Milestones, and STAR Behavioral Stories.

-- ============================================================
-- Feature 2: Topic Auto-categorization
-- ============================================================

-- Add category column to questions
ALTER TABLE questions ADD COLUMN IF NOT EXISTS category TEXT;

-- Index for filtering by category
CREATE INDEX IF NOT EXISTS idx_questions_category ON questions (category);

-- Allowed values (enforced at application layer):
-- python_basics, oop, dsa, system_design, databases, web_dev,
-- networking, os_concepts, testing, devops, behavioral, general

-- ============================================================
-- Feature 1: Mock Interview Tables
-- ============================================================

-- Mock interview sessions
CREATE TABLE IF NOT EXISTS mock_interviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    duration_minutes INT NOT NULL DEFAULT 30,
    status TEXT NOT NULL DEFAULT 'in_progress',
    overall_score FLOAT,
    strengths JSONB,
    weaknesses JSONB,
    improvement_tips JSONB,
    total_questions INT DEFAULT 0,
    correct_count INT DEFAULT 0,
    partial_count INT DEFAULT 0,
    wrong_count INT DEFAULT 0,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Individual Q&A within an interview
CREATE TABLE IF NOT EXISTS interview_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interview_id UUID NOT NULL REFERENCES mock_interviews(id) ON DELETE CASCADE,
    question_id UUID REFERENCES questions(id) ON DELETE SET NULL,
    question_text TEXT NOT NULL,
    expected_answer TEXT NOT NULL,
    user_answer TEXT,
    score INT,
    feedback TEXT,
    follow_up_asked BOOLEAN DEFAULT false,
    follow_up_answer TEXT,
    follow_up_feedback TEXT,
    question_order INT NOT NULL,
    answered_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_mock_interviews_topic ON mock_interviews (topic, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_mock_interviews_status ON mock_interviews (status);
CREATE INDEX IF NOT EXISTS idx_interview_answers_interview ON interview_answers (interview_id, question_order);

-- ============================================================
-- Feature 4: Streak Milestones
-- ============================================================

CREATE TABLE IF NOT EXISTS streak_milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    milestone INT NOT NULL UNIQUE,
    achieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Extend notification_settings
ALTER TABLE notification_settings
    ADD COLUMN IF NOT EXISTS streak_reminder_enabled BOOLEAN DEFAULT true;

-- ============================================================
-- Feature 5: STAR Behavioral Stories
-- ============================================================

CREATE TABLE IF NOT EXISTS star_stories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capture_id UUID REFERENCES captures(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    situation TEXT NOT NULL,
    task TEXT NOT NULL,
    action TEXT NOT NULL,
    result TEXT NOT NULL,
    competency TEXT NOT NULL,
    strength_rating INT NOT NULL DEFAULT 3 CHECK (strength_rating BETWEEN 1 AND 5),
    times_practiced INT NOT NULL DEFAULT 0,
    last_practiced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_star_stories_competency ON star_stories (competency);
CREATE INDEX IF NOT EXISTS idx_star_stories_created ON star_stories (created_at DESC);
