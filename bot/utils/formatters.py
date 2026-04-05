"""Format LLM JSON responses into Telegram messages."""
from __future__ import annotations

import json
from typing import Any


def format_manager_checkin(data: dict[str, Any]) -> str:
    """Format manager mode check-in analysis into a readable message."""
    lines: list[str] = []

    # Header
    sphere = data.get("focus_sphere", "")
    verdict = data.get("verdict", {})
    v_icon = verdict.get("value", "")
    v_reason = verdict.get("reason", "")
    lines.append(f"{v_icon} *Слепок дня* — {sphere}")
    if v_reason:
        lines.append(f"_{v_reason}_")
    lines.append("")

    # Main quest
    mq = data.get("main_quest", {})
    if mq.get("text"):
        lines.append(f"🎯 *Главный результат:* {mq['text']}")
        if mq.get("evidence"):
            lines.append(f"   _{mq['evidence']}_")
        lines.append("")

    # Day conclusion
    conclusion = data.get("day_conclusion", "")
    if conclusion:
        lines.append(f"📝 {conclusion}")
        lines.append("")

    # Goals alignment
    goals = data.get("goals_alignment", [])
    if goals:
        lines.append("*Цели:*")
        alignment_icons = {
            "on_track": "🟢",
            "partial": "🟡",
            "off_track": "🔴",
            "unclear": "⚪",
        }
        for g in goals:
            icon = alignment_icons.get(g.get("alignment", ""), "⚪")
            lines.append(f"{icon} {g.get('goal_short', '')} — _{g.get('evidence', '')}_")
        lines.append("")

    # Insights
    insights = data.get("insights", [])
    if insights:
        lines.append("*Аналитика:*")
        for ins in insights:
            lines.append(f"• {ins}")
        lines.append("")

    # Risk
    risk = data.get("risk", "")
    if risk:
        lines.append(f"⚠️ *Риск:* {risk}")
        lines.append("")

    # Metrics hint
    hint = data.get("metrics_hint", "")
    if hint:
        lines.append(f"📏 *Метрика:* {hint}")
        lines.append("")

    # Sphere fact
    fact = data.get("sphere_fact", "")
    if fact:
        lines.append(f"💡 {fact}")
        lines.append("")

    # Momentum
    momentum = data.get("momentum", "")
    momentum_labels = {
        "accelerated": "⚡ Ускорение",
        "slowed_down": "🐢 Замедление",
        "pivoted": "🔄 Разворот",
    }
    if momentum and momentum in momentum_labels:
        lines.append(f"*Инерция:* {momentum_labels[momentum]}")
        lines.append("")

    # Gamification
    gam = data.get("gamification", {})
    if gam:
        lines.append(
            f"🏅 XP: {gam.get('xp_total', 0)} (+{gam.get('xp_gained', 0)})  "
            f"🔥 Streak: {gam.get('streak_days', 0)} дн."
        )
        comment = gam.get("streak_comment", "")
        if comment:
            lines.append(f"_{comment}_")

    return "\n".join(lines)


def format_psychologist_checkin(data: dict[str, Any]) -> str:
    """Format psychologist mode response. Uses pre-formatted text_markdown from LLM."""
    telegram = data.get("telegram", {})
    text = telegram.get("text_markdown", "")
    if text:
        return text

    # Fallback: build from response fields
    resp = data.get("response", {})
    lines: list[str] = []
    if resp.get("mirror"):
        lines.append(resp["mirror"])
    if resp.get("reframe"):
        lines.append(f"\n{resp['reframe']}")
    step = resp.get("one_small_step", {})
    if step.get("title"):
        minutes = step.get("minutes", 5)
        lines.append(f"\n✅ Шаг на {minutes} минут: {step['title']}")
        if step.get("why_easy"):
            lines.append(f"_{step['why_easy']}_")
    if resp.get("question"):
        lines.append(f"\n{resp['question']}")
    return "\n".join(lines)


def format_report_panel(data: dict[str, Any]) -> str:
    """Format report message 1: TL;DR + highlights + priorities + risks + levers."""
    lines: list[str] = []

    period = data.get("period_label", "")
    date_range = data.get("date_range", "")
    lines.append(f"📊 *Отчёт: {period}*")
    if date_range:
        lines.append(f"_{date_range}_")
    lines.append("")

    tldr = data.get("tldr", "")
    if tldr:
        lines.append(f"*TL;DR:* {tldr}")
        lines.append("")

    highlights = data.get("highlights", [])
    if highlights:
        lines.append("*Факты:*")
        for h in highlights:
            lines.append(f"• {h}")
        lines.append("")

    priorities = data.get("priorities", [])
    if priorities:
        lines.append("*Приоритеты:*")
        for i, p in enumerate(priorities, 1):
            lines.append(f"{i}. {p.get('title', '')}")
            for s in p.get("min_steps", []):
                lines.append(f"   → {s}")
        lines.append("")

    risks = data.get("risks", [])
    if risks:
        severity_icons = {"low": "🟡", "medium": "🟠", "high": "🔴"}
        lines.append("*Риски:*")
        for r in risks:
            icon = severity_icons.get(r.get("severity", ""), "⚪")
            lines.append(f"{icon} {r.get('text', '')}")
            sig = r.get("signal", "")
            mit = r.get("mitigation", "")
            if sig or mit:
                lines.append(f"   _{sig}_ → {mit}")
        lines.append("")

    levers = data.get("levers", [])
    if levers:
        lines.append("*Рычаги:*")
        for lv in levers:
            lines.append(f"• [{lv.get('type', '')}] {lv.get('text', '')} — _{lv.get('test', '')}_")
        lines.append("")

    return "\n".join(lines)


def format_report_drilldown(data: dict[str, Any]) -> str:
    """Format report message 2: goals progress + patterns + plan + questions."""
    lines: list[str] = []

    goals = data.get("progress_by_goals", [])
    if goals:
        status_icons = {
            "on_track": "🟢",
            "partial": "🟡",
            "off_track": "🔴",
            "unclear": "⚪",
        }
        lines.append("*Прогресс по целям:*")
        for g in goals:
            icon = status_icons.get(g.get("status", ""), "⚪")
            lines.append(f"{icon} *{g.get('goal', '')}*")
            if g.get("what_moved"):
                lines.append(f"   Продвинулось: {g['what_moved']}")
            if g.get("blocker"):
                lines.append(f"   Блокер: {g['blocker']}")
            if g.get("next_step"):
                lines.append(f"   Следующий шаг: {g['next_step']}")
        lines.append("")

    patterns = data.get("patterns", [])
    if patterns:
        lines.append("*Паттерны:*")
        for p in patterns:
            lines.append(f"• {p}")
        lines.append("")

    monthly = data.get("monthly_focus", "")
    if monthly:
        lines.append(f"🎯 *Фокус месяца:* {monthly}")
        lines.append("")

    plan = data.get("plan", [])
    if plan:
        lines.append("*План:*")
        for day in plan:
            lines.append(f"*{day.get('label', '')}* — {day.get('focus', '')}")
            for s in day.get("steps", []):
                lines.append(f"  → {s}")
        lines.append("")

    questions = data.get("questions", [])
    if questions:
        lines.append("*Вопросы для рефлексии:*")
        for q in questions:
            lines.append(f"❓ {q}")

    return "\n".join(lines)


def format_goal_card(goal_record) -> str:
    """Format a single goal card with plan steps."""
    lines: list[str] = []
    lines.append(f"🎯 *Цель:* {goal_record['goal']}")

    status = goal_record.get("status", "active")
    status_icons = {"active": "🟢 Active", "completed": "✅ Completed", "archived": "⏸ Archived"}
    lines.append(f"📌 *Статус:* {status_icons.get(status, status)}")

    plan = goal_record.get("plan")
    if plan:
        plan_data = plan if isinstance(plan, dict) else json.loads(plan)
        items = plan_data.get("items", [])
        if items:
            lines.append("")
            lines.append("🧩 *План / шаги:*")
            for i, item in enumerate(items, 1):
                label = item.get("label", "")
                lines.append(f"🧩 *Шаг {i}:* {label}")
                signals = item.get("signals", [])
                if signals:
                    lines.append(f"   _{' · '.join(signals)}_")
                definition = item.get("definition", "")
                if definition:
                    lines.append(f"   {definition}")

    return "\n".join(lines)
