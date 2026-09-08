"""Shared PDF reporting components for VORA."""

from datetime import UTC, datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, HRFlowable, Paragraph, Spacer, Table, TableStyle

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
        "cover_over_title": ParagraphStyle(
            "OverTitle", fontName="Helvetica-Bold", fontSize=10, textColor=COLORS["primary"], spaceAfter=20
        ),
        "cover_title1": ParagraphStyle(
            "Title1",
            fontName="Helvetica-Bold",
            fontSize=32,
            textColor=COLORS["dark_text"],
            leading=36,
            rightIndent=60 * mm,
        ),
        "cover_title2": ParagraphStyle(
            "Title2",
            fontName="Helvetica-Bold",
            fontSize=32,
            textColor=COLORS["primary"],
            leading=36,
            spaceAfter=20,
        ),
        "cover_subtitle1": ParagraphStyle(
            "SubTitle1",
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=COLORS["dark_text"],
            leading=26,
            rightIndent=60 * mm,
        ),
        "cover_subtitle2": ParagraphStyle(
            "SubTitle2",
            fontName="Helvetica",
            fontSize=12,
            textColor=COLORS["muted_text"],
            spaceBefore=10,
            spaceAfter=30,
            rightIndent=60 * mm,
        ),
        "toc_invisible_section": ParagraphStyle(
            name="TOCEntrySection",
            fontSize=0,
            leading=0,
            spaceBefore=0,
            spaceAfter=0,
            textColor=colors.transparent,
        ),
        "toc_invisible_control": ParagraphStyle(
            name="TOCEntryControl",
            fontSize=0,
            leading=0,
            spaceBefore=0,
            spaceAfter=0,
            textColor=colors.transparent,
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


def format_pdf_date(value: Any, include_time: bool = False) -> str:
    """Safely format a date for PDF reports."""
    if not value:
        return "-"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y %I:%M %p") if include_time else value.strftime("%d/%m/%Y")
    return str(value)


def capitalize_first(text: str) -> str:
    """Capitalizes the first character of a string without modifying the rest."""
    if not text:
        return text
    return text[0].upper() + text[1:]


def add_signatures_block(story: list, signatures: list[dict]):
    """
    Renders a unified signature block.
    If 1 signature, right-aligns it.
    If 2 signatures, left-aligns the first and right-aligns the second.
    If >2, distributes them evenly.
    Signature dict keys: title, name, email, date, comment
    """
    if not signatures:
        return

    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle
    from vora_shared.pdf import COLORS, REPORT_MARGINS, REPORT_PAGESIZE

    usable_width = REPORT_PAGESIZE[0] - (REPORT_MARGINS["leftMargin"] + REPORT_MARGINS["rightMargin"])

    base_title = ParagraphStyle(
        "SigTitle", fontName="Helvetica-Bold", fontSize=9, textColor=COLORS["primary"]
    )
    base_name = ParagraphStyle(
        "SigName", fontName="Helvetica-Bold", fontSize=12, textColor=COLORS["dark_text"], spaceBefore=4
    )
    base_email = ParagraphStyle(
        "SigEmail", fontName="Helvetica", fontSize=10, textColor=COLORS["muted_text"], spaceBefore=2
    )
    base_date = ParagraphStyle(
        "SigDate", fontName="Helvetica", fontSize=10, textColor=COLORS["muted_text"], spaceBefore=2
    )
    base_comment = ParagraphStyle(
        "SigComment", fontName="Helvetica-Oblique", fontSize=9, textColor=COLORS["muted_text"], spaceBefore=6
    )

    cells = []
    for idx, sig in enumerate(signatures):
        # Determine alignment
        align = TA_LEFT
        if len(signatures) == 1:
            align = TA_RIGHT
        elif len(signatures) == 2 and idx == 1:
            align = TA_RIGHT

        t_style = ParagraphStyle(f"T{idx}", parent=base_title, alignment=align)
        n_style = ParagraphStyle(f"N{idx}", parent=base_name, alignment=align)
        e_style = ParagraphStyle(f"E{idx}", parent=base_email, alignment=align)
        d_style = ParagraphStyle(f"D{idx}", parent=base_date, alignment=align)
        c_style = ParagraphStyle(f"C{idx}", parent=base_comment, alignment=align)

        cell = []
        if sig.get("title"):
            cell.append(Paragraph(sig["title"], t_style))
        if sig.get("name"):
            cell.append(Paragraph(sig["name"], n_style))
        if sig.get("email"):
            cell.append(Paragraph(sig["email"], e_style))
        if sig.get("date"):
            cell.append(Paragraph(f"Date: {sig['date']}", d_style))
        if sig.get("comment"):
            cell.append(Paragraph(f'"{sig["comment"]}"', c_style))
        cells.append(cell)

    if len(signatures) == 1:
        row_data = [["", cells[0]]]
        col_widths = [usable_width * 0.5, usable_width * 0.5]
        sig_table = Table(row_data, colWidths=col_widths, hAlign="RIGHT")
    else:
        row_data = [cells]
        col_widths = [usable_width / len(signatures)] * len(signatures)
        sig_table = Table(row_data, colWidths=col_widths, hAlign="LEFT")

    sig_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    story.append(Spacer(1, 10 * mm))
    story.append(KeepTogether(sig_table))


def draw_common_footer(canvas, page_num: int, pagesize: tuple, header_text: str | None = None):
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
        f"Generated by VORA Platform | {format_pdf_date(datetime.now(UTC), include_time=True)}",
    )
    canvas.drawRightString(pagesize[0] - REPORT_MARGINS["rightMargin"], 8 * mm, f"Page {page_num}")
    canvas.restoreState()


def control_separator() -> list:
    """Returns the visual separator used between controls."""
    return [HRFlowable(width="100%", color=COLORS["border"], spaceBefore=8, spaceAfter=12)]


def get_cover_frame(id="cover") -> Frame:
    return Frame(
        20 * mm,
        REPORT_MARGINS["bottomMargin"],
        REPORT_PAGESIZE[0] - (20 * mm + REPORT_MARGINS["rightMargin"]),
        REPORT_PAGESIZE[1] - (REPORT_MARGINS["topMargin"] + REPORT_MARGINS["bottomMargin"]),
        id=id,
    )


def get_cover_callback(left_footer_text: str, right_footer_text: str):
    def cover_callback(canvas, doc):
        canvas.saveState()

        sidebar_width = 8 * mm
        canvas.setFillColor(COLORS["primary"])
        canvas.rect(0, 0, sidebar_width, REPORT_PAGESIZE[1], fill=1, stroke=0)

        watermark_color = colors.HexColor("#ccfbf1")
        canvas.setStrokeColor(watermark_color)
        canvas.setLineWidth(1)
        center_x, center_y = REPORT_PAGESIZE[0] - 60 * mm, REPORT_PAGESIZE[1] + 20 * mm
        for radius in [40 * mm, 50 * mm, 60 * mm, 70 * mm]:
            canvas.circle(center_x, center_y, radius, stroke=1, fill=0)

        canvas.setStrokeColor(colors.HexColor("#99f6e4"))
        canvas.setFillColor(COLORS["primary"])
        canvas.setLineWidth(0.5)

        nodes = [
            (160 * mm, 260 * mm),
            (140 * mm, 230 * mm),
            (180 * mm, 230 * mm),
            (160 * mm, 200 * mm),
            (200 * mm, 200 * mm),
        ]
        edges = [(0, 1), (0, 2), (1, 3), (2, 3), (2, 4), (3, 4)]

        for start, end in edges:
            canvas.line(nodes[start][0], nodes[start][1], nodes[end][0], nodes[end][1])

        for nx, ny in nodes:
            canvas.circle(nx, ny, 2 * mm, fill=1, stroke=0)

        canvas.setStrokeColor(watermark_color)
        canvas.setLineWidth(8)
        canvas.setLineJoin(1)

        shield_path = canvas.beginPath()
        sx, sy = 160 * mm, 90 * mm
        shield_path.moveTo(sx - 30 * mm, sy + 30 * mm)
        shield_path.lineTo(sx + 30 * mm, sy + 30 * mm)
        shield_path.lineTo(sx + 30 * mm, sy - 10 * mm)
        shield_path.lineTo(sx, sy - 40 * mm)
        shield_path.lineTo(sx - 30 * mm, sy - 10 * mm)
        shield_path.close()
        canvas.drawPath(shield_path, stroke=1, fill=0)

        canvas.setLineWidth(6)
        chk_path = canvas.beginPath()
        chk_path.moveTo(sx - 12 * mm, sy)
        chk_path.lineTo(sx - 2 * mm, sy - 10 * mm)
        chk_path.lineTo(sx + 18 * mm, sy + 15 * mm)
        canvas.drawPath(chk_path, stroke=1, fill=0)

        canvas.setStrokeColor(COLORS["border"])
        canvas.setLineWidth(0.5)
        margin = 25 * mm
        canvas.line(margin, 20 * mm, REPORT_PAGESIZE[0] - margin, 20 * mm)

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(COLORS["muted_text"])
        canvas.drawString(margin, 15 * mm, left_footer_text)
        canvas.drawRightString(REPORT_PAGESIZE[0] - margin, 15 * mm, right_footer_text)

        canvas.restoreState()

    return cover_callback


class VoraDocTemplate(BaseDocTemplate):
    """Custom DocTemplate that intercepts flowables to build the Table of Contents."""

    def afterFlowable(self, flowable):
        if flowable.__class__.__name__ == "Paragraph":
            style_name = getattr(flowable.style, "name", "")
            if style_name in ("TOCEntrySection", "TOCEntryControl"):
                level = 0 if style_name == "TOCEntrySection" else 1
                text = flowable.getPlainText()
                key = str(hash(text))
                linked_text = f'<a href="#{key}" color="black">{text}</a>'
                self.notify("TOCEntry", (level, linked_text, self.page))


def build_toc_story(styles: dict) -> list:
    """Returns the flowables needed to render the Table of Contents."""
    from reportlab.platypus import PageBreak
    from reportlab.platypus.tableofcontents import TableOfContents

    story = []
    story.append(Paragraph("Table of Contents", styles["h1"]))
    story.append(Spacer(1, 10))
    toc = TableOfContents()
    toc.dotsMinLevel = 0
    toc.levelStyles = [
        ParagraphStyle(
            fontName="Helvetica-Bold",
            fontSize=10,
            name="TOCHeading1",
            leftIndent=20,
            firstLineIndent=-20,
            spaceBefore=5,
            leading=14,
        ),
        ParagraphStyle(
            fontName="Helvetica",
            fontSize=9,
            name="TOCHeading2",
            leftIndent=40,
            firstLineIndent=-20,
            spaceBefore=0,
            leading=12,
        ),
    ]
    story.append(toc)
    story.append(PageBreak())
    return story


def build_stat_card(label: str, value: Any, styles: dict, width: float = 54 * mm) -> Table:
    """Builds a boxed stat card."""
    table = Table(
        [[Paragraph(str(value), styles["stat_value"])], [Paragraph(label, styles["stat_label"])]],
        colWidths=[width],
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
