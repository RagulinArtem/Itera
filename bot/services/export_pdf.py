"""Generate PDF report for a given period."""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from fpdf import FPDF


@dataclass
class ExportData:
    nickname: str
    period_label: str
    date_from: date
    date_to: date
    xp: int
    streak: int
    level_name: str
    checkins: list[dict[str, Any]] = field(default_factory=list)
    goals: list[dict[str, Any]] = field(default_factory=list)
    achievements_unlocked: int = 0
    achievements_total: int = 0


class IteraPDF(FPDF):
    """Custom PDF with Itera branding."""

    def __init__(self):
        super().__init__()
        self._add_fonts()

    def _add_fonts(self):
        """Add DejaVu fonts for Cyrillic support."""
        paths = [
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVu", ""),
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVu", "B"),
        ]
        for path, family, style in paths:
            try:
                self.add_font(family, style, path, uni=True)
            except Exception:
                pass

    def _use_font(self, style: str = "", size: int = 11):
        try:
            self.set_font("DejaVu", style, size)
        except Exception:
            self.set_font("Helvetica", style, size)

    def header(self):
        self._use_font("B", 18)
        self.set_text_color(99, 102, 241)
        self.cell(0, 10, "ITERA", align="L")
        self.ln(6)
        self.set_draw_color(99, 102, 241)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self._use_font("", 8)
        self.set_text_color(160, 160, 160)
        self.cell(0, 10, f"itera-diary.online | @Itera_diary_bot | стр. {self.page_no()}", align="C")

    def section_title(self, title: str):
        self._use_font("B", 13)
        self.set_text_color(60, 60, 80)
        self.ln(4)
        self.cell(0, 8, title)
        self.ln(8)

    def body_text(self, text: str):
        self._use_font("", 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 6, text)
        self.ln(2)

    def stat_row(self, label: str, value: str):
        self._use_font("", 10)
        self.set_text_color(100, 100, 120)
        self.cell(50, 7, label)
        self._use_font("B", 10)
        self.set_text_color(40, 40, 40)
        self.cell(0, 7, value)
        self.ln(7)


def generate_pdf(data: ExportData) -> bytes:
    """Generate a PDF report, return bytes."""
    pdf = IteraPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Title
    pdf._use_font("B", 16)
    pdf.set_text_color(30, 30, 40)
    pdf.cell(0, 10, f"Отчёт: {data.period_label}", ln=True)
    pdf._use_font("", 10)
    pdf.set_text_color(120, 120, 140)
    pdf.cell(0, 6, f"{data.date_from} — {data.date_to}", ln=True)
    pdf.ln(6)

    # Stats summary
    pdf.section_title("Статистика")
    pdf.stat_row("Пользователь:", data.nickname or "—")
    pdf.stat_row("Уровень:", data.level_name)
    pdf.stat_row("XP:", str(data.xp))
    pdf.stat_row("Streak:", f"{data.streak} дн.")
    pdf.stat_row("Ачивки:", f"{data.achievements_unlocked}/{data.achievements_total}")
    pdf.stat_row("Чекинов за период:", str(len(data.checkins)))
    pdf.ln(4)

    # Goals
    if data.goals:
        pdf.section_title("Цели")
        for g in data.goals:
            status_icons = {"active": "[активна]", "completed": "[завершена]", "archived": "[архив]"}
            status = status_icons.get(g.get("status", ""), g.get("status", ""))
            pdf._use_font("B", 10)
            pdf.set_text_color(40, 40, 40)
            pdf.multi_cell(0, 6, f"• {g.get('goal', '')} {status}")
            pdf.ln(2)

    # Checkins
    if data.checkins:
        pdf.section_title(f"Записи ({len(data.checkins)})")
        for entry in data.checkins:
            d = entry.get("entry_date", "")
            text = (entry.get("checkin_text") or "")[:300]

            pdf._use_font("B", 10)
            pdf.set_text_color(99, 102, 241)
            pdf.cell(0, 7, str(d), ln=True)

            pdf._use_font("", 9)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(0, 5, text)
            pdf.ln(4)

            # Page break guard
            if pdf.get_y() > 260:
                pdf.add_page()

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
