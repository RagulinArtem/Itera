from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from bot.config import settings
from bot.services.achievements import get_level


def _webapp_url() -> str:
    """Build Mini App URL based on environment."""
    if settings.webhook_domain:
        return f"{settings.webhook_domain}/app/"
    return f"https://5.129.243.18:{settings.port}/app/"


def main_menu_kb() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="✅ Check-in", callback_data="menu:checkin"),
            InlineKeyboardButton(text="🎯 Цели", callback_data="menu:goals"),
        ],
        [
            InlineKeyboardButton(text="📊 Отчёты", callback_data="menu:reports"),
            InlineKeyboardButton(text="🔮 Спроси", callback_data="menu:ask"),
        ],
        [
            InlineKeyboardButton(text="🏅 Ачивки", callback_data="menu:achievements"),
            InlineKeyboardButton(text="👤 Профиль", callback_data="menu:profile"),
        ],
        [
            InlineKeyboardButton(text="🧠 Режим", callback_data="menu:mode"),
            InlineKeyboardButton(text="📤 Поделиться", callback_data="menu:share"),
        ],
        [
            InlineKeyboardButton(text="📄 Экспорт PDF", callback_data="menu:export"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings"),
        ],
        [
            InlineKeyboardButton(text="🗣 Фидбек", callback_data="menu:feedback"),
        ],
    ]
    # Add Mini App button if domain is configured
    if settings.webhook_domain:
        rows.insert(0, [
            InlineKeyboardButton(
                text="📱 Дашборд",
                web_app=WebAppInfo(url=_webapp_url()),
            ),
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Отмена", callback_data="menu:cancel")],
    ])


def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:home")],
    ])


MODE_LABELS = {
    "focus": "🎯 Фокус (результат и план)",
    "support": "💛 Поддержка (мягкий режим)",
    "coach": "🚀 Коуч (вызов и рост)",
    "reflection": "🪞 Рефлексия (вопросы себе)",
}


def main_menu_text(nickname: str, ai_mode: str, xp: int, streak: int) -> str:
    mode_label = MODE_LABELS.get(ai_mode, ai_mode)
    display_name = nickname or "—"
    level = get_level(xp)
    return (
        f"🏠 Itera — Home\n\n"
        f"👤 {display_name}  {level.icon} {level.name}\n"
        f"🧠 Режим: {mode_label}\n\n"
        f"🏅 XP: {xp}  🔥 Streak: {streak} дн.\n\n"
        f"Выбирай действие кнопками ниже 👇"
    )
