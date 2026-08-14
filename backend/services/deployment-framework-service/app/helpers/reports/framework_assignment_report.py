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
from vora_shared.pdf import (
    COLORS,
    REPORT_MARGINS,
    REPORT_PAGESIZE,
    build_stat_card,
    control_separator,
    draw_common_footer,
    format_pdf_date,
    get_shared_styles,
)

_styles_dict = get_shared_styles()


def _display_user(user: Any) -> str:
    if not user:
        return "System / Unknown"
    if hasattr(user, "name") and user.name:
        return user.name
    if hasattr(user, "email") and user.email:
        return user.email
    if isinstance(user, dict):
        if user.get("name"):
            return user["name"]
        if user.get("email"):
            return user["email"]
    return str(user)


def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _add_header_section(story: list[Any], assignment: Any, file_version: Any, customer: Any):
    story.append(Paragraph("<u>Assigned Framework Report</u>", _styles_dict["title"]))
    story.append(Spacer(1, 10))

    fw_name = assignment.frameworkName or assignment.frameworkCode
    story.append(Paragraph(fw_name, _styles_dict["h1"]))
    story.append(
        Paragraph(
            f"Version: {assignment.frameworkVersion or '-'} &nbsp;|&nbsp; Current: v{file_version.fileVersion}",
            _styles_dict["meta"],
        )
    )
    story.append(
        Paragraph(
            f"Created On: {format_pdf_date(assignment.createdAt)} &nbsp;|&nbsp; "
            f"Updated On: {format_pdf_date(assignment.updatedAt)}",
            _styles_dict["meta"],
        )
    )
    story.append(
        Paragraph(
            f"Customer: {_display_user(customer)} &nbsp;|&nbsp; "
            f"Assigned By: {_display_user(_safe_get(assignment.assignment, 'assignedBy'))} "
            f"on {format_pdf_date(_safe_get(assignment.assignment, 'assignedAt'))}",
            _styles_dict["meta"],
        )
    )
    story.append(
        Paragraph(
            f"Assignment Status: {str(assignment.status or 'assigned').upper()} &nbsp;|&nbsp; "
            f"Finalization: {'FINALIZED' if _safe_get(assignment.finalization, 'isFinalized') else 'PENDING'}",
            _styles_dict["meta"],
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
    stat_cards = [build_stat_card(label, value, _styles_dict) for label, value in stats]
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
    title_style = _styles_dict["control_title"]
    label_style = ParagraphStyle(
        "AFRCtrlLabel", fontName="Helvetica", fontSize=8, textColor=accent, alignment=2
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
            _styles_dict["dp_heading"],
        )
    )
    for idx, point in enumerate(control.deployment_points):
        remark_part = f" | Remark: {point.remark}" if point.remark else ""
        story.append(Paragraph(f"{idx + 1}. {point.name}{remark_part}", _styles_dict["dp_text"]))


def _add_single_control(story: list[Any], control: Any, doc_width: float):
    label_text, accent = _get_control_label_info(control)
    _add_control_header(story, control, doc_width, label_text, accent)

    if control.description:
        story.append(Paragraph(control.description, _styles_dict["control_desc"]))

    _add_control_deployment_points(story, control)

    story.extend(control_separator())


def _add_controls_section(story: list[Any], sections: list[Any], doc_width: float):
    story.append(PageBreak())
    story.append(Paragraph("Controls", _styles_dict["section_title"]))
    story.append(Spacer(1, 4 * mm))

    for section in sections:
        section_title = f"{section.id or ''} {section.name or ''}".strip()
        section_bar = Table(
            [[Paragraph(section_title, _styles_dict["section_title"])]], colWidths=[doc_width]
        )
        section_bar.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), COLORS["primary_light"]),
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
        pagesize=REPORT_PAGESIZE,
        **REPORT_MARGINS,
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
        header_fw_name = assignment.frameworkName or assignment.frameworkCode or "Framework"
        header_text = f"{str(header_fw_name).upper()} - VERSION {assignment.frameworkVersion or '-'}"
        draw_common_footer(canvas, doc_.page, REPORT_PAGESIZE, header_text)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
