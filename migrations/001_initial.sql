-- =============================================
-- ITERA BOT — Migration 001
-- Only creates the NEW table (processed_updates).
-- Existing tables (Profiles, Goals, journal_entries) are NOT touched.
-- =============================================

-- Idempotency table for deduplicating Telegram updates
CREATE TABLE IF NOT EXISTS processed_updates (
    update_id       bigint      PRIMARY KEY,
    processed_at    timestamptz DEFAULT now()
);

-- Optional: index for cleanup job
CREATE INDEX IF NOT EXISTS "processed_updates_time_idx" ON processed_updates (processed_at);
