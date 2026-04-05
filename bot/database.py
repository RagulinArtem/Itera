from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any
from uuid import UUID

import asyncpg

from bot.config import settings

logger = logging.getLogger(__name__)

pool: asyncpg.Pool | None = None


async def create_pool() -> asyncpg.Pool:
    global pool
    pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=2,
        max_size=10,
        command_timeout=30,
    )
    logger.info("Database pool created")
    return pool


async def close_pool() -> None:
    global pool
    if pool:
        await pool.close()
        pool = None
        logger.info("Database pool closed")


def _get_pool() -> asyncpg.Pool:
    if pool is None:
        raise RuntimeError("Database pool is not initialized")
    return pool


# ─────────────────────────────────────────────
# Profiles
# ─────────────────────────────────────────────

async def get_or_create_user(telegram_id: int) -> asyncpg.Record:
    """Upsert user by telegram_id. Returns full profile row."""
    return await _get_pool().fetchrow(
        """
        INSERT INTO "Profiles" (telegram_id)
        VALUES ($1)
        ON CONFLICT (telegram_id) DO UPDATE SET telegram_id = EXCLUDED.telegram_id
        RETURNING *
        """,
        telegram_id,
    )


async def get_user_by_telegram_id(telegram_id: int) -> asyncpg.Record | None:
    return await _get_pool().fetchrow(
        'SELECT * FROM "Profiles" WHERE telegram_id = $1',
        telegram_id,
    )


async def get_user_by_id(user_id: UUID) -> asyncpg.Record | None:
    return await _get_pool().fetchrow(
        'SELECT * FROM "Profiles" WHERE id = $1',
        user_id,
    )


async def update_user_state(telegram_id: int, state: str | None) -> None:
    await _get_pool().execute(
        'UPDATE "Profiles" SET state = $2 WHERE telegram_id = $1',
        telegram_id,
        state,
    )


async def update_nickname(telegram_id: int, nickname: str) -> None:
    await _get_pool().execute(
        'UPDATE "Profiles" SET nickname = $2 WHERE telegram_id = $1',
        telegram_id,
        nickname,
    )


async def update_email(telegram_id: int, email: str) -> None:
    await _get_pool().execute(
        'UPDATE "Profiles" SET email = $2 WHERE telegram_id = $1',
        telegram_id,
        email,
    )


async def update_ai_mode(telegram_id: int, mode: str) -> None:
    await _get_pool().execute(
        'UPDATE "Profiles" SET ai_mode = $2 WHERE telegram_id = $1',
        telegram_id,
        mode,
    )


async def update_reminder_enabled(telegram_id: int, enabled: bool) -> None:
    await _get_pool().execute(
        'UPDATE "Profiles" SET reminder_enabled = $2 WHERE telegram_id = $1',
        telegram_id,
        enabled,
    )


async def update_xp_streak(
    user_id: UUID,
    new_streak: int,
    xp_add: int = 100,
) -> asyncpg.Record:
    """Add XP and set new streak after check-in. Returns updated xp, streak."""
    return await _get_pool().fetchrow(
        """
        UPDATE "Profiles"
        SET xp = COALESCE(xp, 0) + $2,
            streak = $3,
            last_checkin_date = CURRENT_DATE
        WHERE id = $1
        RETURNING xp, streak
        """,
        user_id,
        xp_add,
        new_streak,
    )


async def add_xp(user_id: UUID, xp_add: int = 100) -> None:
    """Add XP without changing streak (e.g. goal creation)."""
    await _get_pool().execute(
        'UPDATE "Profiles" SET xp = COALESCE(xp, 0) + $2 WHERE id = $1',
        user_id,
        xp_add,
    )


async def update_last_reminder_date(user_id: UUID) -> None:
    await _get_pool().execute(
        'UPDATE "Profiles" SET last_reminder_date = CURRENT_DATE WHERE id = $1',
        user_id,
    )


async def get_users_for_reminder() -> list[asyncpg.Record]:
    """Users who need a reminder: reminder enabled, no check-in today, no reminder today."""
    return await _get_pool().fetch(
        """
        SELECT id, telegram_id FROM "Profiles"
        WHERE reminder_enabled = true
          AND telegram_id IS NOT NULL
          AND COALESCE(last_checkin_date, '1900-01-01') < (now() AT TIME ZONE 'Europe/Moscow')::date
          AND COALESCE(last_reminder_date, '1900-01-01') < (now() AT TIME ZONE 'Europe/Moscow')::date
        """
    )


# ─────────────────────────────────────────────
# Goals
# ─────────────────────────────────────────────

async def get_active_goals(user_id: UUID) -> list[asyncpg.Record]:
    return await _get_pool().fetch(
        """
        SELECT id, goal, plan, progress, status, created_at
        FROM "Goals"
        WHERE user_id = $1 AND status = 'active'
        ORDER BY created_at ASC
        """,
        user_id,
    )


async def get_all_goals(user_id: UUID) -> list[asyncpg.Record]:
    return await _get_pool().fetch(
        """
        SELECT id, goal, plan, progress, status, created_at, completed_at
        FROM "Goals"
        WHERE user_id = $1
        ORDER BY created_at DESC
        """,
        user_id,
    )


async def get_goal_by_id(goal_id: UUID) -> asyncpg.Record | None:
    return await _get_pool().fetchrow(
        'SELECT * FROM "Goals" WHERE id = $1',
        goal_id,
    )


async def create_goal(
    user_id: UUID,
    goal_text: str,
    plan: dict[str, Any],
) -> asyncpg.Record:
    return await _get_pool().fetchrow(
        """
        INSERT INTO "Goals" (user_id, goal, plan, status, progress)
        VALUES ($1, $2, $3::jsonb, 'active', 0)
        RETURNING *
        """,
        user_id,
        goal_text,
        json.dumps(plan),
    )


async def update_goal_status(goal_id: UUID, status: str) -> None:
    completed_clause = ", completed_at = now()" if status == "completed" else ""
    await _get_pool().execute(
        f'UPDATE "Goals" SET status = $2{completed_clause} WHERE id = $1',
        goal_id,
        status,
    )


async def delete_goal(goal_id: UUID) -> None:
    await _get_pool().execute(
        'DELETE FROM "Goals" WHERE id = $1',
        goal_id,
    )


# ─────────────────────────────────────────────
# Journal Entries
# ─────────────────────────────────────────────

async def save_checkin(
    user_id: UUID,
    entry_date: date,
    checkin_text: str,
    analysis: dict[str, Any],
) -> asyncpg.Record:
    return await _get_pool().fetchrow(
        """
        INSERT INTO journal_entries (user_id, entry_date, checkin_text, analysis)
        VALUES ($1, $2, $3, $4::jsonb)
        RETURNING *
        """,
        user_id,
        entry_date,
        checkin_text,
        json.dumps(analysis),
    )


async def get_journal_entries(
    user_id: UUID,
    limit: int = 10,
) -> list[asyncpg.Record]:
    return await _get_pool().fetch(
        """
        SELECT entry_date, checkin_text, analysis, created_at
        FROM journal_entries
        WHERE user_id = $1
        ORDER BY entry_date DESC, created_at DESC
        LIMIT $2
        """,
        user_id,
        limit,
    )


async def has_checkin_today(user_id: UUID) -> bool:
    row = await _get_pool().fetchrow(
        """
        SELECT 1 FROM journal_entries
        WHERE user_id = $1 AND entry_date = CURRENT_DATE
        LIMIT 1
        """,
        user_id,
    )
    return row is not None


# ─────────────────────────────────────────────
# Idempotency (processed_updates)
# ─────────────────────────────────────────────

async def check_and_mark_update(update_id: int) -> bool:
    """Returns True if this update was already processed (duplicate)."""
    row = await _get_pool().fetchrow(
        """
        INSERT INTO processed_updates (update_id)
        VALUES ($1)
        ON CONFLICT DO NOTHING
        RETURNING update_id
        """,
        update_id,
    )
    return row is None  # None means ON CONFLICT fired → duplicate


async def cleanup_old_updates(days: int = 7) -> None:
    """Remove processed_updates older than N days."""
    await _get_pool().execute(
        "DELETE FROM processed_updates WHERE processed_at < now() - make_interval(days => $1)",
        days,
    )
