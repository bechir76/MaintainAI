"""Render the sample manuals in data/manuals/src/*.md to PDF.

Supports the small Markdown subset used by the sources: headings, paragraphs,
bullet and numbered lists, pipe tables, block notes (> ...), **bold**, explicit
page breaks (<!-- pagebreak -->) and hidden text (<!-- hidden: ... -->), which
is rendered as tiny white text to simulate content a reader would not notice.

Each page in the source must fit on one PDF page, so citations by page number
stay stable; the script fails if the page count does not match.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "manuals" / "src"
OUT = ROOT / "data" / "manuals"

styles = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9.5, leading=12.5)
H1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=16, spaceAfter=8)
H2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12.5, spaceBefore=8, spaceAfter=4)
H3 = ParagraphStyle("h3", parent=styles["Heading3"], fontSize=10.5, spaceBefore=6, spaceAfter=3)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8.5, leading=10.5, alignment=TA_LEFT)
NOTE = ParagraphStyle(
    "note",
    parent=BODY,
    backColor=colors.HexColor("#FFF4E5"),
    borderColor=colors.HexColor("#E8A33D"),
    borderWidth=0.6,
    borderPadding=5,
    spaceBefore=6,
    spaceAfter=6,
)
HIDDEN = ParagraphStyle("hidden", parent=BODY, fontSize=1, leading=1.2, textColor=colors.white)


def inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)


def split_front_matter(raw: str) -> tuple[dict[str, Any], str]:
    _, fm, body = raw.split("---", 2)
    return yaml.safe_load(fm), body


def build_table(rows: list[list[str]]) -> Table:
    data = [[Paragraph(inline(c), CELL) for c in row] for row in rows]
    data[0] = [Paragraph(f"<b>{inline(c)}</b>", CELL) for c in rows[0]]
    table = Table(data, repeatRows=1, hAlign="LEFT", colWidths=None)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EDF3")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9AA5B1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return table


def parse(body: str) -> tuple[list[Any], int]:
    story: list[Any] = []
    pages = 1
    lines = body.strip().splitlines()
    i = 0
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            story.append(Paragraph(inline(" ".join(paragraph)), BODY))
            paragraph.clear()

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
        if not stripped:
            flush()
            i += 1
            continue
        if stripped == "<!-- pagebreak -->":
            flush()
            story.append(PageBreak())
            pages += 1
            i += 1
            continue
        hidden = re.match(r"<!-- hidden: (.+) -->", stripped)
        if hidden:
            flush()
            story.append(Paragraph(inline(hidden.group(1)), HIDDEN))
            i += 1
            continue
        heading = re.match(r"(#{1,3}) (.+)", stripped)
        if heading:
            flush()
            style = {1: H1, 2: H2, 3: H3}[len(heading.group(1))]
            story.append(Paragraph(inline(heading.group(2)), style))
            i += 1
            continue
        if stripped.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"-+", c) for c in cells):
                    rows.append(cells)
                i += 1
            story.extend([build_table(rows), Spacer(1, 6)])
            continue
        if re.match(r"(- |\d+\. )", stripped):
            flush()
            numbered = stripped[0].isdigit()
            items = []
            while i < len(lines) and re.match(r"(- |\d+\. )", lines[i].strip()):
                text = re.sub(r"^(- |\d+\. )", "", lines[i].strip())
                items.append(ListItem(Paragraph(inline(text), BODY), leftIndent=14))
                i += 1
            story.append(
                ListFlowable(
                    items,
                    bulletType="1" if numbered else "bullet",
                    start="1" if numbered else None,
                    leftIndent=14,
                    bulletFontSize=8 if not numbered else 9.5,
                )
            )
            continue
        if stripped.startswith(">"):
            flush()
            story.append(KeepTogether([Paragraph(inline(stripped.lstrip("> ")), NOTE)]))
            i += 1
            continue
        paragraph.append(stripped)
        i += 1
    flush()
    return story, pages


def render(md_path: Path) -> dict[str, Any]:
    meta, body = split_front_matter(md_path.read_text(encoding="utf-8"))
    story, expected_pages = parse(body)
    out = OUT / meta["filename"]

    def decorate(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#5A6672"))
        canvas.drawString(18 * mm, A4[1] - 12 * mm, f"{meta['doc_id']}  |  {meta['title']}")
        canvas.drawString(18 * mm, 10 * mm, f"{meta['revision']}  |  Sample document")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=meta["title"],
        author="MaintainAI sample data",
        subject=meta["doc_id"],
    )
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)

    # Re-save through pypdf for a clean header and consistent metadata.
    writer = PdfWriter(clone_from=out)
    writer.add_metadata(
        {
            "/Title": meta["title"],
            "/Subject": meta["doc_id"],
            "/Author": "MaintainAI sample data",
            "/Creator": "MaintainAI build_manuals.py",
            "/Producer": "MaintainAI build_manuals.py",
        }
    )
    writer.write(out)

    actual = len(PdfReader(out).pages)
    if actual != expected_pages:
        raise SystemExit(f"{md_path.name}: expected {expected_pages} pages, rendered {actual}")
    return {
        "file": meta["filename"],
        "doc_id": meta["doc_id"],
        "title": meta["title"],
        "machine_type": meta["machine_type"],
        "access_level": meta["access_level"],
        "pages": actual,
    }


def main() -> None:
    entries = [render(p) for p in sorted(SRC.glob("*.md"))]
    manifest = OUT / "manifest.yaml"
    header = "# Built by scripts/build_manuals.py from data/manuals/src\n"
    manifest.write_text(header + yaml.safe_dump({"documents": entries}, sort_keys=False))
    for e in entries:
        print(f"{e['file']:<55} {e['pages']} pages  [{e['machine_type']}, {e['access_level']}]")


if __name__ == "__main__":
    sys.exit(main())
