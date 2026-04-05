from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def goals_list_kb(goals: list, show_new: bool = True) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for g in goals:
        rows.append([
            InlineKeyboardButton(
                text=f"🎯 {g['goal'][:40]}",
                callback_data=f"goal:view:{g['id']}",
            )
        ])
    bottom: list[InlineKeyboardButton] = []
    if show_new:
        bottom.append(InlineKeyboardButton(text="➕ Новая цель", callback_data="goal:new"))
    bottom.append(InlineKeyboardButton(text="🔄 Обновить", callback_data="goals:refresh"))
    rows.append(bottom)
    rows.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def goal_card_kb(goal_id: UUID, status: str) -> InlineKeyboardMarkup:
    gid = str(goal_id)
    row1: list[InlineKeyboardButton] = [
        InlineKeyboardButton(text="✅ Done", callback_data=f"goal:done:{gid}"),
    ]
    if status == "active":
        row1.append(InlineKeyboardButton(text="⏸ Pause", callback_data=f"goal:pause:{gid}"))
    elif status == "archived":
        row1.append(InlineKeyboardButton(text="▶️ Resume", callback_data=f"goal:resume:{gid}"))

    row1.append(InlineKeyboardButton(text="🗑 Delete", callback_data=f"goal:delete:{gid}"))
    row2 = [InlineKeyboardButton(text="↩️ Назад к списку", callback_data="menu:goals")]
    return InlineKeyboardMarkup(inline_keyboard=[row1, row2])
