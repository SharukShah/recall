-- ============================================================
-- Phase 5 Migration: Polish & Advanced Features
-- Run after Phase 4 schema is in place
-- ============================================================

-- 1. Push Notifications: subscription storage
CREATE TABLE IF NOT EXISTS notification_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint TEXT NOT NULL UNIQUE,
    p256dh_key TEXT NOT NULL,
    auth_key TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Push Notifications: settings (single-user)
CREATE TABLE IF NOT EXISTS notification_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enabled BOOLEAN NOT NULL DEFAULT true,
    review_reminder_time TEXT NOT NULL DEFAULT '09:00',
    timezone TEXT NOT NULL DEFAULT 'UTC',
    last_sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Method of Loci: walkthrough sessions
CREATE TABLE IF NOT EXISTS loci_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    items JSONB NOT NULL,
    palace_theme TEXT NOT NULL,
    walkthrough_json JSONB NOT NULL,
    full_narration TEXT NOT NULL,
    capture_id UUID REFERENCES captures(id),
    last_recall_score INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_loci_sessions_created ON loci_sessions (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_review_logs_date ON review_logs (reviewed_at::date);
CREATE INDEX IF NOT EXISTS idx_questions_state ON questions (state);
CREATE INDEX IF NOT EXISTS idx_extracted_points_embedding_not_null
    ON extracted_points (id) WHERE embedding IS NOT NULL;
