"""
Renders the Report Agent's finished markdown report into a downloadable
PDF. This is a small, purpose-built parser for the specific markdown
subset report_agent.py actually produces (# / ## headers, **bold**,
`code`, and "- " bullet lines) - not a general markdown-to-PDF converter.
"""
import io
import re

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_CODE_RE = re.compile(r"`(.+?)`")


def _inline_to_reportlab(text: str) -> str:
    """
    Converts the handful of inline markdown styles the report actually
    uses into ReportLab's Paragraph XML markup. Escapes stray angle
    brackets/ampersands first so they can't be mistaken for markup.
    """
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = _BOLD_RE.sub(r"<b>\1</b>", text)
    text = _CODE_RE.sub(r"<font face='Courier'>\1</font>", text)
    return text


def markdown_report_to_pdf(markdown_text: str, title: str = "Research Report") -> bytes:
    """Returns PDF bytes for the given markdown report text."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        title=title,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    h1_style = ParagraphStyle(
        "ReportH1", parent=styles["Heading1"], spaceAfter=14, spaceBefore=4,
        textColor=HexColor("#3d3550"),
    )
    h2_style = ParagraphStyle(
        "ReportH2", parent=styles["Heading2"], spaceAfter=8, spaceBefore=16,
        textColor=HexColor("#6b5fc9"), fontSize=13,
    )
    body_style = ParagraphStyle("ReportBody", parent=styles["Normal"], spaceAfter=8, leading=15)
    bullet_style = ParagraphStyle("ReportBullet", parent=styles["Normal"], leading=14)

    story = []
    bullet_buffer = []

    def flush_bullets():
        if not bullet_buffer:
            return
        story.append(
            ListFlowable(
                [ListItem(Paragraph(_inline_to_reportlab(b), bullet_style)) for b in bullet_buffer],
                bulletType="bullet",
                leftIndent=18,
            )
        )
        story.append(Spacer(1, 8))
        bullet_buffer.clear()

    for raw_line in markdown_text.split("\n"):
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            flush_bullets()
            continue

        if stripped.startswith("# "):
            flush_bullets()
            story.append(Paragraph(_inline_to_reportlab(stripped[2:].strip()), h1_style))
        elif stripped.startswith("## "):
            flush_bullets()
            story.append(Paragraph(_inline_to_reportlab(stripped[3:].strip()), h2_style))
        elif stripped.startswith("- "):
            bullet_buffer.append(stripped[2:].strip())
        else:
            flush_bullets()
            story.append(Paragraph(_inline_to_reportlab(stripped), body_style))

    flush_bullets()
    doc.build(story)
    return buffer.getvalue()
