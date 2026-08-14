"""Port of framework-report.helper.js using reportlab.

Generates a professional framework report PDF, built with the reportlab
Platypus flowable API (Paragraph/Table/Spacer) instead of pdfkit's
manual/absolute positioning, but with equivalent content and sections:
header banner, summary stat cards, file information table, and a full
sections/controls breakdown with deployment points.
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
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
    get_shared_frame,
    get_shared_styles,
)


def _stat_status_color(ai_status: str) -> colors.Color:
    if ai_status in ("completed", "approved", "extracted"):
        return COLORS["green"]
    if ai_status in ("pending", "processing"):
        return COLORS["amber"]
    return COLORS["gray"]


def _build_stats_table(sections: list[dict], styles: dict) -> Table:
    total_sections = len(sections)
    total_controls = sum(len(s.get("controls") or []) for s in sections)
    all_controls = [c for s in sections for c in (s.get("controls") or [])]
    total_dps = sum(len(c.get("deployment_points") or []) for c in all_controls)
    avg_weightage = (
        round(sum((c.get("weightage") or 0) for c in all_controls) / len(all_controls), 1)
        if all_controls
        else 0
    )

    stats = [
        ("TOTAL SECTIONS", str(total_sections)),
        ("TOTAL CONTROLS", str(total_controls)),
        ("DEPLOYMENT POINTS", str(total_dps)),
        ("AVG PRIORITY SCORE", f"{avg_weightage}/10"),
    ]

    stat_cards = [build_stat_card(label, val, styles) for label, val in stats]
    rows = [stat_cards[i : i + 4] for i in range(0, len(stat_cards), 4)]
    stats_table = Table(rows, hAlign="LEFT", spaceBefore=0, spaceAfter=0)
    stats_table.setStyle(
        TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)])
    )
    return stats_table


def _attr(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _build_file_table(framework, styles: dict, doc_extractions: dict = None) -> Table:
    header = [
        Paragraph("VERSION", styles["table_header"]),
        Paragraph("FILE NAME", styles["table_header"]),
        Paragraph("SIZE", styles["table_header"]),
        Paragraph("AI EXTRACTION STATUS", styles["table_header"]),
    ]
    rows = [header]

    for fv in reversed(framework.fileVersions or []):
        file_version = _attr(fv, "fileVersion")
        file_size = _attr(fv, "fileSize")
        original_name = _attr(fv, "originalFileName")
        ai_extraction = _attr(fv, "aiExtraction")
        if isinstance(ai_extraction, str) and doc_extractions and ai_extraction in doc_extractions:
            ai_extraction = doc_extractions[ai_extraction].aiExtraction
        is_current = file_version == framework.currentFileVersion
        size_str = f"{file_size / (1024 * 1024):.2f} MB" if file_size else "—"
        ai_status = (_attr(ai_extraction, "status") if ai_extraction else None) or "pending"
        version_style = styles["table_cell"]
        if is_current:
            version_style = ParagraphStyle(
                "VersionCurrent", parent=styles["table_cell"], fontName="Helvetica-Bold"
            )
        status_style = ParagraphStyle(
            "StatusCell",
            parent=styles["table_cell"],
            fontName="Helvetica-Bold",
            textColor=_stat_status_color(ai_status),
        )
        rows.append(
            [
                Paragraph(f"v{file_version}", version_style),
                Paragraph(original_name or "—", styles["table_cell"]),
                Paragraph(size_str, styles["table_cell"]),
                Paragraph(ai_status.upper(), status_style),
            ]
        )

    table = Table(rows, colWidths=[60, 240, 70, 130], repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), COLORS["primary_light"]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, COLORS["border"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]
    table.setStyle(TableStyle(style_cmds))
    return table


def _build_control_block(control: dict, styles: dict) -> list:
    flow: list = []

    weight = control.get("weightage")
    weight_display = "—" if weight is None else str(weight)

    header_table = Table(
        [
            [
                Paragraph(f"[{control.get('id')}] {control.get('name')}", styles["control_title"]),
                Paragraph(
                    f"Priority Weightage: {weight_display}/10",
                    styles["control_weightage"],
                ),
            ]
        ],
        colWidths=[340, 140],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 6),
                ("LINEBEFORE", (0, 0), (0, 0), 3, COLORS["secondary"]),
            ]
        )
    )
    flow.append(header_table)

    if control.get("description"):
        flow.append(Paragraph(control["description"], styles["control_desc"]))

    if control.get("remark"):
        remark_table = Table(
            [[Paragraph(f"<b>Remark:</b> {control['remark']}", styles["remark"])]],
            colWidths=[480],
        )
        remark_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), COLORS["remark_bg"]),
                    ("BOX", (0, 0), (-1, -1), 0.5, COLORS["remark_border"]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        flow.append(Spacer(1, 4))
        flow.append(remark_table)

    deployment_points = control.get("deployment_points") or []
    if deployment_points:
        flow.append(Paragraph("Deployment Guidelines:", styles["dp_heading"]))
        for idx, dp in enumerate(deployment_points, start=1):
            text = f"{idx}. {dp.get('name', '')}"
            if dp.get("remark"):
                text += f" | Guideline Remark: {dp['remark']}"
            flow.append(Paragraph(text, styles["dp_text"]))

    flow.extend(control_separator())
    return flow


def _calc_avg_dp_weightage(dps: list) -> float | None:
    dp_weights = []
    for dp in dps:
        dp_w = _attr(dp, "weightage")
        if dp_w is not None:
            try:
                dp_weights.append(float(dp_w))
            except (ValueError, TypeError):
                pass
    return round(sum(dp_weights) / len(dp_weights), 1) if dp_weights else None


def _parse_control(c) -> dict:
    dps = _attr(c, "deployment_points") or []
    c_weightage = _attr(c, "weightage")
    if c_weightage is None and dps:
        c_weightage = _calc_avg_dp_weightage(dps)

    return {
        "id": str(_attr(c, "id")) if _attr(c, "id") is not None else None,
        "name": _attr(c, "name"),
        "description": _attr(c, "description"),
        "weightage": c_weightage,
        "remark": _attr(c, "remark"),
        "deployment_points": [{"name": _attr(dp, "name"), "remark": _attr(dp, "remark")} for dp in dps],
    }


def _parse_section(section) -> dict:
    return {
        "id": str(_attr(section, "id")) if _attr(section, "id") is not None else None,
        "name": _attr(section, "name"),
        "controls": [_parse_control(c) for c in (_attr(section, "controls") or [])],
    }


def _framework_to_dict(framework, doc_extractions: dict = None) -> dict:
    """Convert nested pydantic/JSONB control structures to plain dicts for the PDF."""
    current = next(
        (
            fv
            for fv in (framework.fileVersions or [])
            if _attr(fv, "fileVersion") == framework.currentFileVersion
        ),
        None,
    )
    ai_extraction = _attr(current, "aiExtraction") if current else None

    if isinstance(ai_extraction, str) and doc_extractions and ai_extraction in doc_extractions:
        ai_extraction = doc_extractions[ai_extraction].aiExtraction

    controls = _attr(ai_extraction, "controls") if ai_extraction else None
    if not controls:
        return {"sections": []}

    controls_data = _attr(controls, "controls_data") or []
    sections = [_parse_section(section) for section in controls_data]
    return {"sections": sections}


def _create_header_story(framework, styles: dict) -> list:
    """Create the header section of the report."""
    story = []

    story.append(Paragraph("<u>Industry Framework Report</u>", styles["title"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(framework.frameworkName, styles["h1"]))
    story.append(
        Paragraph(
            f"Version: {framework.frameworkVersion}  |  Current: v{framework.currentFileVersion}",
            styles["meta"],
        )
    )

    dates_text = []
    if framework.createdAt:
        dates_text.append(f"Created On: {format_pdf_date(framework.createdAt)}")
    if framework.updatedAt:
        dates_text.append(f"Updated On: {format_pdf_date(framework.updatedAt)}")
    if dates_text:
        story.append(Paragraph("  \u2022  ".join(dates_text), styles["meta"]))

    return story


def _add_approval_status(story, framework, approval_by_user, styles: dict):
    """Add approval status to the story."""
    approval = framework.approval or {}
    approval_status = (_attr(approval, "status") if approval else "pending") or "pending"
    status_text = f"Expert Review: {approval_status.upper()}"
    approver_name = approval_by_user.name if approval_by_user else None
    if approval_status in ("approved", "rejected") and approver_name:
        verb = "Reviewed By" if approval_status == "approved" else "Rejected By"
        status_text += f"  \u2022  {verb}: {approver_name}"
        approval_date = _attr(approval, "date")
        if approval and approval_date:
            status_text += f" on {format_pdf_date(approval_date)}"
    story.append(Paragraph(status_text, styles["meta"]))
    story.append(Spacer(1, 14))


def _add_file_info(story, framework, styles: dict, doc_extractions: dict = None):
    """Add file information section to the story."""
    if framework.fileVersions:
        story.append(Paragraph("File Information", styles["section_title"]))
        story.append(_build_file_table(framework, styles, doc_extractions))


def _add_controls_section(story, sections: list, styles: dict):
    """Add controls section to the story."""
    story.append(NextPageTemplate("report"))
    story.append(PageBreak())
    story.append(Paragraph("Controls", styles["section_title"]))

    if not sections:
        story.append(
            Paragraph("No controls have been extracted for this framework yet.", styles["no_controls"])
        )
        return

    for section in sections:
        _add_section_block(story, section, styles)


def _add_section_block(story, section: dict, styles: dict):
    """Add a single section block to the story."""
    header_table = Table(
        [[Paragraph(f"{section['id']} {section['name']}", styles["section_header"])]],
        colWidths=[520],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLORS["primary_light"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(KeepTogether([header_table, Spacer(1, 6)]))

    controls = section.get("controls") or []
    if not controls:
        story.append(Paragraph("No controls in this section.", styles["no_controls"]))
        story.append(Spacer(1, 8))
        return

    for control in controls:
        block = _build_control_block(control, styles)
        story.extend(block)


def _on_page(canvas, framework):
    """Page template callback."""
    page_num = canvas.getPageNumber()
    header_text = f"{framework.frameworkName.upper()} - VERSION {framework.frameworkVersion}"
    draw_common_footer(canvas, page_num, REPORT_PAGESIZE, header_text)


def generate_framework_report_pdf(framework, approval_by_user=None, doc_extractions: dict = None) -> bytes:
    styles = get_shared_styles()
    buffer = io.BytesIO()

    frame = get_shared_frame(id="normal")

    def page_callback(canvas, doc):
        _on_page(canvas, framework)

    doc = BaseDocTemplate(
        buffer,
        pagesize=REPORT_PAGESIZE,
        **REPORT_MARGINS,
        title=f"{framework.frameworkName} Report",
    )
    doc.addPageTemplates([PageTemplate(id="report", frames=[frame], onPage=page_callback)])

    story = []

    # Build header
    story.extend(_create_header_story(framework, styles))
    _add_approval_status(story, framework, approval_by_user, styles)

    # Build stats
    fw_dict = _framework_to_dict(framework, doc_extractions)
    story.append(_build_stats_table(fw_dict["sections"], styles))
    story.append(Spacer(1, 18))

    # Build file info
    _add_file_info(story, framework, styles, doc_extractions)

    # Build controls section
    _add_controls_section(story, fw_dict["sections"], styles)

    doc.build(story)
    return buffer.getvalue()
