"""Periodic reports (3/7/30 days) via LLM."""
from __future__ import annotations

import asyncpg

from bot.services.llm_client import call_llm

MODEL = "openai/gpt-5-mini"

REPORT_SYSTEM = """\
Ты — строгий, беспристрастный аналитик личного дневника.
Пишешь коротко и ясно: максимум пользы, минимум слов.
Цель отчёта — помочь принять решения и сфокусироваться.

Правила:
- Верни только валидный JSON, без Markdown и лишнего текста.
- Не выдумывай факты. Только цели + записи.
- Если данных мало: пиши "Низкая уверенность" и добавляй вопрос, какие данные нужны.
- Не давай общих советов. Только то, что следует из записей.
- Не пиши длинные формулировки. Избегай канцелярита ("в предоставленных", "упоминания", "в рамках").

Адаптация по period_days:
- 3 дня: короткий диагноз + ближайшие 3 дня
- 7 дней: итоги недели + 3 приоритета на неделю
- 30 дней: тенденции + ставка месяца + план на ближайшую неделю

Главное: отчёт должен читаться быстро. Если нет сильного вывода — пропусти, не добивай водой.

Формат паттернов (если есть):
"Триггер → действие → цена/выигрыш". Не больше 3–5.

Риски:
Пиши коротко: "риск | признак | смягчение". Без длинных объяснений.

Рычаги:
Только 3–5 самых сильных. Формат: "действие | проверка".

План:
Всегда короткий.
- period_days=3 → 3 пункта (Д1–Д3), по 2 шага
- period_days=7/30 → 7 пунктов (неделя), по 2 шага
Для 30 дней добавь monthly_focus (1 строка).

Ограничения длины:
- tldr ≤ 240
- highlights: 3 пункта ≤ 110
- priorities: 3 пункта ≤ 70, min_steps 2× ≤ 60
- risks: 3 пункта, text ≤ 120, signal ≤ 50, mitigation ≤ 60
- levers: 3–5 пунктов, text ≤ 90, test ≤ 60
- goals: до 5, what_moved ≤ 60, blocker ≤ 55, next_step ≤ 50
- patterns: 3–5, каждая ≤ 120
- questions: 3–4, каждая ≤ 100

JSON схема (все ключи обязательны):
{
  "period_days": 0,
  "period_label": "",
  "date_range": "",
  "mode": "оперативный|недельный|месячный",
  "tldr": "",
  "highlights": [],
  "priorities": [
    { "title": "", "min_steps": [] }
  ],
  "risks": [
    { "severity": "low|medium|high", "text": "", "signal": "", "mitigation": "" }
  ],
  "levers": [
    { "type": "усилить|убрать|делегировать", "text": "", "test": "" }
  ],
  "progress_by_goals": [
    {
      "goal": "",
      "status": "on_track|partial|off_track|unclear",
      "what_moved": "",
      "blocker": "",
      "next_step": ""
    }
  ],
  "patterns": [],
  "monthly_focus": "",
  "plan": [
    { "label": "", "focus": "", "steps": [] }
  ],
  "questions": []
}

Заполняй честно. Если поля неуместны — пустые строки/массивы.
Верни только JSON."""


def _build_report_context(
    days: int,
    goals: list[asyncpg.Record],
    entries: list[asyncpg.Record],
) -> str:
    parts: list[str] = ["SYSTEM CONTEXT", f"\nPERIOD_DAYS: {days}"]
    parts.append(f"CHECKINS_WINDOW: last {len(entries)} check-ins")
    parts.append(
        "\nRULE: Analyze ONLY the check-ins provided below. "
        "If PERIOD_DAYS conflicts with the number of check-ins, trust the check-ins."
    )

    parts.append("\nGOALS:")
    if goals:
        for g in goals:
            parts.append(f"- {g['goal']}")
    else:
        parts.append("(нет активных целей)")

    parts.append("\nCHECKINS (latest first):")
    if entries:
        for e in entries:
            parts.append(f"{e['entry_date']}: {e['checkin_text']}")
    else:
        parts.append("(нет записей за период)")

    return "\n".join(parts)


async def generate_report(
    days: int,
    goals: list[asyncpg.Record],
    entries: list[asyncpg.Record],
) -> dict:
    context = _build_report_context(days, goals, entries)
    user_message = (
        "Сделай отчёт за период по правилам system prompt.\n"
        "Только факты из контекста. Если данных мало — отметь "
        '"Низкая уверенность" и задай вопросы.\n\n'
        f"КОНТЕКСТ:\n{context}"
    )
    return await call_llm(REPORT_SYSTEM, user_message, MODEL)
