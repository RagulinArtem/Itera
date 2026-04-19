"""Handlers: /start, /help, /menu, /cancel, menu:home, menu:cancel, onboarding."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot import database as db
from bot.fsm.states import IteraStates
from bot.keyboards.main_menu import main_menu_kb, main_menu_text, cancel_kb

router = Router()
logger = logging.getLogger(__name__)

# ── Onboarding screens ─────────────────────

ONBOARDING = [
    {
        "text": (
            "👋 *Привет! Я — Itera*\n\n"
            "AI-дневник для тех, кто хочет расти каждый день.\n\n"
            "📝 Делай ежедневные чекины\n"
            "🎯 Ставь цели и отслеживай прогресс\n"
            "🧠 Получай AI-аналитику своих паттернов\n"
            "🏅 Зарабатывай XP и открывай ачивки\n\n"
            "Давай начнём!"
        ),
        "button": "Поехали! →",
    },
    {
        "text": (
            "✏️ *Как тебя зовут?*\n\n"
            "Напиши своё имя или никнейм — "
            "так AI будет обращаться к тебе лично."
        ),
        "input": True,
    },
    {
        "text": (
            "🎯 *Отлично, {name}!*\n\n"
            "Теперь опиши свою первую цель.\n"
            "Например: _выучить Python_, _бегать 3 раза в неделю_, "
            "_запустить свой проект_.\n\n"
            "Напиши цель:"
        ),
        "input": True,
    },
]


def _onboarding_kb(step: int) -> InlineKeyboardMarkup:
    btn_text = ONBOARDING[step].get("button", "Далее →")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_text, callback_data=f"onboard:{step + 1}")],
    ])


async def _show_menu(target: Message | CallbackQuery, state: FSMContext) -> None:
    """Send or edit the main menu."""
    tg_id = target.from_user.id
    user = await db.get_or_create_user(tg_id)
    await state.clear()
    await db.update_user_state(tg_id, None)

    text = main_menu_text(
        nickname=user["nickname"],
        ai_mode=user["ai_mode"],
        xp=user["xp"] or 0,
        streak=user["streak"] or 0,
    )
    kb = main_menu_kb()

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=kb)
        await target.answer()
    else:
        await target.answer(text, reply_markup=kb)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    tg_id = message.from_user.id
    user = await db.get_or_create_user(tg_id)

    # If user has no nickname → new user, start onboarding
    if not user["nickname"]:
        await message.answer(
            ONBOARDING[0]["text"],
            reply_markup=_onboarding_kb(0),
            parse_mode="Markdown",
        )
        return

    await _show_menu(message, state)


@router.callback_query(F.data == "onboard:1")
async def cb_onboard_name(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 1: ask for name."""
    await state.set_state(IteraStates.onboarding_name)
    await callback.message.edit_text(
        ONBOARDING[1]["text"],
        reply_markup=cancel_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(IteraStates.onboarding_name)
async def process_onboard_name(message: Message, state: FSMContext) -> None:
    """Save name, ask for first goal."""
    name = (message.text or "").strip()
    if not name:
        await message.answer("Напиши своё имя текстом.", reply_markup=cancel_kb())
        return

    await db.update_nickname(message.from_user.id, name)
    await state.update_data(onboard_name=name)
    await state.set_state(IteraStates.onboarding_goal)

    text = ONBOARDING[2]["text"].format(name=name)
    await message.answer(text, reply_markup=cancel_kb(), parse_mode="Markdown")


@router.message(IteraStates.onboarding_goal)
async def process_onboard_goal(message: Message, state: FSMContext) -> None:
    """Save first goal, finish onboarding → show menu."""
    goal_text = (message.text or "").strip()
    if not goal_text:
        await message.answer("Напиши цель текстом.", reply_markup=cancel_kb())
        return

    tg_id = message.from_user.id
    user = await db.get_or_create_user(tg_id)

    # Create goal (simple, without AI plan for speed)
    await db.create_goal(user["id"], goal_text, plan={"items": []})

    state_data = await state.get_data()
    name = state_data.get("onboard_name", "")

    await state.clear()
    await db.update_user_state(tg_id, None)

    await message.answer(
        f"🎉 *Добро пожаловать, {name}!*\n\n"
        f"Цель создана: _{goal_text}_\n\n"
        f"Теперь сделай первый чекин — расскажи, как прошёл твой день!",
        parse_mode="Markdown",
        reply_markup=main_menu_kb(),
    )



@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await _show_menu(message, state)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    text = (
        "ℹ️ *Itera — AI-дневник развития*\n\n"
        "/start — запустить бота\n"
        "/menu — главное меню\n"
        "/mygoals — список целей\n"
        "/cancel — отменить текущее действие\n\n"
        "Используй кнопки меню для навигации."
    )
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await db.update_user_state(message.from_user.id, None)
    await _show_menu(message, state)


@router.callback_query(F.data == "menu:home")
async def cb_home(callback: CallbackQuery, state: FSMContext) -> None:
    await _show_menu(callback, state)


@router.callback_query(F.data == "menu:cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await _show_menu(callback, state)
