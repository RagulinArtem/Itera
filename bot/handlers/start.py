"""Handlers: /start, /help, /menu, /cancel, menu:home, menu:cancel."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import database as db
from bot.keyboards.main_menu import main_menu_kb, main_menu_text

router = Router()
logger = logging.getLogger(__name__)


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
    await _show_menu(message, state)


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
