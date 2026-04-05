from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def reports_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 3 дня", callback_data="report:3"),
            InlineKeyboardButton(text="📊 7 дней", callback_data="report:7"),
            InlineKeyboardButton(text="📈 30 дней", callback_data="report:30"),
        ],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="menu:home")],
    ])
