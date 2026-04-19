"""'Ask Itera' — free-form questions about user's patterns and history."""
from __future__ import annotations

import json
from typing import Any

from bot.services.llm_client import call_llm

MODEL = "openai/gpt-4.1-mini"

ASK_SYSTEM = """\
Ты — аналитик-ассистент Itera. Пользователь задаёт вопрос о своих паттернах, \
привычках и прогрессе. У тебя есть полный контекст: история чекинов, цели, статистика.

ПРАВИЛА:
- Отвечай конкретно, опираясь ТОЛЬКО на данные из контекста
- Если данных недостаточно — честно скажи
- Используй цифры: даты, количества, проценты
- Формат: обычный текст для Telegram (Markdown)
- Не длиннее 1500 символов
- Язык: русский

Верни JSON:
{
  "answer": "текст ответа в Markdown",
  "confidence": "high" | "medium" | "low"
}
"""


async def ask_itera(
    question: str,
    goals: list[dict[str, Any]],
    history: list[dict[str, Any]],
    xp: int,
    streak: int,
    nickname: str,
) -> dict:
    """Answer a free-form question about user's data."""
    goals_text = "\n".join(
        f"- {g['goal']} (статус: {g.get('status', 'active')})"
        for g in goals
    ) or "Нет целей"

    history_lines = []
    for entry in history:
        d = entry.get("entry_date", "?")
        text = (entry.get("checkin_text") or "")[:200]
        history_lines.append(f"[{d}] {text}")
    history_text = "\n".join(history_lines) or "Нет записей"

    user_message = (
        f"ПРОФИЛЬ: {nickname}, XP={xp}, Streak={streak} дн.\n\n"
        f"ЦЕЛИ:\n{goals_text}\n\n"
        f"ИСТОРИЯ ЧЕКИНОВ (последние):\n{history_text}\n\n"
        f"ВОПРОС: {question}"
    )

    return await call_llm(ASK_SYSTEM, user_message, MODEL)
