-- ============================================================
-- Memory Gym Migration: per-exercise training sessions
-- Run against an existing DB: psql "$DATABASE_URL" -f migration_gym.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS gym_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exercise TEXT NOT NULL,          -- 'dual_n_back' | 'span' | 'math_ladder' | 'pattern' | 'name_face'
    score INT NOT NULL,              -- primary metric (accuracy %, digits, solved, correct)
    max_score INT,                   -- denominator when applicable (e.g. /10), nullable
    level INT,                       -- n-back N, digit span, etc., nullable
    duration_seconds INT,            -- nullable
    detail JSONB,                    -- per-exercise extra metrics
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gym_sessions_exercise ON gym_sessions (exercise, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_gym_sessions_created ON gym_sessions (created_at DESC);
