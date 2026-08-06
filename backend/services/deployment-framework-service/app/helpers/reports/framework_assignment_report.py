"""Port of deployment-framework-service-main/src/helpers/framework-assignment-report.helper.js.

Rebuilt with reportlab/platypus (flowable-based layout) instead of pdfkit's
manual absolute positioning; content and structure are preserved.
"""

from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

COLORS = {
    "primary": colors.HexColor("#0f766e"),
    "primaryLight": colors.HexColor("#f0fdfa"),
    "text": colors.HexColor("#1f2937"),
    "muted": colors.HexColor("#4b5563"),
    "light": colors.HexColor("#9ca3af"),
    "border": colors.HexColor("#e5e7eb"),
    "card": colors.HexColor("#f8fafc"),
    "success": colors.HexColor("#15803d"),
    "danger": colors.HexColor("#b91c1c"),
    "warning": colors.HexColor("#d97706"),
}

_styles = getSampleStyleSheet()
_STYLE_TITLE = ParagraphStyle("AFRTitle", parent=_styles["Title"], textColor=COLORS["primary"], fontSize=18)
_STYLE_H1 = ParagraphStyle("AFRH1", parent=_styles["Heading1"], textColor=COLORS["text"], fontSize=20)
_STYLE_MUTED = ParagraphStyle("AFRMuted", parent=_styles["Normal"], textColor=COLORS["muted"], fontSize=10)
_STYLE_SECTION = ParagraphStyle(
    "AFRSection", parent=_styles["Heading2"], textColor=COLORS["primary"], fontSize=11
)
_STYLE_CONTROL_TITLE = ParagraphStyle(
    "AFRControlTitle",
    parent=_styles["Normal"],
    textColor=COLORS["text"],
    fontSize=9.5,
    fontName="Helvetica-Bold",
)
_STYLE_DESC = ParagraphStyle("AFRDesc", parent=_styles["Normal"], textColor=COLORS["muted"], fontSize=8.5)
_STYLE_DP = ParagraphStyle("AFRDp", parent=_styles["Normal"], textColor=COLORS["muted"], fontSize=8)
_STYLE_STAT_LABEL = ParagraphStyle(
    "AFRStatLabel", parent=_styles["Normal"], fontSize=7.5, textColor=COLORS["muted"], alignment=1
)
_STYLE_STAT_VALUE = ParagraphStyle(
    "AFRStatValue",
    parent=_styles["Normal"],
    fontSize=17,
    textColor=COLORS["primary"],
    alignment=1,
    fontName="Helvetica-Bold",
)


def _display_date(value: Any) -> str:
    if not value:
        return "-"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    return value.strftime("%d %b %Y")


def _display_user(user: Any) -> str:
    if not user:
        return "System / Unknown"
    if hasattr(user, "name") and user.name:
        return user.name
    if hasattr(user, "email") and user.email:
        return user.email
    return str(user)


def _stat_card(label: str, value: Any) -> Table:
    table = Table(
        [[Paragraph(str(value), _STYLE_STAT_VALUE)], [Paragraph(label, _STYLE_STAT_LABEL)]],
        colWidths=[54 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLORS["card"]),
                ("BOX", (0, 0), (-1, -1), 0.75, COLORS["border"]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _add_header_section(story: list[Any], assignment: Any, file_version: Any, customer: Any):
    story.append(Paragraph("Assigned Framework Report", _STYLE_TITLE))
    story.append(HRFlowable(width="100%", color=COLORS["border"], thickness=1, spaceAfter=8))

    fw_name = assignment.frameworkName or assignment.frameworkCode
    story.append(Paragraph(fw_name, _STYLE_H1))
    story.append(
        Paragraph(
            f"Version: {assignment.frameworkVersion or '-'} &nbsp;|&nbsp; Current: v{file_version.fileVersion}",
            _STYLE_MUTED,
        )
    )
    story.append(
        Paragraph(
            f"Created On: {_display_date(assignment.createdAt)} &nbsp;|&nbsp; "
            f"Updated On: {_display_date(assignment.updatedAt)}",
            _STYLE_MUTED,
        )
    )
    story.append(
        Paragraph(
            f"Customer: {_display_user(customer)} &nbsp;|&nbsp; "
            f"Assigned By: {_display_user(assignment.assignment.assignedBy if assignment.assignment else None)} "
            f"on {_display_date(assignment.assignment.assignedAt if assignment.assignment else None)}",
            _STYLE_MUTED,
        )
    )
    story.append(
        Paragraph(
            f"Assignment Status: {str(assignment.status or 'assigned').upper()} &nbsp;|&nbsp; "
            f"Finalization: {'FINALIZED' if assignment.finalization and assignment.finalization.isFinalized else 'PENDING'}",
            _STYLE_MUTED,
        )
    )
    story.append(Spacer(1, 10 * mm))


def _add_stats_section(
    story: list[Any],
    sections: list[Any],
    applicable_controls: list[Any],
    controls: list[Any],
    deployment_points: list[Any],
    org_specific_controls: int,
    avg_customer_weightage: float,
):
    stats = [
        ("SECTIONS", len(sections)),
        ("APPLICABLE CONTROLS", len(applicable_controls)),
        ("NOT APPLICABLE", len(controls) - len(applicable_controls)),
        ("DEPLOYMENT POINTS", len(deployment_points)),
        ("ORG SPECIFIC CONTROLS", org_specific_controls),
        ("AVG CUSTOMER WEIGHT", f"{avg_customer_weightage}/10"),
    ]
    stat_cards = [_stat_card(label, value) for label, value in stats]
    rows = [stat_cards[i : i + 3] for i in range(0, len(stat_cards), 3)]
    stats_table = Table(rows, hAlign="LEFT", spaceBefore=0, spaceAfter=0)
    stats_table.setStyle(
        TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)])
    )
    story.append(stats_table)


def _get_control_label_info(control: Any) -> tuple[str, Any]:
    applicable = not control.customization or control.customization.is_applicable is not False
    is_org_specific = bool(
        control.customization and str(control.customization.source or "").lower() == "custom"
    )
    fw_weight = (
        control.customization.weightage.framework_weightage
        if control.customization and control.customization.weightage
        else 0
    )
    cust_weight = (
        control.customization.weightage.customer_weightage
        if control.customization and control.customization.weightage
        else 0
    )

    if not applicable:
        return "NOT APPLICABLE", COLORS["danger"]
    if is_org_specific:
        return "ORG SPECIFIC CONTROL", COLORS["warning"]
    return f"FW {fw_weight}/10 | Customer {cust_weight}/10", COLORS["primary"]


def _add_control_header(story: list[Any], control: Any, doc_width: float, label_text: str, accent: Any):
    title_style = ParagraphStyle("AFRCtrlTitleAccent", parent=_STYLE_CONTROL_TITLE)
    label_style = ParagraphStyle(
        "AFRCtrlLabel", parent=_styles["Normal"], fontSize=8, textColor=accent, alignment=2
    )

    header_row = Table(
        [
            [
                Paragraph(f"[{control.id}] {control.name}", title_style),
                Paragraph(label_text, label_style),
            ]
        ],
        colWidths=[doc_width * 0.65, doc_width * 0.35],
    )
    header_row.setStyle(
        TableStyle(
            [
                ("LINEBEFORE", (0, 0), (0, 0), 3, accent),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 6),
            ]
        )
    )
    story.append(header_row)


def _add_control_deployment_points(story: list[Any], control: Any):
    if not control.deployment_points:
        return
    story.append(
        Paragraph(
            "Deployment Points",
            ParagraphStyle("AFRDpHeader", parent=_styles["Normal"], fontSize=8, fontName="Helvetica-Bold"),
        )
    )
    for idx, point in enumerate(control.deployment_points):
        remark_part = f" | Remark: {point.remark}" if point.remark else ""
        story.append(Paragraph(f"{idx + 1}. {point.name}{remark_part}", _STYLE_DP))


def _add_single_control(story: list[Any], control: Any, doc_width: float):
    label_text, accent = _get_control_label_info(control)
    _add_control_header(story, control, doc_width, label_text, accent)

    if control.description:
        story.append(Paragraph(control.description, _STYLE_DESC))

    _add_control_deployment_points(story, control)

    story.append(Spacer(1, 2 * mm))
    story.append(HRFlowable(width="100%", color=COLORS["border"], thickness=0.5))
    story.append(Spacer(1, 2 * mm))


def _add_controls_section(story: list[Any], sections: list[Any], doc_width: float):
    story.append(PageBreak())
    story.append(Paragraph("Controls", _STYLE_SECTION))
    story.append(Spacer(1, 4 * mm))

    for section in sections:
        section_title = f"{section.id or ''} {section.name or ''}".strip()
        section_bar = Table([[Paragraph(section_title, _STYLE_SECTION)]], colWidths=[doc_width])
        section_bar.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), COLORS["primaryLight"]),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(section_bar)
        story.append(Spacer(1, 2 * mm))

        for control in section.controls or []:
            _add_single_control(story, control, doc_width)


def generate_framework_assignment_report_pdf(assignment: Any, file_version: Any, customer: Any) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=14 * mm,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        title="Assigned Framework Report",
    )

    sections = file_version.aiExtraction or []
    controls = [c for s in sections for c in (s.controls or [])]
    applicable_controls = [
        c for c in controls if not c.customization or c.customization.is_applicable is not False
    ]
    deployment_points = [dp for c in applicable_controls for dp in (c.deployment_points or [])]
    org_specific_controls = sum(
        1 for c in controls if c.customization and str(c.customization.source or "").lower() == "custom"
    )
    avg_customer_weightage = (
        round(
            sum(
                (
                    c.customization.weightage.customer_weightage
                    if c.customization and c.customization.weightage
                    else 0
                )
                for c in applicable_controls
            )
            / len(applicable_controls),
            1,
        )
        if applicable_controls
        else 0.0
    )

    story: list[Any] = []

    _add_header_section(story, assignment, file_version, customer)
    _add_stats_section(
        story,
        sections,
        applicable_controls,
        controls,
        deployment_points,
        org_specific_controls,
        avg_customer_weightage,
    )
    _add_controls_section(story, sections, doc.width)

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(COLORS["light"])
        canvas.drawString(
            14 * mm, 8 * mm, f"Generated by VORA Platform | {_display_date(datetime.now(timezone.utc))}"
        )
        canvas.drawRightString(doc_.pagesize[0] - 14 * mm, 8 * mm, f"Page {doc_.page}")
        if doc_.page > 1:
            canvas.setFont("Helvetica-Bold", 8)
            header_fw_name = assignment.frameworkName or assignment.frameworkCode or "Framework"
            canvas.drawString(
                14 * mm,
                doc_.pagesize[1] - 12 * mm,
                f"{str(header_fw_name).upper()} - VERSION {assignment.frameworkVersion or '-'}",
            )
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
