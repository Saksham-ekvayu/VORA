"""Port of deployment-framework-service-main/src/helpers/framework-assignment-report.helper.js.

Rebuilt with reportlab/platypus (flowable-based layout) instead of pdfkit's
manual absolute positioning; content and structure are preserved.
"""

from io import BytesIO
from typing import Any

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
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
    VoraDocTemplate,
    build_stat_card,
    build_toc_story,
    control_separator,
    draw_common_footer,
    format_pdf_date,
    get_cover_callback,
    get_cover_frame,
    get_shared_frame,
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
    from reportlab.platypus import HRFlowable

    fw_name = assignment.frameworkName or assignment.frameworkCode

    # Content
    story.append(Spacer(1, 30))
    story.append(Paragraph("COMPLIANCE / SECURITY", _styles_dict["cover_over_title"]))

    story.append(Paragraph("Assigned Framework", _styles_dict["cover_title1"]))
    story.append(Paragraph("Report", _styles_dict["cover_title2"]))
    story.append(
        HRFlowable(
            width=45 * mm, color=COLORS["primary"], thickness=3.5, spaceBefore=4, spaceAfter=20, hAlign="LEFT"
        )
    )

    story.append(Spacer(1, 10))
    story.append(Paragraph(str(fw_name), _styles_dict["cover_subtitle1"]))
    story.append(Paragraph("Framework assignment and compliance reference", _styles_dict["cover_subtitle2"]))

    # Version Info Box
    v_styles = {
        "lbl": ParagraphStyle("Lbl", fontName="Helvetica-Bold", fontSize=8, textColor=COLORS["primary"]),
        "val": ParagraphStyle(
            "Val", fontName="Helvetica", fontSize=12, textColor=COLORS["dark_text"], spaceBefore=5
        ),
    }

    col1 = [
        Paragraph("FRAMEWORK VERSION", v_styles["lbl"]),
        Paragraph(str(assignment.frameworkVersion or "-"), v_styles["val"]),
    ]
    col2 = [
        Paragraph("CURRENT VERSION", v_styles["lbl"]),
        Paragraph(f"v{file_version.fileVersion}", v_styles["val"]),
    ]

    box_table = Table([[col1, col2]], colWidths=[80 * mm, 80 * mm])
    box_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLORS["primary_light"]),
                ("ROUNDEDCORNERS", [8, 8, 8, 8]),
                ("BOX", (0, 0), (-1, -1), 0.5, COLORS["border"]),
                ("LINEBEFORE", (1, 0), (1, -1), 0.5, COLORS["border"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 15),
                ("RIGHTPADDING", (0, 0), (-1, -1), 15),
                ("TOPPADDING", (0, 0), (-1, -1), 15),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 15),
            ]
        )
    )
    story.append(box_table)


def _add_stats_section(
    story: list[Any],
    assignment: Any,
    customer: Any,
    sections: list[Any],
    applicable_controls: list[Any],
    controls: list[Any],
    deployment_points: list[Any],
    org_specific_controls: int,
    avg_customer_weightage: float,
):
    # Assignment Information Table
    story.append(Paragraph("Assignment Information", _styles_dict["section_title"]))
    story.append(Spacer(1, 4 * mm))

    def _make_cell(label, value):
        if not label:
            return ""
        return [
            Paragraph(
                label,
                ParagraphStyle(
                    "AssigLabel", fontName="Helvetica-Bold", fontSize=8, textColor=COLORS["primary"]
                ),
            ),
            Paragraph(
                value,
                ParagraphStyle(
                    "AssigVal",
                    fontName="Helvetica",
                    fontSize=10,
                    textColor=COLORS["dark_text"],
                    spaceBefore=4,
                ),
            ),
        ]

    data = [
        [
            _make_cell("CUSTOMER", _display_user(customer)),
            _make_cell("ASSIGNMENT STATUS", str(assignment.status or "assigned").upper()),
        ],
    ]

    info_table = Table(data, colWidths=[80 * mm, 80 * mm], hAlign="LEFT")
    info_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLORS["primary_light"]),
                ("ROUNDEDCORNERS", [8, 8, 8, 8]),
                ("BOX", (0, 0), (-1, -1), 0.5, COLORS["border"]),
                ("LINEBEFORE", (1, 0), (1, -1), 0.5, COLORS["border"]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ]
        )
    )
    story.append(info_table)

    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("Statistics", _styles_dict["section_title"]))

    usable_width = REPORT_PAGESIZE[0] - (REPORT_MARGINS["leftMargin"] + REPORT_MARGINS["rightMargin"])
    card_width = usable_width / 3

    stats = [
        ("SECTIONS", len(sections)),
        ("APPLICABLE CONTROLS", len(applicable_controls)),
        ("NOT APPLICABLE", len(controls) - len(applicable_controls)),
        ("DEPLOYMENT POINTS", len(deployment_points)),
        ("ORG SPECIFIC CONTROLS", org_specific_controls),
        ("AVG CUSTOMER WEIGHT", f"{avg_customer_weightage}/10"),
    ]
    stat_cards = [build_stat_card(label, value, _styles_dict, width=card_width) for label, value in stats]
    rows = [stat_cards[i : i + 3] for i in range(0, len(stat_cards), 3)]
    section_table = Table(rows, hAlign="LEFT", spaceBefore=0, spaceAfter=0)
    section_table.setStyle(
        TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)])
    )
    story.append(section_table)
    story.append(Spacer(1, 15 * mm))


def _get_user_info(user: Any) -> tuple[str, str]:
    if not user:
        return "System / Unknown", ""

    name = ""
    email = ""
    if hasattr(user, "name") and user.name:
        name = user.name
    elif isinstance(user, dict) and user.get("name"):
        name = user["name"]

    if hasattr(user, "email") and user.email:
        email = user.email
    elif isinstance(user, dict) and user.get("email"):
        email = user["email"]

    if not name and not email:
        return str(user), ""

    if not name:
        name = email
        email = ""

    return name, email


def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _add_signatures_section(story: list[Any], assignment: Any):
    from vora_shared.pdf import add_signatures_block, format_pdf_date

    assigned_name, assigned_email = _get_user_info(_safe_get(assignment.assignment, "assignedBy"))
    assigned_on = format_pdf_date(_safe_get(assignment.assignment, "assignedAt"))

    finalized = _safe_get(assignment.finalization, "isFinalized")
    finalized_name, finalized_email = (
        _get_user_info(_safe_get(assignment.finalization, "finalizedBy")) if finalized else ("N/A", "")
    )
    finalized_on = format_pdf_date(_safe_get(assignment.finalization, "finalizedAt")) if finalized else "N/A"

    story.append(Spacer(1, 15 * mm))
    story.append(Paragraph("Signatures & Approvals", _styles_dict["section_title"]))

    sigs = [
        {
            "title": "ASSIGNED BY",
            "name": assigned_name,
            "email": assigned_email,
            "date": assigned_on,
        },
        {
            "title": "FINALIZED BY",
            "name": finalized_name,
            "email": finalized_email,
            "date": finalized_on,
        },
    ]
    add_signatures_block(story, sigs)


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

    name = control.name or ""
    if name:
        name = name[0].upper() + name[1:]
    text = f"[{control.id}] {name}"
    key = str(hash(text))
    story.append(Paragraph(text, _styles_dict["toc_invisible_control"]))

    header_row = Table(
        [
            [
                Paragraph(f'<a name="{key}"/>{text}', title_style),
                Paragraph(label_text, label_style),
            ]
        ],
        colWidths=[doc_width * 0.65, doc_width * 0.35],
        hAlign="LEFT",
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
        key = str(hash(section_title))
        story.append(Paragraph(section_title, _styles_dict["toc_invisible_section"]))

        section_bar = Table(
            [[Paragraph(f'<a name="{key}"/>{section_title}', _styles_dict["section_title"])]],
            colWidths=[doc_width],
            hAlign="LEFT",
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

    frame = get_shared_frame(id="normal")
    cover_frame = get_cover_frame(id="cover")

    header_fw_name = assignment.frameworkName or assignment.frameworkCode or "Framework"
    header_text = f"{str(header_fw_name).upper()} - VERSION {assignment.frameworkVersion or '-'}"

    def page_callback(canvas, doc):
        draw_common_footer(canvas, doc.page, REPORT_PAGESIZE, header_text)

    cover_callback = get_cover_callback("Assigned Framework Report", f"v{file_version.fileVersion}")

    doc = VoraDocTemplate(
        buffer,
        pagesize=REPORT_PAGESIZE,
        **REPORT_MARGINS,
        title="Assigned Framework Report",
    )
    doc.addPageTemplates(
        [
            PageTemplate(id="cover", frames=[cover_frame], onPage=cover_callback),
            PageTemplate(id="report", frames=[frame], onPage=page_callback),
        ]
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
    story.append(NextPageTemplate("report"))
    story.append(PageBreak())

    # TOC
    story.extend(build_toc_story(_styles_dict))

    _add_stats_section(
        story,
        assignment,
        customer,
        sections,
        applicable_controls,
        controls,
        deployment_points,
        org_specific_controls,
        avg_customer_weightage,
    )

    # Controls
    _add_controls_section(story, sections, frame.width)

    # Signatures
    _add_signatures_section(story, assignment)

    doc.multiBuild(story)
    return buffer.getvalue()
