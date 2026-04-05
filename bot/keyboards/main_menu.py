from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Check-in", callback_data="menu:checkin"),
            InlineKeyboardButton(text="🎯 Цели", callback_data="menu:goals"),
        ],
        [
            InlineKeyboardButton(text="📊 Отчёты", callback_data="menu:reports"),
            InlineKeyboardButton(text="🧠 Режим", callback_data="menu:mode"),
        ],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="menu:profile"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings"),
        ],
        [
            InlineKeyboardButton(text="🗣 Фидбек", callback_data="menu:feedback"),
        ],
    ])


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Отмена", callback_data="menu:cancel")],
    ])


def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:home")],
    ])


MODE_LABELS = {
    "manager": "Менеджер 📌 (результат)",
    "psychologist": "Психолог 🧠 (мягкий режим)",
}


def main_menu_text(nickname: str, ai_mode: str, xp: int, streak: int) -> str:
    mode_label = MODE_LABELS.get(ai_mode, ai_mode)
    display_name = nickname or "—"
    return (
        f"🏠 Itera — Home\n\n"
        f"👤 Профиль: {display_name}\n"
        f"🧠 Режим: {mode_label}\n\n"
        f"🏅 XP: {xp}\n"
        f"🔥 Streak: {streak} дн.\n\n"
        f"Выбирай действие кнопками ниже 👇"
    )
