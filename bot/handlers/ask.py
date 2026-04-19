"""'Ask Itera' handler — free-form questions about patterns."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import database as db
from bot.fsm.states import IteraStates
from bot.keyboards.main_menu import back_to_menu_kb, cancel_kb
from bot.services.ask_ai import ask_itera

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "menu:ask")
async def cb_ask_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(IteraStates.awaiting_question)
    await callback.message.edit_text(
        "🔮 *Спроси Itera*\n\n"
        "Задай любой вопрос о своих паттернах и прогрессе. Например:\n\n"
        "• _Когда я продуктивнее всего?_\n"
        "• _Какие цели я чаще бросаю?_\n"
        "• _Как изменился мой streak за последний месяц?_\n"
        "• _Что мне мешает двигаться к цели X?_\n\n"
        "Напиши вопрос:",
        reply_markup=cancel_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(IteraStates.awaiting_question)
async def process_question(message: Message, state: FSMContext) -> None:
    question = message.text
    if not question:
        await message.answer("Отправь текстовый вопрос.", reply_markup=cancel_kb())
        return

    tg_id = message.from_user.id
    user = await db.get_or_create_user(tg_id)

    wait_msg = await message.answer("🔮 Анализирую твои данные...")

    try:
        goals = await db.get_all_goals(user["id"])
        history = await db.get_journal_entries(user["id"], limit=30)

        result = await ask_itera(
            question=question,
            goals=goals,
            history=history,
            xp=user["xp"] or 0,
            streak=user["streak"] or 0,
            nickname=user["nickname"] or "",
        )

        answer = result.get("answer", "Не удалось найти ответ.")

        await state.clear()
        await db.update_user_state(tg_id, None)
        await wait_msg.delete()
        await message.answer(answer, reply_markup=back_to_menu_kb(), parse_mode="Markdown")

    except Exception:
        logger.exception("Ask Itera error for user %d", tg_id)
        await state.clear()
        await db.update_user_state(tg_id, None)
        await wait_msg.delete()
        await message.answer(
            "⚠️ Не удалось обработать вопрос. Попробуй позже.",
            reply_markup=back_to_menu_kb(),
        )
