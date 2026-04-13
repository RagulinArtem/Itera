"""Achievements & levels system."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from bot import database as db


# ─────────────────────────────────────────────
# Levels
# ─────────────────────────────────────────────

@dataclass
class Level:
    number: int
    name: str
    min_xp: int
    icon: str


LEVELS = [
    Level(1, "Новичок", 0, "🌱"),
    Level(2, "Ученик", 100, "📗"),
    Level(3, "Практик", 300, "📘"),
    Level(4, "Опытный", 600, "⚡"),
    Level(5, "Мастер", 1000, "🔥"),
    Level(6, "Эксперт", 1800, "💎"),
    Level(7, "Сенсей", 3000, "👑"),
]


def get_level(xp: int) -> Level:
    """Return current level based on XP."""
    result = LEVELS[0]
    for lvl in LEVELS:
        if xp >= lvl.min_xp:
            result = lvl
    return result


def get_next_level(xp: int) -> Level | None:
    """Return next level or None if max."""
    current = get_level(xp)
    for lvl in LEVELS:
        if lvl.min_xp > current.min_xp:
            return lvl
    return None


def format_level_progress(xp: int) -> str:
    """Format level info with progress bar."""
    level = get_level(xp)
    next_lvl = get_next_level(xp)
    if next_lvl is None:
        return f"{level.icon} *{level.name}* (MAX) — {xp} XP"

    progress = xp - level.min_xp
    needed = next_lvl.min_xp - level.min_xp
    bar_len = 10
    filled = min(bar_len, int(progress / needed * bar_len))
    bar = "▓" * filled + "░" * (bar_len - filled)
    return (
        f"{level.icon} *{level.name}* — {xp} XP\n"
        f"[{bar}] {progress}/{needed} до {next_lvl.icon} {next_lvl.name}"
    )


# ─────────────────────────────────────────────
# Achievement definitions
# ─────────────────────────────────────────────

@dataclass
class AchievementDef:
    code: str
    icon: str
    name: str
    description: str
    xp_reward: int


ACHIEVEMENT_DEFS: dict[str, AchievementDef] = {}


def _register(code: str, icon: str, name: str, desc: str, xp: int = 50) -> None:
    ACHIEVEMENT_DEFS[code] = AchievementDef(code, icon, name, desc, xp)


# Checkin achievements
_register("first_checkin", "🎉", "Первый шаг", "Сделай первый чекин", 50)
_register("streak_3", "🔥", "Разогрев", "Достигни streak 3 дня", 50)
_register("streak_7", "⚡", "Неделя огня", "Streak 7 дней подряд", 100)
_register("streak_14", "💪", "Двухнедельный марафон", "Streak 14 дней", 150)
_register("streak_30", "🏆", "Месяц дисциплины", "Streak 30 дней подряд", 300)
_register("checkins_10", "📝", "Десятка", "Сделай 10 чекинов", 100)
_register("checkins_50", "📚", "Полсотни", "Сделай 50 чекинов", 200)
_register("checkins_100", "🎓", "Сотня", "Сделай 100 чекинов", 500)

# Goal achievements
_register("first_goal", "🎯", "Целеустремлённый", "Создай первую цель", 50)
_register("goal_completed", "✅", "Финишёр", "Заверши первую цель", 100)
_register("goals_5", "🏅", "Многозадачный", "Создай 5 целей", 100)
_register("goals_completed_3", "🌟", "Серийный финишёр", "Заверши 3 цели", 200)

# Report achievements
_register("first_report", "📊", "Аналитик", "Запроси первый отчёт", 50)
_register("reports_5", "🔍", "Глубокий анализ", "Запроси 5 отчётов", 100)

# Mode achievements
_register("try_psychologist", "🧠", "Исследователь", "Попробуй режим психолога", 50)

# Level achievements
_register("level_3", "📘", "Практик", "Достигни 3-го уровня", 0)
_register("level_5", "🔥", "Мастер", "Достигни 5-го уровня", 0)
_register("level_7", "👑", "Сенсей", "Достигни максимального уровня", 0)


# ─────────────────────────────────────────────
# Check & unlock logic
# ─────────────────────────────────────────────

async def get_user_achievements(user_id: UUID) -> set[str]:
    """Return set of achievement codes user already has."""
    rows = await db._get_pool().fetch(
        "SELECT code FROM achievements WHERE user_id = $1",
        user_id,
    )
    return {r["code"] for r in rows}


async def unlock_achievement(user_id: UUID, code: str) -> AchievementDef | None:
    """Try to unlock an achievement. Returns def if newly unlocked, None if already had."""
    if code not in ACHIEVEMENT_DEFS:
        return None

    row = await db._get_pool().fetchrow(
        """
        INSERT INTO achievements (user_id, code)
        VALUES ($1, $2)
        ON CONFLICT (user_id, code) DO NOTHING
        RETURNING id
        """,
        user_id,
        code,
    )
    if row is None:
        return None  # already unlocked

    defn = ACHIEVEMENT_DEFS[code]
    if defn.xp_reward > 0:
        await db.add_xp(user_id, defn.xp_reward)
    return defn


async def check_checkin_achievements(
    user_id: UUID,
    new_streak: int,
    total_checkins: int | None = None,
) -> list[AchievementDef]:
    """Check and unlock checkin-related achievements. Returns newly unlocked list."""
    unlocked: list[AchievementDef] = []

    # Count total checkins if not provided
    if total_checkins is None:
        row = await db._get_pool().fetchrow(
            "SELECT COUNT(*) as cnt FROM journal_entries WHERE user_id = $1",
            user_id,
        )
        total_checkins = row["cnt"] if row else 0

    # First checkin
    if total_checkins >= 1:
        if r := await unlock_achievement(user_id, "first_checkin"):
            unlocked.append(r)

    # Streak achievements
    streak_checks = [(3, "streak_3"), (7, "streak_7"), (14, "streak_14"), (30, "streak_30")]
    for threshold, code in streak_checks:
        if new_streak >= threshold:
            if r := await unlock_achievement(user_id, code):
                unlocked.append(r)

    # Total checkins
    checkin_checks = [(10, "checkins_10"), (50, "checkins_50"), (100, "checkins_100")]
    for threshold, code in checkin_checks:
        if total_checkins >= threshold:
            if r := await unlock_achievement(user_id, code):
                unlocked.append(r)

    # Check level achievements after XP changes
    unlocked.extend(await _check_level_achievements(user_id))

    return unlocked


async def check_goal_achievements(user_id: UUID) -> list[AchievementDef]:
    """Check goal-related achievements."""
    unlocked: list[AchievementDef] = []

    total_goals = await db._get_pool().fetchval(
        'SELECT COUNT(*) FROM "Goals" WHERE user_id = $1', user_id
    )
    completed_goals = await db._get_pool().fetchval(
        'SELECT COUNT(*) FROM "Goals" WHERE user_id = $1 AND status = \'completed\'', user_id
    )

    if total_goals >= 1:
        if r := await unlock_achievement(user_id, "first_goal"):
            unlocked.append(r)
    if total_goals >= 5:
        if r := await unlock_achievement(user_id, "goals_5"):
            unlocked.append(r)
    if completed_goals >= 1:
        if r := await unlock_achievement(user_id, "goal_completed"):
            unlocked.append(r)
    if completed_goals >= 3:
        if r := await unlock_achievement(user_id, "goals_completed_3"):
            unlocked.append(r)

    unlocked.extend(await _check_level_achievements(user_id))
    return unlocked


async def check_report_achievements(user_id: UUID) -> list[AchievementDef]:
    """Check report-related achievements."""
    unlocked: list[AchievementDef] = []

    # Count reports (journal entries used as proxy, or we can count report requests)
    # For simplicity, use a counter approach
    existing = await get_user_achievements(user_id)
    if "first_report" not in existing:
        if r := await unlock_achievement(user_id, "first_report"):
            unlocked.append(r)

    return unlocked


async def check_mode_achievement(user_id: UUID, mode: str) -> list[AchievementDef]:
    """Check mode-switch achievements."""
    unlocked: list[AchievementDef] = []
    if mode == "psychologist":
        if r := await unlock_achievement(user_id, "try_psychologist"):
            unlocked.append(r)
    return unlocked


async def _check_level_achievements(user_id: UUID) -> list[AchievementDef]:
    """Check if user reached level milestones."""
    unlocked: list[AchievementDef] = []
    user = await db.get_user_by_id(user_id)
    if not user:
        return unlocked

    xp = user["xp"] or 0
    level = get_level(xp)

    level_checks = [(3, "level_3"), (5, "level_5"), (7, "level_7")]
    for threshold, code in level_checks:
        if level.number >= threshold:
            if r := await unlock_achievement(user_id, code):
                unlocked.append(r)

    return unlocked


def format_achievement_unlocked(ach: AchievementDef) -> str:
    """Format achievement unlock notification."""
    xp_text = f" (+{ach.xp_reward} XP)" if ach.xp_reward > 0 else ""
    return f"🏅 *Ачивка разблокирована!*\n{ach.icon} *{ach.name}*\n_{ach.description}_{xp_text}"


def format_achievements_list(unlocked_codes: set[str]) -> str:
    """Format all achievements for display."""
    lines: list[str] = ["🏅 *Ачивки*\n"]

    categories = [
        ("Чекины", ["first_checkin", "streak_3", "streak_7", "streak_14", "streak_30",
                     "checkins_10", "checkins_50", "checkins_100"]),
        ("Цели", ["first_goal", "goal_completed", "goals_5", "goals_completed_3"]),
        ("Аналитика", ["first_report", "reports_5"]),
        ("Режимы", ["try_psychologist"]),
        ("Уровни", ["level_3", "level_5", "level_7"]),
    ]

    total = len(ACHIEVEMENT_DEFS)
    got = len(unlocked_codes & set(ACHIEVEMENT_DEFS.keys()))
    lines.append(f"Прогресс: {got}/{total}\n")

    for cat_name, codes in categories:
        lines.append(f"*{cat_name}:*")
        for code in codes:
            defn = ACHIEVEMENT_DEFS[code]
            if code in unlocked_codes:
                lines.append(f"  {defn.icon} {defn.name} — _{defn.description}_")
            else:
                lines.append(f"  🔒 {defn.name} — _{defn.description}_")
        lines.append("")

    return "\n".join(lines)
