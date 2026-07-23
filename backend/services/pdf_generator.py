import io
import json
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect, String
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

    # Score Banner
    score = score_data.get("score", 0)
    risk_level = score_data.get("risk_level", "—")
    confidence = score_data.get("confidence", 0)

    score_table = Table(
        [[
            Paragraph(f"{score:.0f}", ParagraphStyle("ScoreNum", parent=styles["Normal"],
                fontSize=42, fontName="Helvetica-Bold", textColor=DARK, alignment=TA_CENTER)),
            Paragraph(f"Decision Score", ParagraphStyle("ScoreLbl", parent=styles["Normal"],
                fontSize=9, textColor=GRAY, alignment=TA_CENTER)),
            Paragraph(f"{risk_level} Risk", ParagraphStyle("RiskBadge", parent=styles["Normal"],
                fontSize=14, fontName="Helvetica-Bold",
                textColor=_risk_color(risk_level), alignment=TA_CENTER)),
            Paragraph(f"{confidence:.0f}%\nConfidence", ParagraphStyle("Conf", parent=styles["Normal"],
                fontSize=11, textColor=GRAY, alignment=TA_CENTER)),
        ]],
        colWidths=[2*inch, 2*inch, 2*inch, 2*inch]
    )
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("ROUNDEDCORNERS", [6]),
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
