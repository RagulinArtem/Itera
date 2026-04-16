"""Generate a shareable progress card image."""
from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont


@dataclass
class CardData:
    nickname: str
    level_name: str
    level_icon: str
    xp: int
    streak: int
    achievements_unlocked: int
    achievements_total: int
    goals_completed: int
    checkins_total: int


# ── Colors ──────────────────────────────────

BG_TOP = (30, 32, 44)       # dark blue-gray
BG_BOTTOM = (18, 18, 28)    # near black
ACCENT = (99, 102, 241)     # indigo
ACCENT_LIGHT = (139, 142, 255)
WHITE = (255, 255, 255)
GRAY = (156, 163, 175)
GOLD = (251, 191, 36)
GREEN = (52, 211, 153)

W, H = 800, 480


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a font, falling back to default if not available."""
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _gradient(img: Image.Image) -> None:
    """Draw a vertical gradient background."""
    draw = ImageDraw.Draw(img)
    for y in range(H):
        ratio = y / H
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * ratio)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * ratio)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * ratio)
        draw.line([(0, y), (W, y)], fill=(r, g, b))


def _rounded_rect(draw: ImageDraw.Draw, xy: tuple, fill: tuple, radius: int = 16) -> None:
    """Draw a rounded rectangle."""
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def generate_card(data: CardData) -> bytes:
    """Generate progress card image, return PNG bytes."""
    img = Image.new("RGB", (W, H))
    _gradient(img)
    draw = ImageDraw.Draw(img)

    font_lg = _load_font(36, bold=True)
    font_md = _load_font(22, bold=True)
    font_sm = _load_font(18)
    font_xs = _load_font(14)
    font_num = _load_font(32, bold=True)

    # ── Header area ─────────────────────────
    # Brand
    draw.text((32, 24), "ITERA", fill=ACCENT_LIGHT, font=font_md)

    # Nickname + level
    name = data.nickname or "Пользователь"
    draw.text((32, 68), name, fill=WHITE, font=font_lg)

    # Level badge
    level_text = f"{data.level_icon}  {data.level_name}"
    draw.text((32, 116), level_text, fill=GOLD, font=font_md)

    # ── Stats cards row ─────────────────────
    card_y = 170
    card_h = 130
    card_w = 170
    gap = 18
    start_x = 32

    stats = [
        ("XP", str(data.xp), "Опыт", ACCENT),
        ("STREAK", f"{data.streak}", "дней подряд", GREEN),
        ("АЧИВКИ", f"{data.achievements_unlocked}/{data.achievements_total}", "собрано", GOLD),
        ("ЦЕЛИ", str(data.goals_completed), "завершено", ACCENT_LIGHT),
    ]

    for i, (label, value, sub, color) in enumerate(stats):
        x = start_x + i * (card_w + gap)
        _rounded_rect(draw, (x, card_y, x + card_w, card_y + card_h),
                       fill=(40, 42, 56), radius=14)
        # Top label
        draw.text((x + 16, card_y + 12), label, fill=GRAY, font=font_xs)
        # Value
        draw.text((x + 16, card_y + 36), value, fill=color, font=font_num)
        # Sub label
        draw.text((x + 16, card_y + 80), sub, fill=GRAY, font=font_sm)

    # ── Checkins bar ────────────────────────
    bar_y = card_y + card_h + 28
    _rounded_rect(draw, (32, bar_y, W - 32, bar_y + 70),
                   fill=(40, 42, 56), radius=14)
    draw.text((52, bar_y + 12), f"Всего чекинов: {data.checkins_total}",
              fill=WHITE, font=font_md)
    draw.text((52, bar_y + 42), "Каждый день — это прогресс",
              fill=GRAY, font=font_sm)

    # ── Footer ──────────────────────────────
    footer_y = H - 44
    draw.text((32, footer_y), "@Itera_diary_bot", fill=GRAY, font=font_sm)
    draw.text((W - 200, footer_y), "itera-diary.online", fill=GRAY, font=font_sm)

    # ── Decorative accent line ──────────────
    draw.rectangle([(0, 0), (W, 4)], fill=ACCENT)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
