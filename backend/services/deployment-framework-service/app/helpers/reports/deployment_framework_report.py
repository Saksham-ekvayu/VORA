"""Port of deployment-framework-service-main/src/helpers/deployment-framework-report.helper.js.

Rebuilt with reportlab (platypus flowables + reportlab.graphics charts) instead
of pdfkit's manual absolute positioning; content and structure are preserved,
including the compliance radar (spider) chart.
"""

from io import BytesIO
from typing import Any

from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.spider import SpiderChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from vora_shared.pdf import COLORS as SHARED_COLORS
from vora_shared.pdf import (
    REPORT_MARGINS,
    REPORT_PAGESIZE,
    control_separator,
    draw_common_footer,
    get_shared_styles,
)

IMPLEMENTED = "Implemented"
PARTIALLY_IMPLEMENTED = "Partially Implemented"
NOT_IMPLEMENTED = "Not Implemented"
HIGH = "High"
MEDIUM = "Medium"
LOW = "Low"

_COLORS = {
    "primary": SHARED_COLORS["primary"],
    "primaryLight": SHARED_COLORS["primary_light"],
    "secondary": SHARED_COLORS["secondary"],
    "accent": SHARED_COLORS["warning"],
    "darkText": SHARED_COLORS["dark_text"],
    "mutedText": SHARED_COLORS["muted_text"],
    "lightText": SHARED_COLORS["light_text"],
    "borderColor": SHARED_COLORS["border"],
    "cardBg": SHARED_COLORS["card_bg"],
    "green": SHARED_COLORS["green"],
    "amber": SHARED_COLORS["amber"],
    "red": SHARED_COLORS["danger"],
    "gray": SHARED_COLORS["gray"],
}

_base_styles = getSampleStyleSheet()
_shared_styles = get_shared_styles()

_SECTION = _shared_styles["section_title"]
_SMALL_MUTED = ParagraphStyle(
    "DFRSmallMuted", parent=_base_styles["Normal"], textColor=_COLORS["mutedText"], fontSize=8.5
)


def _format_size(num_bytes: float | None) -> str:
    if not num_bytes:
        return "\u2014"
    if num_bytes >= 1_048_576:
        return f"{num_bytes / 1_048_576:.2f} MB"
    if num_bytes >= 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes} B"


def _normalise_status(raw: str | None) -> str:
    s = str(raw or "").strip().lower()
    if s == "implemented":
        return IMPLEMENTED
    if s == "not implemented" or "not impl" in s:
        return NOT_IMPLEMENTED
    return PARTIALLY_IMPLEMENTED


def _normalise_match(score: float) -> str:
    if score >= 80:
        return HIGH
    if score >= 60:
        return MEDIUM
    return LOW


def _map_dp_row(row: dict[str, Any], idx: int) -> dict[str, Any]:
    assigned_dp = row.get("assigned_framework_deployment_points") or {}
    deployment_dp = row.get("deployment_framework_deployment_points") or {}
    return {
        "no": assigned_dp.get("id", idx + 1),
        "assigned_framework_control_id": row.get("assigned_framework_control_id", ""),
        "assigned_framework_control_name": row.get("assigned_framework_control_name", ""),
        "assigned_dp_id": assigned_dp.get("id"),
        "clientDp": assigned_dp.get("point", ""),
        "deployment_framework_control_id": row.get("deployment_framework_control_id", ""),
        "deployment_framework_control_name": row.get("deployment_framework_control_name", ""),
        "deployment_dp_id": deployment_dp.get("id"),
        "matchedFp": deployment_dp.get("point", ""),
        "reviewComment": row.get("reviewComment") or "",
        "sim": float(row.get("similarity_score") or 0),
        "status": _normalise_status(row.get("implementation_status")),
    }


def _build_dp_data(gap_results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    dp_data: dict[str, list[dict[str, Any]]] = {}
    for row in gap_results or []:
        dep_id = row.get("deployment_framework_control_id") or row.get("assigned_framework_control_id")
        if not dep_id:
            continue
        dp_data.setdefault(dep_id, [])
        dp_data[dep_id].append(_map_dp_row(row, len(dp_data[dep_id])))
    return dp_data


def _count_from_dp_rows(dp_rows: list[dict[str, Any]]) -> tuple[int, int, int]:
    impl = sum(1 for d in dp_rows if d["status"] == IMPLEMENTED)
    partial = sum(1 for d in dp_rows if d["status"] == PARTIALLY_IMPLEMENTED)
    not_impl = len(dp_rows) - impl - partial
    return impl, partial, not_impl


def _avg_sim(dp_rows: list[dict[str, Any]]) -> float:
    if not dp_rows:
        return 0.0
    return sum(d["sim"] for d in dp_rows) / len(dp_rows)


def _process_comparison_control(
    ctrl: dict[str, Any], dp_data: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    control_id = (
        ctrl.get("deployment_framework_control_id") or ctrl.get("assigned_framework_control_id") or ""
    )
    raw_score = ctrl.get("comparison_score") or 0
    score = round(raw_score * 100) if raw_score <= 1 else round(raw_score)

    impl, partial, not_impl = _count_from_dp_rows(dp_data.get(control_id, []))
    sim = _avg_sim(dp_data.get(control_id, []))

    return {
        "id": control_id,
        "name": ctrl.get("assigned_framework_control_name")
        or ctrl.get("deployment_framework_control_name")
        or control_id,
        "assigned_id": ctrl.get("assigned_framework_control_id") or "",
        "assigned_name": ctrl.get("assigned_framework_control_name") or "",
        "deployment_id": ctrl.get("deployment_framework_control_id") or "",
        "deployment_name": ctrl.get("deployment_framework_control_name") or "",
        "score": score,
        "match": _normalise_match(score),
        "impl": impl,
        "partial": partial,
        "notImpl": not_impl,
        "sim": round(sim, 1),
    }


def _parse_report_data(
    package_data: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    gap_results = ((package_data.get("gapAnalysis") or {}).get("deployment_gap_results")) or []
    dp_data = _build_dp_data(gap_results)

    controls: list[dict[str, Any]] = []
    comparison_result = ((package_data.get("comparison") or {}).get("comparison_result")) or []

    for section in comparison_result:
        for ctrl in section.get("controls") or []:
            controls.append(_process_comparison_control(ctrl, dp_data))

    return controls, dp_data


def _score_color(score: float):
    if score >= 85:
        return _COLORS["green"]
    if score >= 70:
        return colors.HexColor("#2563eb")
    if score >= 55:
        return colors.HexColor("#ca8a04")
    return _COLORS["red"]


def _sim_color(sim: float):
    if sim >= 70:
        return colors.HexColor("#16a34a")
    if sim >= 60:
        return colors.HexColor("#ca8a04")
    return colors.HexColor("#dc2626")


def _status_badge_colors(status: str) -> tuple[Any, Any]:
    if status == IMPLEMENTED:
        return colors.HexColor("#e6f4ea"), colors.HexColor("#137333")
    if status == PARTIALLY_IMPLEMENTED:
        return colors.HexColor("#fef7e0"), colors.HexColor("#b06000")
    if status == NOT_IMPLEMENTED:
        return colors.HexColor("#fce8e6"), colors.HexColor("#c5221f")
    return colors.HexColor("#f3f4f6"), colors.HexColor("#4b5563")


def _donut_drawing(chart_data: list[tuple[str, int, Any]], center_label: str) -> Drawing:
    total = sum(v for _, v, _ in chart_data)
    d = Drawing(240, 150)
    pie = Pie()
    pie.x = 120
    pie.y = 20
    pie.width = 100
    pie.height = 100
    pie.data = [max(v, 0.0001) for _, v, _ in chart_data] if total else [1]
    pie.labels = None
    pie.simpleLabels = False
    for i, (_, _, color) in enumerate(chart_data):
        pie.slices[i].fillColor = color
        pie.slices[i].strokeColor = colors.white
        pie.slices[i].strokeWidth = 1
    d.add(pie)
    d.add(String(170, 5, center_label, fontSize=8, fillColor=_COLORS["mutedText"], textAnchor="middle"))
    legend_y = 110
    for label, value, color in chart_data:
        pct = (value / total * 100) if total else 0
        d.add(String(10, legend_y, "\u25a0", fillColor=color, fontSize=9))
        d.add(
            String(
                20,
                legend_y,
                f"{label}: {value} ({pct:.1f}%)",
                fontSize=7,
                fillColor=_COLORS["darkText"],
            )
        )
        legend_y -= 12
    return d


def _spider_drawing(controls: list[dict[str, Any]]) -> Drawing | None:
    if not controls:
        return None
    available_width = REPORT_PAGESIZE[0] - (REPORT_MARGINS["leftMargin"] + REPORT_MARGINS["rightMargin"])

    # Increase canvas to use landscape width better, chart itself is a square
    d = Drawing(available_width, 420)
    chart = SpiderChart()

    # Center the square chart (360x360) within the available width
    chart.width = 360
    chart.height = 360
    chart.x = (available_width - chart.width) / 2
    chart.y = 30

    chart.data = [[c["score"] for c in controls]]

    chart.labels = [c["id"] for c in controls]
    chart.spokeLabels.fontName = "Helvetica"
    if len(controls) > 70:
        chart.spokeLabels.fontSize = 4
    elif len(controls) > 40:
        chart.spokeLabels.fontSize = 5
    elif len(controls) > 20:
        chart.spokeLabels.fontSize = 6
    else:
        chart.spokeLabels.fontSize = 7

    chart.strands[0].strokeColor = _COLORS["primary"]
    chart.strands[0].fillColor = colors.Color(
        _COLORS["primary"].red, _COLORS["primary"].green, _COLORS["primary"].blue, alpha=0.15
    )
    chart.spokes.strokeColor = colors.HexColor("#e2e8f0")
    chart.spokes.strokeWidth = 0.5
    d.add(chart)
    return d


def _add_expert_review_section(story: list, expert_review: dict):
    if (
        expert_review
        and expert_review.get("assignedExpert")
        and expert_review.get("status") not in (None, "pending")
    ):
        expert = expert_review["assignedExpert"]
        story.append(Spacer(1, 4 * mm))
        story.append(
            Paragraph(
                f"<b>Expert Review:</b> {expert.get('name', '—')} ({expert.get('email', '')}) "
                f"— {str(expert_review.get('status')).upper()}",
                _shared_styles["meta"],
            )
        )
        if expert_review.get("comments"):
            story.append(Paragraph(f"“{expert_review['comments']}”", _SMALL_MUTED))


def _add_document_table(story: list, documents: list):
    if not documents:
        return
    story.append(Paragraph(f"File Information ({len(documents)} files)", _SECTION))
    rows = [["VERSION", "FILE NAME", "SIZE"]]
    for fv in documents:
        rows.append(
            [
                f"v{fv.get('fileVersion', '1.0.0')}",
                Paragraph(fv.get("originalFileName", "—"), _shared_styles["table_cell"]),
                _format_size(fv.get("fileSize")),
            ]
        )
    file_table = Table(rows, colWidths=["15%", "70%", "15%"], hAlign="LEFT")
    file_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _COLORS["primaryLight"]),
                ("TEXTCOLOR", (0, 0), (-1, 0), _COLORS["primary"]),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, _COLORS["borderColor"]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(file_table)
    story.append(Spacer(1, 6 * mm))


def _add_implementation_status_table(story: list, controls: list, total_dp: int):
    total_compared = len(controls)
    avg_score = round(sum(c["score"] for c in controls) / total_compared) if total_compared else 0
    high_match = sum(1 for c in controls if c["match"] == HIGH)
    low_match = sum(1 for c in controls if c["match"] == LOW)

    story.append(Paragraph("Implementation Status &amp; Match Distribution", _SECTION))
    stats = [
        ("TOTAL DEPLOYMENT POINTS", str(total_dp)),
        ("CONTROLS ASSESSED", str(total_compared)),
        ("AVG ACHIEVED SCORE", f"{avg_score}%"),
        ("HIGH-MATCH CONTROLS", f"{high_match}/{total_compared}"),
        ("LOW-MATCH CONTROLS", f"{low_match}/{total_compared}"),
    ]
    stat_style_val = ParagraphStyle(
        "DFRStatVal",
        parent=_base_styles["Normal"],
        fontSize=14,
        fontName="Helvetica-Bold",
        textColor=_COLORS["primary"],
        alignment=1,
    )
    stat_style_label = ParagraphStyle(
        "DFRStatLabel", parent=_base_styles["Normal"], fontSize=7, textColor=_COLORS["mutedText"], alignment=1
    )
    stat_cells = [[Paragraph(v, stat_style_val)] for _, v in stats]
    stat_label_cells = [[Paragraph(l, stat_style_label)] for l, _ in stats]
    combined_rows = [
        [stat_cells[i][0] for i in range(len(stats))],
        [stat_label_cells[i][0] for i in range(len(stats))],
    ]
    stat_table = Table(combined_rows, colWidths=[f"{100.0/len(stats)}%"] * len(stats), hAlign="LEFT")
    stat_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, _COLORS["borderColor"]),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, _COLORS["borderColor"]),
                ("BACKGROUND", (0, 0), (-1, -1), _COLORS["cardBg"]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(stat_table)
    story.append(Spacer(1, 6 * mm))


def _add_charts(
    story: list, controls: list, total_dp: int, total_impl: int, total_partial: int, total_not_impl: int
):
    if total_dp > 0:
        impl_chart = _donut_drawing(
            [
                ("Implemented", total_impl, _COLORS["green"]),
                ("Partial", total_partial, _COLORS["accent"]),
                ("Not Impl.", total_not_impl, _COLORS["red"]),
            ],
            "Implementation",
        )

        match_high = sum(1 for c in controls if c["match"] == HIGH)
        match_med = sum(1 for c in controls if c["match"] == MEDIUM)
        match_low = sum(1 for c in controls if c["match"] == LOW)

        match_chart = _donut_drawing(
            [
                ("High Match", match_high, _COLORS["green"]),
                ("Medium Match", match_med, _COLORS["amber"]),
                ("Low Match", match_low, _COLORS["red"]),
            ],
            "Match Distribution",
        )

        charts_table = Table([[impl_chart, match_chart]], colWidths=["50%", "50%"], hAlign="CENTER")
        story.append(charts_table)
        story.append(Spacer(1, 4 * mm))

    spider = _spider_drawing(controls)
    if spider:
        spider_elements = [
            Paragraph("Compliance Radar Analysis", _SECTION),
            Paragraph(
                f"Spider chart mapping all {len(controls)} controls by achieved compliance score.",
                _SMALL_MUTED,
            ),
            spider,
        ]
        story.append(KeepTogether(spider_elements))
        story.append(PageBreak())


def _calc_avg_dp_weightage(dps: list[dict[str, Any]]) -> float | None:
    dp_weights = []
    for dp in dps:
        dp_w = dp.get("weightage")
        if dp_w is not None:
            try:
                dp_weights.append(float(dp_w))
            except (ValueError, TypeError):
                pass
    return round(sum(dp_weights) / len(dp_weights), 1) if dp_weights else None


def _get_control_weightage(ctrl: dict[str, Any]) -> str | int | float:
    weight_display = ctrl.get("weightage")
    if weight_display is None:
        weight_display = _calc_avg_dp_weightage(ctrl.get("deployment_points") or [])

    if weight_display is None:
        return "N/A"
    if isinstance(weight_display, (int, float)) and float(weight_display).is_integer():
        return int(weight_display)
    return weight_display


def _build_merge_control_block(ctrl: dict[str, Any]) -> list:
    ctrl_block = []
    weight_display = _get_control_weightage(ctrl)

    ctrl_header_table = Table(
        [
            [
                Paragraph(
                    f"[{ctrl.get('id', '')}] {ctrl.get('name', 'Unnamed Control')}",
                    _shared_styles["control_title"],
                ),
                Paragraph(f"Weightage: {weight_display}/10", _shared_styles["control_weightage"]),
            ]
        ],
        colWidths=["75%", "25%"],
    )
    ctrl_header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 6),
                ("LINEBEFORE", (0, 0), (0, 0), 3, SHARED_COLORS["secondary"]),
            ]
        )
    )
    ctrl_block.append(ctrl_header_table)

    if ctrl.get("description"):
        ctrl_block.append(Paragraph(ctrl["description"], _shared_styles["control_desc"]))

    if ctrl.get("remark"):
        remark_table = Table(
            [[Paragraph(f"<b>Remark:</b> {ctrl['remark']}", _shared_styles["remark"])]],
            colWidths=["100%"],
        )
        remark_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), SHARED_COLORS["remark_bg"]),
                    ("BOX", (0, 0), (-1, -1), 0.5, SHARED_COLORS["remark_border"]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        ctrl_block.append(Spacer(1, 4))
        ctrl_block.append(remark_table)

    deployment_points = ctrl.get("deployment_points") or []
    if deployment_points:
        ctrl_block.append(Paragraph("Deployment Guidelines:", _shared_styles["dp_heading"]))
        for idx, dp in enumerate(deployment_points, start=1):
            text = f"{idx}. {dp.get('name', 'Unnamed DP')}"
            if dp.get("remark"):
                text += f" | Guideline Remark: {dp['remark']}"
            ctrl_block.append(Paragraph(text, _shared_styles["dp_text"]))

    ctrl_block.extend(control_separator())
    return ctrl_block


def _build_merge_section_block(section: dict[str, Any]) -> list:
    block = []
    header_table = Table(
        [
            [
                Paragraph(
                    f"{section.get('id', '')} {section.get('name', 'Unnamed Section')}",
                    _shared_styles["section_header"],
                )
            ]
        ],
        colWidths=["100%"],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SHARED_COLORS["primary_light"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    block.append(KeepTogether([header_table, Spacer(1, 6)]))

    controls = section.get("controls") or []
    if not controls:
        block.append(Paragraph("No controls in this section.", _shared_styles["no_controls"]))
        block.append(Spacer(1, 8))
        return block

    for ctrl in controls:
        block.extend(_build_merge_control_block(ctrl))

    return block


def _add_merge_details(story: list, merge_sections: list):
    if not merge_sections:
        return
    total_merge_controls = sum(len(s.get("controls") or []) for s in merge_sections)
    if not total_merge_controls:
        return
    story.append(Paragraph("Merge Extraction Details", _shared_styles["section_title"]))
    for section in merge_sections:
        story.extend(_build_merge_section_block(section))
    story.append(Spacer(1, 4 * mm))


def _add_control_compliance_table(story: list, controls: list):
    if not controls:
        return
    story.append(Paragraph("Control Compliance Detail", _SECTION))
    rows = [["ID", "Control Name", "Score", "Match", "Impl", "Part", "Not"]]
    for c in controls:
        rows.append(
            [
                c["assigned_id"] or c["id"],
                Paragraph(c["name"], _shared_styles["table_cell"]),
                f"{c['score']}%",
                c["match"],
                str(c["impl"]),
                str(c["partial"]),
                str(c["notImpl"]),
            ]
        )
    detail_table = Table(rows, colWidths=["10%", "48%", "8%", "10%", "8%", "8%", "8%"], hAlign="LEFT")
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), _COLORS["primaryLight"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), _COLORS["primary"]),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, _COLORS["borderColor"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i, c in enumerate(controls, start=1):
        style_cmds.append(("TEXTCOLOR", (2, i), (2, i), _score_color(c["score"])))
    detail_table.setStyle(TableStyle(style_cmds))
    story.append(detail_table)
    story.append(Spacer(1, 6 * mm))


def _add_deployment_point_analysis(story: list, controls: list, dp_data: dict, total_dp: int):
    if total_dp <= 0:
        return
    story.append(Paragraph("Deployment Point Analysis", _SECTION))
    story.append(
        Paragraph(
            f"Granular view of all {total_dp} deployment points, mapped to their best-matched framework point.",
            _SMALL_MUTED,
        )
    )
    for ctrl in controls:
        gaps = dp_data.get(ctrl["id"], [])
        if not gaps:
            continue
        story.append(
            Paragraph(
                f"Assigned: [{ctrl['assigned_id'] or 'N/A'}] {ctrl['assigned_name'] or '—'}<br/>"
                f"Deployment: [{ctrl['deployment_id'] or 'N/A'}] {ctrl['deployment_name'] or '—'}",
                ParagraphStyle(
                    "DFRGapHeader",
                    parent=_base_styles["Normal"],
                    fontSize=8.5,
                    leading=13,
                    textColor=_COLORS["primary"],
                    backColor=_COLORS["primaryLight"],
                    borderPadding=6,
                    spaceBefore=12,
                    spaceAfter=4,
                ),
            )
        )
        gap_rows = [["DP", "Assigned Point", "Matched Point", "Sim", "Status"]]
        for idx, gap in enumerate(gaps):
            gap_rows.append(
                [
                    f"D{idx + 1}",
                    Paragraph(gap["clientDp"], _shared_styles["table_cell"]),
                    Paragraph(
                        gap["matchedFp"] or "No matching deployment point", _shared_styles["table_cell"]
                    ),
                    f"{gap['sim']:.1f}%",
                    Paragraph(
                        f"<font color='#{_status_badge_colors(gap['status'])[1].hexval()[2:]}'>{gap['status']}</font>",
                        _shared_styles["table_cell"],
                    ),
                ]
            )
        gap_table = Table(gap_rows, colWidths=["5%", "37.5%", "37.5%", "8%", "12%"], hAlign="LEFT")
        gap_style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("GRID", (0, 0), (-1, -1), 0.5, _COLORS["borderColor"]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
        for i, gap in enumerate(gaps, start=1):
            bg, fg = _status_badge_colors(gap["status"])
            gap_style_cmds.append(("BACKGROUND", (4, i), (4, i), bg))
            gap_style_cmds.append(("TEXTCOLOR", (4, i), (4, i), fg))
            gap_style_cmds.append(("TEXTCOLOR", (3, i), (3, i), _sim_color(gap["sim"])))
        gap_table.setStyle(TableStyle(gap_style_cmds))
        story.append(gap_table)
        story.append(Spacer(1, 3 * mm))


def generate_deployment_framework_report_pdf(framework: Any, package_data: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=REPORT_PAGESIZE,
        **REPORT_MARGINS,
        title="Deployment Framework Report",
    )

    fw_name = getattr(framework, "frameworkName", None) or "Framework Report"
    fw_version = getattr(framework, "frameworkVersion", None) or "N/A"

    controls, dp_data = _parse_report_data(package_data)

    total_impl = sum(c["impl"] for c in controls)
    total_partial = sum(c["partial"] for c in controls)
    total_not_impl = sum(c["notImpl"] for c in controls)
    total_dp = total_impl + total_partial + total_not_impl

    story: list[Any] = []

    story.append(Paragraph("Deployment Framework Report", _shared_styles["title"]))
    story.append(HRFlowable(width="100%", color=_COLORS["borderColor"], thickness=1, spaceAfter=6))

    badge_row = " &nbsp;&nbsp; ".join(
        [
            f"<font color='#1a73e8'><b>{fw_version}</b></font>",
            f"<font color='#b06000'><b>{str(package_data.get('type', 'pre-release')).title()}</b></font>",
            f"<font color='#137333'><b>v{package_data.get('packageVersion', '1.0.0')}</b></font>",
            f"<font color='#1a73e8'><b>{str(package_data.get('status', 'pending')).title()}</b></font>",
        ]
    )
    story.append(Paragraph(badge_row, _shared_styles["meta"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(fw_name, _shared_styles["h1"]))
    story.append(
        Paragraph(
            f"{fw_name} Deployment Framework Gap Analysis &amp; Compliance Audit Report "
            f"— Package v{package_data.get('packageVersion', '1.0.0')}, {package_data.get('trigger', '')}",
            _shared_styles["meta"],
        )
    )

    _add_expert_review_section(story, package_data.get("expertReview"))
    story.append(Spacer(1, 6 * mm))

    _add_document_table(story, package_data.get("documents") or [])
    _add_implementation_status_table(story, controls, total_dp)
    _add_charts(story, controls, total_dp, total_impl, total_partial, total_not_impl)
    _add_merge_details(story, (package_data.get("mergeDocument") or {}).get("controls_data") or [])
    _add_control_compliance_table(story, controls)
    _add_deployment_point_analysis(story, controls, dp_data, total_dp)

    def _footer(canvas, doc_):
        header_text = f"{fw_name.upper()} - PACKAGE v{package_data.get('packageVersion', '1.0.0')}"
        draw_common_footer(canvas, doc_.page, doc_.pagesize, header_text)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
