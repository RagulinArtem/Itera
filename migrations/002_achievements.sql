-- =============================================
-- Achievements table
-- =============================================
CREATE TABLE IF NOT EXISTS achievements (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid        NOT NULL REFERENCES "Profiles"(id) ON DELETE CASCADE,
    code            text        NOT NULL,           -- unique achievement code e.g. 'first_checkin'
    unlocked_at     timestamptz DEFAULT now(),
    notified        boolean     DEFAULT false,      -- whether user was notified
    CONSTRAINT achievements_user_code_unique UNIQUE (user_id, code)
);

CREATE INDEX IF NOT EXISTS achievements_user_idx ON achievements (user_id);
