"""Check-in flow handler with pre-checkin mode selector."""
from __future__ import annotations

import logging
from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import database as db
from bot.fsm.states import IteraStates
from bot.keyboards.main_menu import back_to_menu_kb, cancel_kb
from bot.services.achievements import check_checkin_achievements, format_achievement_unlocked
from bot.services.auto_insights import check_and_generate_insight, format_insight
from bot.services.checkin_ai import analyze_checkin_manager
from bot.services.coach_ai import analyze_checkin_coach
from bot.services.psychologist_ai import analyze_checkin_psychologist
from bot.services.reflection_ai import analyze_checkin_reflection
from bot.utils.formatters import (
    format_coach_checkin,
    format_manager_checkin,
    format_psychologist_checkin,
    format_reflection_checkin,
)

router = Router()
logger = logging.getLogger(__name__)

# Mood options: value → (emoji, label)
MOODS = [
    (1, "😫", "Тяжело"),
    (2, "😔", "Так себе"),
    (3, "😐", "Нормально"),
    (4, "🙂", "Хорошо"),
    (5, "🔥", "Отлично"),
]


def mood_kb() -> InlineKeyboardMarkup:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{emoji}", callback_data=f"mood:{val}")
         for val, emoji, _ in MOODS],
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="mood:skip")],
    ])


# Prompt texts shown before checkin input
MODE_PROMPTS = {
    "focus": (
        "🎯 *Режим: Фокус*\n\n"
        "Опиши свой день:\n"
        "1. Что сделал?\n"
        "2. Что не получилось?\n"
        "3. Что понял/осознал?\n"
        "4. 1–3 действия на завтра"
    ),
    "support": (
        "💛 *Режим: Поддержка*\n\n"
        "Расскажи свободно: как прошёл день? Что чувствуешь?\n"
        "Пропуск — не провал. Возвращаемся мягко."
    ),
    "coach": (
        "🚀 *Режим: Коуч*\n\n"
        "Расскажи честно: что сделал, а что нет?\n"
        "Коуч будет прямолинеен — готов к вызову?"
    ),
    "reflection": (
        "🪞 *Режим: Рефлексия*\n\n"
        "Расскажи о своём дне свободно.\n"
        "Я задам вопросы, которые помогут разобраться самому."
    ),
}


def _calculate_streak(
    last_checkin_date: date | None,
    current_streak: int,
    streak_shield_used_at: date | None = None,
) -> tuple[int, bool]:
    """Calculate new streak. Returns (new_streak, shield_used).

    Shield activates automatically if user missed exactly 1 day
    and shield wasn't used in last 7 days.
    """
    today = date.today()
    if last_checkin_date is None:
        return 1, False
    delta = (today - last_checkin_date).days
    if delta == 1:
        return current_streak + 1, False
    elif delta == 0:
        return current_streak, False
    elif delta == 2 and current_streak >= 3:
        # Missed exactly 1 day — check shield eligibility
        shield_available = (
            streak_shield_used_at is None
            or (today - streak_shield_used_at).days >= 7
        )
        if shield_available:
            return current_streak, True  # shield saves the streak
    return 1, False


@router.callback_query(F.data == "menu:checkin")
async def cb_start_checkin(callback: CallbackQuery, state: FSMContext) -> None:
    tg_id = callback.from_user.id
    user = await db.get_or_create_user(tg_id)
    goals = await db.get_active_goals(user["id"])

    if not goals:
        await callback.message.edit_text(
            "Пока нет целей. Создай первую цель через 🎯 Цели в меню.",
            reply_markup=back_to_menu_kb(),
        )
        await callback.answer()
        return

    # Check if already checked in today
    if user["last_checkin_date"] == date.today():
        await callback.message.edit_text(
            "✅ Ты уже делал check-in сегодня. Возвращайся завтра!",
            reply_markup=back_to_menu_kb(),
        )
        await callback.answer()
        return

    # Ask mood first, then go to checkin text
    mode = user["ai_mode"] or "focus"
    await state.update_data(checkin_mode=mode)

    await callback.message.edit_text(
        "Как ты себя сейчас чувствуешь?",
        reply_markup=mood_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mood:"))
async def cb_mood_selected(callback: CallbackQuery, state: FSMContext) -> None:
    mood_val = callback.data.split(":")[1]
    if mood_val != "skip":
        await state.update_data(mood=int(mood_val))

    await state.set_state(IteraStates.awaiting_checkin)
    data = await state.get_data()
    mode = data.get("checkin_mode", "focus")
    prompt_text = MODE_PROMPTS.get(mode, MODE_PROMPTS["focus"])
    await callback.message.edit_text(prompt_text, reply_markup=cancel_kb(), parse_mode="Markdown")
    await callback.answer()


@router.message(IteraStates.awaiting_checkin)
async def process_checkin(message: Message, state: FSMContext) -> None:
    tg_id = message.from_user.id
    checkin_text = message.text
    if not checkin_text:
        await message.answer("Отправь текстовое сообщение.", reply_markup=cancel_kb())
        return

    user = await db.get_or_create_user(tg_id)

    # Double-check: no duplicate today
    if await db.has_checkin_today(user["id"]):
        await state.clear()
        await db.update_user_state(tg_id, None)
        await message.answer(
            "✅ Check-in за сегодня уже сохранён.",
            reply_markup=back_to_menu_kb(),
        )
        return

    # Get selected mode and mood from FSM data
    state_data = await state.get_data()
    ai_mode = state_data.get("checkin_mode") or user["ai_mode"] or "focus"
    mood = state_data.get("mood")  # None if skipped

    wait_msg = await message.answer("⏳ Анализирую...")

    try:
        goals = await db.get_active_goals(user["id"])
        history = await db.get_journal_entries(user["id"], limit=10)
        morning_intentions = await db.get_today_intentions(user["id"])
        new_streak, shield_used = _calculate_streak(
            user["last_checkin_date"],
            user["streak"] or 0,
            user.get("streak_shield_used_at"),
        )
        current_xp = (user["xp"] or 0) + 100

        # Enrich checkin text with morning intentions if available
        enriched_text = checkin_text
        if morning_intentions:
            intentions_str = "\n".join(f"- {i}" for i in morning_intentions)
            enriched_text = (
                f"[Утренние намерения: {intentions_str}]\n\n"
                f"{checkin_text}"
            )

        # Common kwargs for support/coach/reflection modes
        common_kwargs = dict(
            checkin_text=enriched_text,
            nickname=user["nickname"] or "",
            last_checkin_date=user["last_checkin_date"],
            goals=goals,
            history=history,
            xp=current_xp,
            streak=new_streak,
        )

        if ai_mode == "support":
            analysis = await analyze_checkin_psychologist(**common_kwargs)
            formatted = format_psychologist_checkin(analysis)
        elif ai_mode == "coach":
            analysis = await analyze_checkin_coach(**common_kwargs)
            formatted = format_coach_checkin(analysis)
        elif ai_mode == "reflection":
            analysis = await analyze_checkin_reflection(**common_kwargs)
            formatted = format_reflection_checkin(analysis)
        else:  # focus (default)
            analysis = await analyze_checkin_manager(
                goals=goals,
                checkin_text=enriched_text,
                history=history,
                xp=current_xp,
                new_streak=new_streak,
            )
            formatted = format_manager_checkin(analysis)

        # Save to DB
        await db.save_checkin(user["id"], date.today(), checkin_text, analysis, mood=mood)
        await db.update_xp_streak(user["id"], new_streak)

        if shield_used:
            await db.use_streak_shield(user["id"])

        # Clear state
        await state.clear()
        await db.update_user_state(tg_id, None)

        # Check achievements
        new_achievements = await check_checkin_achievements(user["id"], new_streak)

        # Send result
        await wait_msg.delete()
        await message.answer(formatted, reply_markup=back_to_menu_kb(), parse_mode="Markdown")

        # Notify about streak shield
        if shield_used:
            await message.answer(
                "🛡️ *Streak Shield активирован!*\n\n"
                "Ты пропустил день, но щит сохранил твой streak!\n"
                f"🔥 Streak: {new_streak} дней\n\n"
                "_Щит можно использовать раз в 7 дней при streak от 3._",
                parse_mode="Markdown",
            )

        # Notify about new achievements
        for ach in new_achievements:
            await message.answer(
                format_achievement_unlocked(ach),
                parse_mode="Markdown",
            )

        # Auto-insights check (non-blocking)
        try:
            insight = await check_and_generate_insight(user["id"])
            if insight:
                await message.answer(format_insight(insight), parse_mode="Markdown")
        except Exception:
            logger.exception("Auto-insight check failed for user %d", tg_id)

    except Exception:
        logger.exception("Check-in LLM error for user %d", tg_id)
        await state.clear()
        await db.update_user_state(tg_id, None)
        await wait_msg.delete()
        await message.answer(
            "⚠️ Сервис временно недоступен. Попробуй через минуту.",
            reply_markup=back_to_menu_kb(),
        )
