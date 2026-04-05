"""Goals handlers: list, create, view, done, pause, resume, delete."""
from __future__ import annotations

import logging
from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import database as db
from bot.fsm.states import IteraStates
from bot.keyboards.goals_kb import goal_card_kb, goals_list_kb
from bot.keyboards.main_menu import back_to_menu_kb, cancel_kb
from bot.services.goal_ai import generate_goal_plan
from bot.utils.formatters import format_goal_card

router = Router()
logger = logging.getLogger(__name__)


async def _show_goals_list(callback: CallbackQuery, user_id: UUID) -> None:
    goals = await db.get_active_goals(user_id)
    if not goals:
        await callback.message.edit_text(
            "У тебя пока нет активных целей. Создай первую!",
            reply_markup=goals_list_kb([], show_new=True),
        )
    else:
        text = f"🎯 *Твои цели* ({len(goals)}):\n"
        await callback.message.edit_text(
            text,
            reply_markup=goals_list_kb(goals),
            parse_mode="Markdown",
        )
    await callback.answer()


@router.callback_query(F.data == "menu:goals")
async def cb_goals(callback: CallbackQuery, state: FSMContext) -> None:
    user = await db.get_or_create_user(callback.from_user.id)
    await _show_goals_list(callback, user["id"])


@router.message(Command("mygoals"))
async def cmd_mygoals(message: Message) -> None:
    user = await db.get_or_create_user(message.from_user.id)
    goals = await db.get_active_goals(user["id"])
    if not goals:
        await message.answer(
            "У тебя пока нет активных целей.",
            reply_markup=goals_list_kb([], show_new=True),
        )
    else:
        text = f"🎯 *Твои цели* ({len(goals)}):\n"
        await message.answer(text, reply_markup=goals_list_kb(goals), parse_mode="Markdown")


@router.callback_query(F.data == "goals:refresh")
async def cb_goals_refresh(callback: CallbackQuery) -> None:
    user = await db.get_or_create_user(callback.from_user.id)
    await _show_goals_list(callback, user["id"])


@router.callback_query(F.data == "goal:new")
async def cb_new_goal(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(IteraStates.awaiting_goal_text)
    await callback.message.edit_text(
        "✏️ Опиши свою цель одним-двумя предложениями:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(IteraStates.awaiting_goal_text)
async def process_goal_text(message: Message, state: FSMContext) -> None:
    goal_text = message.text
    if not goal_text:
        await message.answer("Отправь текстовое описание цели.", reply_markup=cancel_kb())
        return

    tg_id = message.from_user.id
    user = await db.get_or_create_user(tg_id)
    wait_msg = await message.answer("⏳ Генерирую план...")

    try:
        plan = await generate_goal_plan(goal_text)
        goal = await db.create_goal(user["id"], goal_text, plan)
        await db.add_xp(user["id"], 100)

        await state.clear()
        await db.update_user_state(tg_id, None)

        card_text = format_goal_card(goal)
        await wait_msg.delete()
        await message.answer(
            f"✅ Цель создана! +100 XP\n\n{card_text}",
            reply_markup=goal_card_kb(goal["id"], goal["status"]),
            parse_mode="Markdown",
        )
    except Exception:
        logger.exception("Goal creation error for user %d", tg_id)
        await state.clear()
        await db.update_user_state(tg_id, None)
        await wait_msg.delete()
        await message.answer(
            "⚠️ Не удалось создать цель. Попробуй через минуту.",
            reply_markup=back_to_menu_kb(),
        )


@router.callback_query(F.data.startswith("goal:view:"))
async def cb_view_goal(callback: CallbackQuery) -> None:
    goal_id = UUID(callback.data.split(":")[-1])
    goal = await db.get_goal_by_id(goal_id)
    if not goal:
        await callback.answer("Цель не найдена", show_alert=True)
        return
    card_text = format_goal_card(goal)
    await callback.message.edit_text(
        card_text,
        reply_markup=goal_card_kb(goal["id"], goal["status"]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("goal:done:"))
async def cb_done_goal(callback: CallbackQuery) -> None:
    goal_id = UUID(callback.data.split(":")[-1])
    await db.update_goal_status(goal_id, "completed")
    await callback.message.edit_text(
        "✅ Цель отмечена как выполненная! Поздравляю!",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("goal:pause:"))
async def cb_pause_goal(callback: CallbackQuery) -> None:
    goal_id = UUID(callback.data.split(":")[-1])
    await db.update_goal_status(goal_id, "archived")
    await callback.message.edit_text(
        "⏸ Цель поставлена на паузу.",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("goal:resume:"))
async def cb_resume_goal(callback: CallbackQuery) -> None:
    goal_id = UUID(callback.data.split(":")[-1])
    await db.update_goal_status(goal_id, "active")
    await callback.message.edit_text(
        "▶️ Цель возобновлена!",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("goal:delete:"))
async def cb_delete_goal(callback: CallbackQuery) -> None:
    goal_id = UUID(callback.data.split(":")[-1])
    await db.delete_goal(goal_id)
    await callback.message.edit_text(
        "🗑 Цель удалена.",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()
