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
from reportlab.lib.pagesizes import A4, landscape
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

IMPLEMENTED = "Implemented"
PARTIALLY_IMPLEMENTED = "Partially Implemented"
NOT_IMPLEMENTED = "Not Implemented"
HIGH = "High"
MEDIUM = "Medium"
LOW = "Low"

_COLORS = {
    "primary": colors.HexColor("#0f766e"),
    "primaryLight": colors.HexColor("#f0fdfa"),
    "secondary": colors.HexColor("#0d9488"),
    "accent": colors.HexColor("#f59e0b"),
    "darkText": colors.HexColor("#1f2937"),
    "mutedText": colors.HexColor("#4b5563"),
    "lightText": colors.HexColor("#9ca3af"),
    "borderColor": colors.HexColor("#e5e7eb"),
    "cardBg": colors.HexColor("#f8fafc"),
    "green": colors.HexColor("#16a34a"),
    "amber": colors.HexColor("#d97706"),
    "red": colors.HexColor("#dc2626"),
    "gray": colors.HexColor("#4b5563"),
}

_styles = getSampleStyleSheet()
_H_TITLE = ParagraphStyle("DFRTitle", parent=_styles["Title"], textColor=_COLORS["primary"], fontSize=18)
_H1 = ParagraphStyle("DFRH1", parent=_styles["Heading1"], textColor=_COLORS["darkText"], fontSize=20)
_MUTED = ParagraphStyle("DFRMuted", parent=_styles["Normal"], textColor=_COLORS["mutedText"], fontSize=11)
_SECTION = ParagraphStyle("DFRSection", parent=_styles["Heading2"], textColor=_COLORS["darkText"], fontSize=12)
_SMALL_MUTED = ParagraphStyle("DFRSmallMuted", parent=_styles["Normal"], textColor=_COLORS["mutedText"], fontSize=8.5)


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
    for section in gap_results or []:
        for control_obj in section.get("controls") or []:
            for control_id, dp_rows in control_obj.items():
                for row in dp_rows or []:
                    dep_id = row.get("deployment_framework_control_id") or control_id
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


def _parse_report_data(package_data: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    gap_results = ((package_data.get("gapAnalysis") or {}).get("deployment_gap_results")) or []
    dp_data = _build_dp_data(gap_results)

    controls: list[dict[str, Any]] = []
    comparison_result = ((package_data.get("comparison") or {}).get("comparison_result")) or []

    for section in comparison_result:
        for ctrl in section.get("controls") or []:
            control_id = ctrl.get("deployment_framework_control_id") or ctrl.get("assigned_framework_control_id") or ""
            raw_score = ctrl.get("comparison_score") or 0
            score = round(raw_score * 100) if raw_score <= 1 else round(raw_score)

            impl, partial, not_impl = _count_from_dp_rows(dp_data.get(control_id, []))
            sim = _avg_sim(dp_data.get(control_id, []))

            controls.append(
                {
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
            )

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
    d = Drawing(180, 150)
    pie = Pie()
    pie.x = 40
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
    d.add(String(90, 5, center_label, fontSize=8, fillColor=_COLORS["mutedText"], textAnchor="middle"))
    legend_y = 130
    for label, value, color in chart_data:
        pct = (value / total * 100) if total else 0
        d.add(String(0, legend_y, "\u25a0", fillColor=color, fontSize=9))
        d.add(
            String(
                10,
                legend_y,
                f"{label}: {value} ({pct:.1f}%)",
                fontSize=7,
                fillColor=_COLORS["darkText"],
            )
        )
        legend_y -= 10
    return d


def _spider_drawing(controls: list[dict[str, Any]]) -> Drawing | None:
    if not controls:
        return None
    d = Drawing(480, 380)
    chart = SpiderChart()
    chart.x = 60
    chart.y = 30
    chart.width = 360
    chart.height = 320
    chart.data = [[c["score"] for c in controls]]
    chart.labels = [c["id"] for c in controls]
    chart.strands[0].strokeColor = _COLORS["primary"]
    chart.strands[0].fillColor = colors.Color(
        _COLORS["primary"].red, _COLORS["primary"].green, _COLORS["primary"].blue, alpha=0.15
    )
    chart.spokes.strokeColor = colors.HexColor("#e2e8f0")
    chart.spokes.strokeWidth = 0.5
    d.add(chart)
    return d


def generate_deployment_framework_report_pdf(framework: Any, package_data: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        topMargin=16 * mm,
        bottomMargin=12 * mm,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
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

    story.append(Paragraph("Deployment Framework Report", _H_TITLE))
    story.append(HRFlowable(width="100%", color=_COLORS["borderColor"], thickness=1, spaceAfter=6))

    badge_row = " &nbsp;&nbsp; ".join(
        [
            f"<font color='#1a73e8'><b>{fw_version}</b></font>",
            f"<font color='#b06000'><b>{str(package_data.get('type', 'pre-release')).title()}</b></font>",
            f"<font color='#137333'><b>v{package_data.get('packageVersion', '1.0.0')}</b></font>",
            f"<font color='#1a73e8'><b>{str(package_data.get('status', 'pending')).title()}</b></font>",
        ]
    )
    story.append(Paragraph(badge_row, _MUTED))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(fw_name, _H1))
    story.append(
        Paragraph(
            f"{fw_name} Deployment Framework Gap Analysis &amp; Compliance Audit Report "
            f"\u2014 Package v{package_data.get('packageVersion', '1.0.0')}, {package_data.get('trigger', '')}",
            _MUTED,
        )
    )

    expert_review = package_data.get("expertReview")
    if expert_review and expert_review.get("assignedExpert") and expert_review.get("status") not in (None, "pending"):
        expert = expert_review["assignedExpert"]
        story.append(Spacer(1, 4 * mm))
        story.append(
            Paragraph(
                f"<b>Expert Review:</b> {expert.get('name', '\u2014')} ({expert.get('email', '')}) "
                f"\u2014 {str(expert_review.get('status')).upper()}",
                _MUTED,
            )
        )
        if expert_review.get("comments"):
            story.append(Paragraph(f"\u201c{expert_review['comments']}\u201d", _SMALL_MUTED))

    story.append(PageBreak())

    documents = package_data.get("documents") or []
    if documents:
        story.append(Paragraph(f"File Information ({len(documents)} files)", _SECTION))
        rows = [["VERSION", "FILE NAME", "SIZE"]]
        for fv in documents:
            rows.append(
                [
                    f"v{fv.get('fileVersion', '1.0.0')}",
                    fv.get("originalFileName", "\u2014"),
                    _format_size(fv.get("fileSize")),
                ]
            )
        file_table = Table(rows, colWidths=[25 * mm, 180 * mm, 25 * mm], hAlign="LEFT")
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
    stat_style_val = ParagraphStyle("DFRStatVal", parent=_styles["Normal"], fontSize=14, fontName="Helvetica-Bold", textColor=_COLORS["primary"], alignment=1)
    stat_style_label = ParagraphStyle("DFRStatLabel", parent=_styles["Normal"], fontSize=7, textColor=_COLORS["mutedText"], alignment=1)
    stat_cells = [[Paragraph(v, stat_style_val)] for _, v in stats]
    stat_label_cells = [[Paragraph(l, stat_style_label)] for l, _ in stats]
    combined_rows = [[stat_cells[i][0] for i in range(len(stats))], [stat_label_cells[i][0] for i in range(len(stats))]]
    stat_table = Table(combined_rows, colWidths=[46 * mm] * len(stats), hAlign="LEFT")
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

    if total_dp > 0:
        impl_chart = _donut_drawing(
            [
                ("Implemented", total_impl, _COLORS["green"]),
                ("Partial", total_partial, _COLORS["accent"]),
                ("Not Impl.", total_not_impl, _COLORS["red"]),
            ],
            "Implementation",
        )
        story.append(impl_chart)
        story.append(Spacer(1, 4 * mm))

    spider = _spider_drawing(controls)
    if spider:
        story.append(Paragraph("Compliance Radar Analysis", _SECTION))
        story.append(
            Paragraph(
                f"Spider chart mapping all {total_compared} controls by achieved compliance score.",
                _SMALL_MUTED,
            )
        )
        story.append(spider)
        story.append(PageBreak())

    merge_doc = package_data.get("mergeDocument") or {}
    merge_sections = merge_doc.get("controls_data") or []
    if merge_sections:
        total_merge_controls = sum(len(s.get("controls") or []) for s in merge_sections)
        if total_merge_controls:
            story.append(Paragraph("Merge Extraction Details", _SECTION))
            for section in merge_sections:
                story.append(
                    Paragraph(
                        f"<b>{section.get('id', '')} - {section.get('name', 'Unnamed Section')}</b>",
                        ParagraphStyle("DFRMergeSection", parent=_styles["Normal"], fontSize=10, textColor=_COLORS["primary"]),
                    )
                )
                for ctrl in section.get("controls") or []:
                    story.append(
                        Paragraph(f"{ctrl.get('id', '')} - {ctrl.get('name', 'Unnamed Control')}", _SMALL_MUTED)
                    )
                    for dp in ctrl.get("deployment_points") or []:
                        story.append(Paragraph(f"\u2022 {dp.get('id', '')}: {dp.get('name', 'Unnamed DP')}", _SMALL_MUTED))
            story.append(Spacer(1, 4 * mm))

    if controls:
        story.append(Paragraph("Control Compliance Detail", _SECTION))
        rows = [["ID", "Control Name", "Score", "Match", "Impl", "Part", "Not"]]
        for c in controls:
            rows.append(
                [
                    c["assigned_id"] or c["id"],
                    c["name"],
                    f"{c['score']}%",
                    c["match"],
                    str(c["impl"]),
                    str(c["partial"]),
                    str(c["notImpl"]),
                ]
            )
        detail_table = Table(
            rows, colWidths=[22 * mm, 110 * mm, 18 * mm, 22 * mm, 12 * mm, 12 * mm, 12 * mm], hAlign="LEFT"
        )
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

    if total_dp > 0:
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
                    f"Assigned: [{ctrl['assigned_id'] or 'N/A'}] {ctrl['assigned_name'] or '\u2014'}<br/>"
                    f"Deployment: [{ctrl['deployment_id'] or 'N/A'}] {ctrl['deployment_name'] or '\u2014'}",
                    ParagraphStyle("DFRGapHeader", parent=_styles["Normal"], fontSize=8.5, textColor=_COLORS["primary"], backColor=_COLORS["primaryLight"], borderPadding=4),
                )
            )
            gap_rows = [["DP", "Assigned Point", "Matched Point", "Sim", "Status"]]
            for idx, gap in enumerate(gaps):
                gap_rows.append(
                    [
                        f"D{idx + 1}",
                        gap["clientDp"],
                        gap["matchedFp"] or "No matching deployment point",
                        f"{gap['sim']:.1f}%",
                        gap["status"],
                    ]
                )
            gap_table = Table(gap_rows, colWidths=[10 * mm, 95 * mm, 95 * mm, 15 * mm, 25 * mm], hAlign="LEFT")
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

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(_COLORS["lightText"])
        canvas.drawString(14 * mm, 6 * mm, "Generated by VORA Platform")
        canvas.drawRightString(doc_.pagesize[0] - 14 * mm, 6 * mm, f"Page {doc_.page}")
        if doc_.page > 1:
            canvas.setFont("Helvetica-Bold", 8)
            canvas.drawString(
                14 * mm,
                doc_.pagesize[1] - 10 * mm,
                f"{fw_name.upper()} - PACKAGE v{package_data.get('packageVersion', '1.0.0')}",
            )
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
