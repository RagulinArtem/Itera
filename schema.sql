-- =============================================
-- ITERA BOT — DATABASE SCHEMA
-- Supabase/PostgreSQL
-- =============================================
-- ВАЖНО: Эти таблицы уже существуют в продакшен БД.
-- Этот файл — справочный DDL для разработки.
-- НЕ запускать CREATE TABLE на продакшен БД без проверки.
-- Для новых таблиц (processed_updates) — запускать безопасно.
-- =============================================

-- Enum types
CREATE TYPE goal_status AS ENUM ('active', 'completed', 'archived');
CREATE TYPE habit_log_status AS ENUM ('done', 'missed');

-- =============================================
-- Profiles — пользователи бота
-- =============================================
CREATE TABLE IF NOT EXISTS "Profiles" (
    id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    nickname            text        DEFAULT '',
    email               text        DEFAULT '',
    created_at          timestamptz NOT NULL DEFAULT now(),
    telegram_id         bigint      NOT NULL,
    state               text        NULL,           -- FSM state: NULL | 'awaiting_checkin' | 'awaiting_goal_text' | 'awaiting_nickname' | 'awaiting_email' | 'awaiting_feedback'
    xp                  integer     DEFAULT 0,
    streak              integer     DEFAULT 0,
    last_checkin_date   date        NULL,
    reminder_enabled    boolean     NOT NULL DEFAULT true,
    last_reminder_date  date        NULL,
    ai_mode             text        NOT NULL DEFAULT 'manager',  -- 'manager' | 'psychologist'
    CONSTRAINT "Profiles_telegram_id_key" UNIQUE (telegram_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS "Profiles_pkey" ON "Profiles" (id);
CREATE UNIQUE INDEX IF NOT EXISTS "Profiles_telegram_id_key" ON "Profiles" (telegram_id);

-- =============================================
-- Goals — цели пользователей
-- =============================================
CREATE TABLE IF NOT EXISTS "Goals" (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at      timestamptz NOT NULL DEFAULT now(),
    user_id         uuid        NOT NULL REFERENCES "Profiles"(id) ON DELETE CASCADE,
    status          text        DEFAULT 'active',   -- 'active' | 'completed' | 'archived'
    goal            text,                           -- текст цели
    progress        bigint      DEFAULT 0,
    plan            jsonb       DEFAULT '{}',       -- структурированный план от AI
    plan_updated_at timestamptz DEFAULT now(),
    completed_at    timestamptz NULL
);

CREATE INDEX IF NOT EXISTS "Goals_user_id_idx" ON "Goals" (user_id);
CREATE INDEX IF NOT EXISTS "Goals_user_status_idx" ON "Goals" (user_id, status);

-- =============================================
-- journal_entries — чек-ины пользователей
-- =============================================
CREATE TABLE IF NOT EXISTS journal_entries (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid        NOT NULL REFERENCES "Profiles"(id) ON DELETE CASCADE,
    entry_date      date        NOT NULL,
    checkin_text    text,                   -- сырой текст пользователя
    analysis        jsonb,                  -- полный JSON-ответ от LLM
    created_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS "journal_entries_user_id_idx" ON journal_entries (user_id);
CREATE INDEX IF NOT EXISTS "journal_entries_user_date_idx" ON journal_entries (user_id, entry_date DESC);

-- =============================================
-- processed_updates — идемпотентность
-- Новая таблица для защиты от дублей Telegram updates
-- =============================================
CREATE TABLE IF NOT EXISTS processed_updates (
    update_id       bigint      PRIMARY KEY,
    processed_at    timestamptz DEFAULT now()
);

-- Автоочистка старых записей (старше 7 дней) — опционально
-- CREATE INDEX IF NOT EXISTS "processed_updates_time_idx" ON processed_updates (processed_at);

-- =============================================
-- Полезные запросы для справки
-- =============================================

-- UPSERT пользователя по telegram_id:
-- INSERT INTO "Profiles" (telegram_id)
-- VALUES ($1)
-- ON CONFLICT (telegram_id) DO UPDATE SET telegram_id = EXCLUDED.telegram_id
-- RETURNING *;

-- Активные цели пользователя:
-- SELECT id, goal, plan, progress FROM "Goals"
-- WHERE user_id = $1 AND status = 'active'
-- ORDER BY created_at ASC;

-- Последние N чек-инов пользователя:
-- SELECT entry_date, checkin_text, analysis, created_at
-- FROM journal_entries
-- WHERE user_id = $1
-- ORDER BY entry_date DESC, created_at DESC
-- LIMIT $2;

-- Обновление XP и streak после чек-ина:
-- UPDATE "Profiles"
-- SET xp = COALESCE(xp, 0) + 100,
--     streak = $2,
--     last_checkin_date = CURRENT_DATE
-- WHERE id = $1
-- RETURNING xp, streak;

-- Пользователи для напоминаний (21:00 MSK):
-- SELECT id, telegram_id FROM "Profiles"
-- WHERE reminder_enabled = true
--   AND telegram_id IS NOT NULL
--   AND COALESCE(last_checkin_date, '1900-01-01') < (now() AT TIME ZONE 'Europe/Moscow')::date
--   AND COALESCE(last_reminder_date, '1900-01-01') < (now() AT TIME ZONE 'Europe/Moscow')::date;
