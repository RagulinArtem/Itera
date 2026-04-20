"""Auto-insights: detect patterns every 5-7 checkins and send proactive message."""
from __future__ import annotations

import logging
from typing import Any

from bot import database as db
from bot.services.llm_client import call_llm

logger = logging.getLogger(__name__)

MODEL = "openai/gpt-4.1-mini"
CHECKINS_BETWEEN_INSIGHTS = 5

INSIGHT_SYSTEM = """\
Ты — аналитик поведенческих паттернов. Тебе дано {count} последних чек-инов пользователя.

Твоя задача — найти паттерны, тренды и закономерности, которые пользователь может не замечать сам.

ПРАВИЛА:
- Анализируй ТОЛЬКО факты из чек-инов. Не выдумывай.
- Ищи: повторяющиеся темы, эмоциональные паттерны, продуктивные/непродуктивные дни недели, прогресс к целям.
- Если есть данные о настроении (mood 1-5), анализируй тренд настроения.
- Тон: дружелюбный, конкретный, без воды.
- Язык: русский.

Верни JSON:
{{
  "has_insight": true/false,
  "title": "Краткий заголовок инсайта (до 50 символов)",
  "text": "Текст инсайта (2-4 предложения, конкретно и полезно)",
  "pattern_type": "productivity|mood|consistency|goals|growth",
  "confidence": 0.0-1.0
}}

Если паттернов нет или данных мало — верни has_insight: false.
"""


async def check_and_generate_insight(user_id) -> dict[str, Any] | None:
    """Check if it's time for an insight and generate one if so.

    Returns insight dict or None.
    """
    # Count checkins since last insight
    total_checkins = await db._get_pool().fetchval(
        "SELECT COUNT(*) FROM journal_entries WHERE user_id = $1",
        user_id,
    )

    if total_checkins < CHECKINS_BETWEEN_INSIGHTS:
        return None

    # Check if we should generate (every N checkins)
    if total_checkins % CHECKINS_BETWEEN_INSIGHTS != 0:
        return None

    # Get recent checkins for analysis
    entries = await db.get_journal_entries(user_id, limit=CHECKINS_BETWEEN_INSIGHTS + 2)
    if len(entries) < CHECKINS_BETWEEN_INSIGHTS:
        return None

    # Build context
    lines = []
    for e in entries:
        mood_str = ""
        if e.get("mood"):
            mood_str = f" [mood: {e['mood']}/5]"
        lines.append(f"{e['entry_date']}{mood_str}: {e['checkin_text']}")

    context = "\n\n".join(lines)

    # Get goals for context
    goals = await db.get_active_goals(user_id)
    goals_text = "\n".join(f"- {g['goal']}" for g in goals) if goals else "Нет активных целей"

    user_message = (
        f"ЦЕЛИ:\n{goals_text}\n\n"
        f"ПОСЛЕДНИЕ {len(entries)} ЧЕК-ИНОВ:\n{context}"
    )

    try:
        result = await call_llm(
            INSIGHT_SYSTEM.format(count=len(entries)),
            user_message,
            MODEL,
        )
        if result.get("has_insight") and result.get("confidence", 0) >= 0.6:
            return result
    except Exception:
        logger.exception("Auto-insight generation failed for user %s", user_id)

    return None


def format_insight(insight: dict[str, Any]) -> str:
    """Format insight for Telegram message."""
    type_icons = {
        "productivity": "📊",
        "mood": "💭",
        "consistency": "🔄",
        "goals": "🎯",
        "growth": "📈",
    }
    icon = type_icons.get(insight.get("pattern_type", ""), "💡")
    return (
        f"{icon} *Авто-инсайт*\n\n"
        f"*{insight.get('title', 'Наблюдение')}*\n\n"
        f"{insight.get('text', '')}"
    )
