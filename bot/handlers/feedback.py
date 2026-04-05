"""Feedback handler."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import database as db
from bot.fsm.states import IteraStates
from bot.keyboards.main_menu import back_to_menu_kb, cancel_kb

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "menu:feedback")
async def cb_feedback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(IteraStates.awaiting_feedback)
    await callback.message.edit_text(
        "🗣 Напиши свой фидбек, предложение или жалобу:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(IteraStates.awaiting_feedback)
async def process_feedback(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Отправь текстовое сообщение.", reply_markup=cancel_kb())
        return

    # Log feedback (can be extended to save in DB or send to admin)
    logger.info(
        "Feedback from user %d (@%s): %s",
        message.from_user.id,
        message.from_user.username or "no_username",
        text,
    )

    await state.clear()
    await db.update_user_state(message.from_user.id, None)
    await message.answer(
        "✅ Спасибо за фидбек! Мы обязательно учтём.",
        reply_markup=back_to_menu_kb(),
    )
