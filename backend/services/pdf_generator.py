import io
import json
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, Image as RLImage
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect, String, Wedge, Line, Polygon
from reportlab.graphics import renderPDF
from datetime import datetime

# Brand colors
ACCENT = colors.HexColor("#2563EB")   # Blue-600
ACCENT_LIGHT = colors.HexColor("#EFF6FF")
DARK = colors.HexColor("#1E293B")
GRAY = colors.HexColor("#64748B")
LIGHT_GRAY = colors.HexColor("#F1F5F9")
SUCCESS = colors.HexColor("#16A34A")
WARNING = colors.HexColor("#D97706")
DANGER = colors.HexColor("#DC2626")
WHITE = colors.white


def _risk_color(risk_level: str):
    if risk_level == "Low":
        return SUCCESS
    elif risk_level == "Medium":
        return WARNING
    return DANGER


# ── Chart helpers (server-side, no matplotlib dependency) ────────────────────

def _score_gauge_drawing(score: float, risk_level: str, width: int = 240, height: int = 130) -> Drawing:
    """Render a semicircle score gauge as a ReportLab Drawing (vector, no PNG).

    The gauge shows the score as a filled wedge from 180° (left) sweeping
    counter-clockwise to a degree proportional to the score. The numeric
    score sits in the center.
    """
    d = Drawing(width, height)

    cx = width // 2
    cy = 20
    r = (width - 40) // 2

    # Background semicircle track (light gray) — top half: 0° to 180°
    track = Wedge(cx, cy, r, 0, 180)
    track.strokeColor = colors.HexColor("#E2E8F0")
    track.strokeWidth = 14
    track.fillColor = None
    d.add(track)

    # Filled wedge — proportional to score.
    # Score 100 = full semicircle (180° sweep from 180° back to 0°).
    # ReportLab Wedge: startAngle=180, endAngle=180 - (score/100)*180
    # (going clockwise from 180° down to 0° as score goes 0→100)
    score_color = _risk_color(risk_level)
    fill_end_angle = 180 - (score / 100.0) * 180
    if score > 0:
        fill = Wedge(cx, cy, r, 180, fill_end_angle)
        fill.strokeColor = score_color
        fill.strokeWidth = 14
        fill.fillColor = None
        d.add(fill)

    # Score number (centered, slightly above center of circle)
    score_text = String(cx, 50, f"{score:.0f}",
                        textAnchor="middle", fontName="Helvetica-Bold",
                        fontSize=36, fillColor=DARK)
    d.add(score_text)

    # "/ 100" label
    label = String(cx, 32, "out of 100",
                   textAnchor="middle", fontName="Helvetica",
                   fontSize=10, fillColor=GRAY)
    d.add(label)

    # Risk badge below
    risk_text = String(cx, 12, f"{risk_level} Risk",
                       textAnchor="middle", fontName="Helvetica-Bold",
                       fontSize=11, fillColor=score_color)
    d.add(risk_text)

    return d


def _subscore_bars_drawing(sub_scores: Dict[str, float], width: int = 480, height: int = 140) -> Drawing:
    """Render 4 horizontal sub-score bars with weight labels.

    Each bar: [label] [bar fill proportional to value] [value]
    Color: green >=70, amber >=50, red <50.
    """
    d = Drawing(width, height)

    items = [
        ("Data Quality",    sub_scores.get("data_quality", 0),    0.35),
        ("Trend Stability", sub_scores.get("trend_stability", 0), 0.25),
        ("Risk Inverse",    sub_scores.get("risk_inverse", 0),    0.25),
        ("Opportunity (AI)", sub_scores.get("opportunity", 0),    0.15),
    ]

    label_w = 110
    bar_x = label_w + 10
    bar_max_w = width - bar_x - 60  # leave room for value text
    row_h = height // 4
    bar_h = 14

    for i, (label, value, weight) in enumerate(items):
        y = height - (i + 1) * row_h + row_h // 2

        # Label
        d.add(String(0, y + 2, label, fontName="Helvetica",
                     fontSize=10, fillColor=DARK))

        # Weight badge
        d.add(String(label_w - 5, y + 2, f"({int(weight * 100)}%)",
                     fontName="Helvetica", fontSize=8, fillColor=GRAY,
                     textAnchor="end"))

        # Bar background
        d.add(Rect(bar_x, y - bar_h // 2, bar_max_w, bar_h,
                   fillColor=colors.HexColor("#F1F5F9"),
                   strokeColor=None))

        # Bar fill
        fill_w = (value / 100.0) * bar_max_w
        bar_color = SUCCESS if value >= 70 else (WARNING if value >= 50 else DANGER)
        d.add(Rect(bar_x, y - bar_h // 2, fill_w, bar_h,
                   fillColor=bar_color, strokeColor=None))

        # Value text
        d.add(String(width - 5, y + 2, f"{value:.1f}",
                     fontName="Helvetica-Bold", fontSize=10, fillColor=DARK,
                     textAnchor="end"))

    return d


def _forecast_chart_png(column: str, historical: list, projected: list) -> Optional[bytes]:
    """Render the forecast chart as a PNG using matplotlib.

    Returns PNG bytes, or None if matplotlib isn't available or data is empty.
    Falls back gracefully — the PDF will just skip the chart.
    """
    if not historical or not projected:
        return None
    try:
        import matplotlib
        matplotlib.use("Agg")  # non-interactive backend
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm

        # Try to register a CJK-capable font for safety (column names may have unicode)
        try:
            fm.fontManager.addfont('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        except Exception:
            pass
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        fig, ax = plt.subplots(figsize=(7, 2.8), constrained_layout=True)

        hist_x = [p["index"] for p in historical]
        hist_y = [p["value"] for p in historical]
        proj_x = [p["index"] for p in projected]
        proj_y = [p["value"] for p in projected]
        lower = [p.get("lower", p["value"]) for p in projected]
        upper = [p.get("upper", p["value"]) for p in projected]

        # Historical line
        ax.plot(hist_x, hist_y, color="#2563EB", linewidth=2.5,
                marker="o", markersize=5, label="Historical")

        # Connect last historical to first projected
        if hist_x and proj_x:
            ax.plot([hist_x[-1], proj_x[0]], [hist_y[-1], proj_y[0]],
                    color="#7C3AED", linewidth=2, linestyle="--", alpha=0.5)

        # Projected line
        ax.plot(proj_x, proj_y, color="#7C3AED", linewidth=2.5,
                linestyle="--", marker="s", markersize=5, label="Projected")

        # CI band
        ax.fill_between(proj_x, lower, upper, color="#7C3AED", alpha=0.15, label="95% CI")

        ax.set_title(f"Trend Projection: {column}", fontsize=11, color="#1E293B", pad=8)
        ax.set_xlabel("Period", fontsize=9, color="#64748B")
        ax.set_ylabel("Value", fontsize=9, color="#64748B")
        ax.tick_params(axis="both", labelsize=8, colors="#64748B")
        ax.grid(True, linestyle="--", alpha=0.3, color="#CBD5E1")
        ax.legend(loc="best", fontsize=8, framealpha=0.9)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#CBD5E1")
        ax.spines["bottom"].set_color("#CBD5E1")

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches=None)
        plt.close(fig)
        return buf.getvalue()
    except Exception as e:
        print(f"[pdf_generator] Forecast chart render failed: {e}")
        return None


def generate_pdf_report(
    session_data: Dict[str, Any],
    filename: str = "decision_report.pdf"
) -> bytes:
    """
    Generate an executive PDF report using ReportLab.
    Returns PDF as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
        title="DecisionLens AI — Executive Report"
    )

    styles = getSampleStyleSheet()
    story = []

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=26,
        fontName="Helvetica-Bold",
        textColor=DARK,
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=GRAY,
        spaceAfter=4
    )
    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=14,
        fontName="Helvetica-Bold",
        textColor=DARK,
        spaceBefore=16,
        spaceAfter=8,
        borderPad=0
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        textColor=DARK,
        spaceAfter=6,
        leading=15
    )
    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=8,
        textColor=GRAY
    )

    score_data = session_data.get("score_data", {})
    summary_data = session_data.get("summary_data", {})
    profile_data = session_data.get("profile_data", {})
    cleaning_log = session_data.get("cleaning_log", [])
    whatif_data = session_data.get("whatif_data", None)
    dataset_name = session_data.get("filename", "Dataset")
    dataset_context = session_data.get("dataset_context", "general")
    time_to_insight_ms = session_data.get("time_to_insight_ms", None)

    # ── COVER ──────────────────────────────────────────────────────────────────

    # Header bar
    story.append(Paragraph("DecisionLens AI", ParagraphStyle(
        "Brand", parent=styles["Normal"], fontSize=11,
        textColor=ACCENT, fontName="Helvetica-Bold"
    )))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT))
    story.append(Spacer(1, 20))

    # Title
    story.append(Paragraph("Executive Decision Report", title_style))
    story.append(Paragraph(f"Dataset: {dataset_name}", subtitle_style))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        subtitle_style
    ))

    if time_to_insight_ms:
        secs = time_to_insight_ms / 1000
        story.append(Paragraph(
            f"Time to Insight: {secs:.1f}s",
            ParagraphStyle("TTI", parent=styles["Normal"], fontSize=10, textColor=ACCENT, fontName="Helvetica-Bold")
        ))

    story.append(Spacer(1, 24))

    # Score Banner — now with visual gauge + confidence + risk badge
    score = score_data.get("score", 0)
    risk_level = score_data.get("risk_level", "—")
    confidence = score_data.get("confidence", 0)

    # Use a 1x3 table: [gauge drawing] | [score details] | [confidence + TTI]
    gauge_drawing = _score_gauge_drawing(score, risk_level, width=200, height=120)

    score_details = []
    score_details.append(Paragraph("Decision Score", ParagraphStyle("ScoreLbl", parent=styles["Normal"],
        fontSize=10, textColor=GRAY, alignment=TA_CENTER, spaceAfter=4)))
    score_details.append(Paragraph(f"<b>{score:.1f}</b> / 100", ParagraphStyle("ScoreNum", parent=styles["Normal"],
        fontSize=22, fontName="Helvetica-Bold", textColor=DARK, alignment=TA_CENTER, spaceAfter=8)))
    score_details.append(Paragraph(
        f'<font color="#{_risk_color(risk_level).hexval()[2:]}"><b>{risk_level} Risk</b></font>',
        ParagraphStyle("RiskBadge", parent=styles["Normal"], fontSize=13,
            fontName="Helvetica-Bold", alignment=TA_CENTER)
    ))

    conf_html = f"<b>{confidence:.0f}%</b> Confidence"
    if time_to_insight_ms:
        secs = time_to_insight_ms / 1000
        conf_html += f"<br/><br/><b>{secs:.1f}s</b><br/><font size='8' color='#64748B'>Time to Insight</font>"
    conf_para = Paragraph(conf_html, ParagraphStyle("Conf", parent=styles["Normal"],
        fontSize=12, textColor=DARK, alignment=TA_CENTER))

    score_table = Table(
        [[gauge_drawing, score_details, conf_para]],
        colWidths=[2.4*inch, 2.0*inch, 1.8*inch]
    )
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 20))

    # ── EXECUTIVE SUMMARY ─────────────────────────────────────────────────────

    story.append(Paragraph("Executive Summary", h2_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0")))
    story.append(Spacer(1, 8))

    summary_text = summary_data.get("summary_text", "No summary available.")
    story.append(Paragraph(summary_text, body_style))

    # Key Findings
    key_findings = summary_data.get("key_findings", [])
    if key_findings:
        story.append(Spacer(1, 8))
        story.append(Paragraph("Key Findings", ParagraphStyle(
            "KFTitle", parent=styles["Normal"], fontSize=11,
            fontName="Helvetica-Bold", textColor=DARK, spaceAfter=6
        )))
        for finding in key_findings:
            story.append(Paragraph(f"• {finding}", body_style))

    story.append(Spacer(1, 12))

    # ── DECISION SCORE BREAKDOWN ───────────────────────────────────────────────

    story.append(Paragraph("Decision Score Breakdown", h2_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0")))
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "The Decision Score is a weighted composite of four sub-scores. "
        "Three are computed deterministically from data statistics; the Opportunity Score alone incorporates AI analysis.",
        ParagraphStyle("Note", parent=styles["Normal"], fontSize=9, textColor=GRAY, spaceAfter=10)
    ))

    sub_scores = score_data.get("sub_scores", {})
    breakdown_data = [
        ["Sub-Score", "Weight", "Value", "Contribution"],
        ["Data Quality", "35%", f"{sub_scores.get('data_quality', 0):.1f}", f"{0.35 * sub_scores.get('data_quality', 0):.1f}"],
        ["Trend Stability", "25%", f"{sub_scores.get('trend_stability', 0):.1f}", f"{0.25 * sub_scores.get('trend_stability', 0):.1f}"],
        ["Risk Inverse", "25%", f"{sub_scores.get('risk_inverse', 0):.1f}", f"{0.25 * sub_scores.get('risk_inverse', 0):.1f}"],
        ["Opportunity (AI)", "15%", f"{sub_scores.get('opportunity', 0):.1f}", f"{0.15 * sub_scores.get('opportunity', 0):.1f}"],
        ["TOTAL", "100%", "", f"{score:.1f}"],
    ]
    breakdown_table = Table(breakdown_data, colWidths=[2.5*inch, 1.2*inch, 1.2*inch, 1.5*inch])
    breakdown_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [WHITE, LIGHT_GRAY]),
        ("BACKGROUND", (0, -1), (-1, -1), DARK),
        ("TEXTCOLOR", (0, -1), (-1, -1), WHITE),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(breakdown_table)
    story.append(Spacer(1, 10))

    # Visual sub-score bars (vector drawing)
    sub_scores = score_data.get("sub_scores", {})
    bars_drawing = _subscore_bars_drawing(sub_scores, width=480, height=130)
    story.append(bars_drawing)
    story.append(Spacer(1, 16))

    # ── TOP PRIORITIES & RECOMMENDATIONS ──────────────────────────────────────

    top_priorities = score_data.get("top_priorities", [])
    recommendations = score_data.get("recommendations", [])

    if top_priorities:
        story.append(Paragraph("Top 3 Priorities", h2_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0")))
        story.append(Spacer(1, 8))
        for i, p in enumerate(top_priorities[:3], 1):
            impact = p.get("impact_tag", "")
            impact_color = SUCCESS if "High" in impact else (WARNING if "Medium" in impact else ACCENT)
            story.append(Paragraph(
                f"<b>{i}. {p.get('text', '')}</b> "
                f"<font color='#{impact_color.hexval()[2:] if hasattr(impact_color, 'hexval') else '2563EB'}'>({impact})</font>",
                body_style
            ))
            story.append(Paragraph(f"   {p.get('rationale', '')}", ParagraphStyle(
                "Rationale", parent=body_style, textColor=GRAY, fontSize=9
            )))
            story.append(Spacer(1, 4))

    if recommendations:
        story.append(Spacer(1, 8))
        story.append(Paragraph("Recommended Actions", h2_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0")))
        story.append(Spacer(1, 8))
        rec_data = [["Action", "Rationale", "Priority"]]
        for r in recommendations[:5]:
            rec_data.append([
                r.get("action", ""),
                r.get("rationale", ""),
                r.get("priority", "")
            ])
        rec_table = Table(rec_data, colWidths=[2.5*inch, 3*inch, 1*inch])
        rec_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("WORDWRAP", (0, 0), (-1, -1), True),
        ]))
        story.append(rec_table)

    # ── WHAT-IF SECTION ───────────────────────────────────────────────────────

    if whatif_data:
        story.append(Spacer(1, 16))
        story.append(Paragraph("Trend Projection — Scenario Simulation", h2_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0")))
        story.append(Spacer(1, 8))

        story.append(Paragraph(
            "⚠ This section presents a trend projection using scenario simulation math — NOT a forecast or prediction.",
            ParagraphStyle("Disclaimer", parent=styles["Normal"], fontSize=9, textColor=WARNING, spaceAfter=8)
        ))

        col = whatif_data.get("column", "")
        pct = whatif_data.get("pct_change", 0)
        old_s = whatif_data.get("old_score", {})
        new_s = whatif_data.get("new_score", {})

        story.append(Paragraph(
            f"Scenario: '{col}' adjusted by {pct:+.0f}%",
            ParagraphStyle("Scenario", parent=styles["Normal"], fontSize=11,
                fontName="Helvetica-Bold", textColor=DARK, spaceAfter=10)
        ))

        wi_data = [
            ["Metric", "Before", "After", "Change"],
            ["Decision Score", f"{old_s.get('score', 0):.1f}", f"{new_s.get('score', 0):.1f}",
             f"{new_s.get('score', 0) - old_s.get('score', 0):+.1f}"],
            ["Risk Level", old_s.get("risk_level", "—"), new_s.get("risk_level", "—"),
             "Changed" if old_s.get("risk_level") != new_s.get("risk_level") else "Unchanged"],
        ]
        wi_table = Table(wi_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        wi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(wi_table)
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            whatif_data.get("delta_explanation", ""),
            ParagraphStyle("Explanation", parent=body_style, textColor=GRAY)
        ))

        # Try to embed a forecast chart for the perturbed column (visual reinforcement)
        # We need to re-run forecast on the original column to get historical + projected.
        # Since session_data doesn't include forecast, we generate a simple chart from
        # the perturbed scenario_deltas if available.
        scenario_deltas = new_score_result = whatif_data.get("scenario_deltas", {}) or {}
        if scenario_deltas and scenario_deltas.get("column"):
            try:
                # Reconstruct a minimal forecast visualization using the scenario deltas
                # rather than calling forecast_series (which needs the df). This keeps the
                # PDF generator dependency-free.
                col_name = scenario_deltas.get("column", "")
                pct = scenario_deltas.get("pct_change", 0)
                opp_delta = scenario_deltas.get("opportunity_delta", 0)
                stab_pen = scenario_deltas.get("stability_penalty", 0)
                risk_pen = scenario_deltas.get("risk_penalty", 0)

                # Small bar chart showing the 3 lever deltas
                lever_drawing = Drawing(480, 100)
                levers = [
                    ("Opportunity Δ", opp_delta, "#2563EB"),
                    ("Stability Penalty", -stab_pen, "#D97706"),
                    ("Risk Penalty", -risk_pen, "#DC2626"),
                ]
                bar_y_base = 20
                bar_h = 30
                bar_w_unit = 2  # pixels per delta point
                center_x = 240

                for i, (label, val, color) in enumerate(levers):
                    y = bar_y_base + (2 - i) * (bar_h + 6)
                    # zero line
                    lever_drawing.add(Line(center_x, y - 5, center_x, y + bar_h + 5,
                                           strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.5))
                    # bar (positive=right, negative=left)
                    bar_len = abs(val) * bar_w_unit
                    if val >= 0:
                        lever_drawing.add(Rect(center_x, y, bar_len, bar_h,
                                               fillColor=colors.HexColor(color), strokeColor=None))
                    else:
                        lever_drawing.add(Rect(center_x - bar_len, y, bar_len, bar_h,
                                               fillColor=colors.HexColor(color), strokeColor=None))
                    # label
                    lever_drawing.add(String(5, y + bar_h // 2 - 3, label,
                                             fontName="Helvetica", fontSize=9, fillColor=DARK))
                    # value
                    lever_drawing.add(String(475, y + bar_h // 2 - 3,
                                             f"{val:+.1f}",
                                             fontName="Helvetica-Bold", fontSize=9,
                                             fillColor=DARK, textAnchor="end"))

                lever_drawing.add(String(center_x, 5, "← adverse    0    favorable →",
                                         fontName="Helvetica", fontSize=7,
                                         fillColor=GRAY, textAnchor="middle"))

                story.append(Spacer(1, 10))
                story.append(Paragraph(
                    f"Scenario Lever Breakdown: '{col_name}' {pct:+.0f}%",
                    ParagraphStyle("LeverTitle", parent=styles["Normal"], fontSize=10,
                                   fontName="Helvetica-Bold", textColor=DARK, spaceAfter=6)
                ))
                story.append(lever_drawing)
            except Exception as e:
                print(f"[pdf_generator] Lever chart render failed: {e}")

    # ── APPENDIX ──────────────────────────────────────────────────────────────

    story.append(Spacer(1, 16))
    story.append(Paragraph("Appendix: Data Profile", h2_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0")))
    story.append(Spacer(1, 8))

    profile_cols = profile_data.get("columns", [])
    if profile_cols:
        prof_data = [["Column", "Type", "Nulls %", "Mean", "Std", "Outliers"]]
        for c in profile_cols:
            prof_data.append([
                c["name"],
                c["dtype"],
                f"{c['nulls_pct']:.1f}%",
                f"{c.get('mean', '—'):.2f}" if c.get("mean") is not None else "—",
                f"{c.get('std', '—'):.2f}" if c.get("std") is not None else "—",
                str(c.get("outlier_count", 0))
            ])
        prof_table = Table(prof_data, colWidths=[1.8*inch, 0.9*inch, 0.8*inch, 0.9*inch, 0.9*inch, 0.9*inch])
        prof_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(prof_table)

    if cleaning_log:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Cleaning Log", ParagraphStyle(
            "CLTitle", parent=styles["Normal"], fontSize=10,
            fontName="Helvetica-Bold", textColor=DARK, spaceAfter=6
        )))
        for entry in cleaning_log:
            story.append(Paragraph(f"• {entry}", small_style))

    # Footer
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0")))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Generated by DecisionLens AI · Powered by Google Gemini · Mind_Mesh Team",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8, textColor=GRAY, alignment=TA_CENTER)
    ))

    doc.build(story)
    return buffer.getvalue()
