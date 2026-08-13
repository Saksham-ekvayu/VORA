"""Shared PDF reporting components for VORA."""

from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Frame, HRFlowable, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import A4

REPORT_PAGESIZE = A4
REPORT_MARGINS = {
    "topMargin": 18 * mm,
    "bottomMargin": 14 * mm,
    "leftMargin": 14 * mm,
    "rightMargin": 14 * mm,
}

COLORS = {
    "primary": colors.HexColor("#0f766e"),
    "primary_light": colors.HexColor("#f0fdfa"),
    "secondary": colors.HexColor("#0d9488"),
    "dark_text": colors.HexColor("#1f2937"),
    "muted_text": colors.HexColor("#4b5563"),
    "light_text": colors.HexColor("#9ca3af"),
    "border": colors.HexColor("#e5e7eb"),
    "card_bg": colors.HexColor("#f8fafc"),
    "green": colors.HexColor("#16a34a"),
    "amber": colors.HexColor("#d97706"),
    "gray": colors.HexColor("#4b5563"),
    "remark_bg": colors.HexColor("#fef9c3"),
    "remark_border": colors.HexColor("#fde047"),
    "remark_text": colors.HexColor("#854d0e"),
    "danger": colors.HexColor("#b91c1c"),
    "warning": colors.HexColor("#d97706"),
    "success": colors.HexColor("#15803d"),
}


def get_shared_styles() -> dict[str, ParagraphStyle]:
    """Return unified ParagraphStyles used across VORA PDF reports."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=32,
            textColor=COLORS["primary"],
            alignment=1,
        ),
        "h1": ParagraphStyle(
            "ReportH1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=COLORS["dark_text"],
            spaceAfter=8,
        ),
        "meta": ParagraphStyle(
            "Meta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            textColor=COLORS["muted_text"],
            spaceAfter=4,
            leading=14,
        ),
        "section_title": ParagraphStyle(
            "SectionTitle",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=COLORS["primary"],
            spaceBefore=14,
            spaceAfter=8,
        ),
        "section_header": ParagraphStyle(
            "SectionHeader",
            fontName="Helvetica-Bold",
            fontSize=10.5,
            textColor=COLORS["primary"],
        ),
        "control_title": ParagraphStyle(
            "ControlTitle",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            textColor=COLORS["dark_text"],
        ),
        "control_weightage": ParagraphStyle(
            "ControlWeightage",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=COLORS["muted_text"],
            alignment=2,
        ),
        "control_desc": ParagraphStyle(
            "ControlDesc",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            textColor=COLORS["muted_text"],
            spaceBefore=3,
            spaceAfter=3,
        ),
        "remark": ParagraphStyle(
            "Remark",
            fontName="Helvetica",
            fontSize=8.5,
            textColor=COLORS["remark_text"],
        ),
        "dp_heading": ParagraphStyle(
            "DpHeading",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=COLORS["dark_text"],
            spaceBefore=4,
            spaceAfter=3,
        ),
        "dp_text": ParagraphStyle(
            "DpText",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=COLORS["muted_text"],
        ),
        "no_controls": ParagraphStyle(
            "NoControls",
            fontName="Helvetica-Oblique",
            fontSize=9,
            textColor=COLORS["muted_text"],
        ),
        "table_cell": ParagraphStyle(
            "TableCell", fontName="Helvetica", fontSize=8.5, textColor=COLORS["dark_text"]
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=COLORS["primary"],
        ),
        "stat_label": ParagraphStyle(
            "StatLabel",
            parent=base["Normal"],
            fontSize=7.5,
            leading=10,
            textColor=COLORS["muted_text"],
            alignment=1,
        ),
        "stat_value": ParagraphStyle(
            "StatValue",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=22,
            textColor=COLORS["primary"],
            alignment=1,
            spaceAfter=6,
        ),
    }


def format_pdf_date(value: Any) -> str:
    """Safely format a date for PDF reports."""
    if not value:
        return "-"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return value
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    return str(value)


def draw_common_footer(canvas, page_num: int, pagesize: tuple, header_text: str = None):
    """Draws a standardized header (page>1) and footer for PDF reports."""
    canvas.saveState()

    if page_num > 1 and header_text:
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(COLORS["light_text"])
        canvas.drawString(REPORT_MARGINS["leftMargin"], pagesize[1] - 12 * mm, header_text)

        canvas.setStrokeColor(COLORS["border"])
        canvas.line(
            REPORT_MARGINS["leftMargin"],
            pagesize[1] - 14 * mm,
            pagesize[0] - REPORT_MARGINS["rightMargin"],
            pagesize[1] - 14 * mm,
        )

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(COLORS["light_text"])
    canvas.drawString(
        REPORT_MARGINS["leftMargin"],
        8 * mm,
        f"Generated by VORA Platform | {format_pdf_date(datetime.now())}",
    )
    canvas.drawRightString(pagesize[0] - REPORT_MARGINS["rightMargin"], 8 * mm, f"Page {page_num}")
    canvas.restoreState()


def control_separator() -> list:
    """Returns the visual separator used between controls."""
    return [
        Spacer(1, 2 * mm),
        HRFlowable(width="100%", color=COLORS["border"], thickness=0.5),
        Spacer(1, 2 * mm),
    ]


def build_stat_card(label: str, value: Any, styles: dict) -> Table:
    """Builds a boxed stat card."""
    table = Table(
        [[Paragraph(str(value), styles["stat_value"])], [Paragraph(label, styles["stat_label"])]],
        colWidths=[54 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLORS["card_bg"]),
                ("BOX", (0, 0), (-1, -1), 0.75, COLORS["border"]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table

def get_shared_frame(id: str = "normal") -> Frame:
    """Returns a unified ReportLab Frame respecting the shared margins."""
    return Frame(
        REPORT_MARGINS["leftMargin"],
        REPORT_MARGINS["bottomMargin"],
        REPORT_PAGESIZE[0] - (REPORT_MARGINS["leftMargin"] + REPORT_MARGINS["rightMargin"]),
        REPORT_PAGESIZE[1] - (REPORT_MARGINS["topMargin"] + REPORT_MARGINS["bottomMargin"]),
        id=id,
    )
