from __future__ import annotations

from html import escape
from pathlib import Path

import pymupdf

PAGE_RECT = pymupdf.paper_rect("a4")
CONTENT_RECT = pymupdf.Rect(64, 68, PAGE_RECT.width - 64, PAGE_RECT.height - 58)


def create_pdf_from_text(
    destination: str | Path,
    title: str,
    text: str,
) -> Path:
    """Create a selectable, multi-page A4 PDF with Unicode text."""
    clean_title = " ".join(title.split()).strip()
    clean_text = text.strip()
    if not clean_title:
        raise ValueError("A document title is required.")
    if not clean_text:
        raise ValueError("Enter some text before creating the PDF.")

    destination_path = Path(destination).expanduser().resolve()
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination_path.with_suffix(".creating.pdf")
    temporary_path.unlink(missing_ok=True)

    paragraphs = "".join(
        f"<p>{escape(paragraph).replace(chr(10), '<br>')}</p>"
        for paragraph in clean_text.split("\n\n")
        if paragraph.strip()
    )
    html = f"<article><h1>{escape(clean_title)}</h1>{paragraphs}</article>"
    css = """
        @page { size: a4; }
        body { font-family: sans-serif; color: #172033; }
        h1 { font-size: 25px; line-height: 1.22; margin: 0 0 24px 0; color: #111827; }
        p { font-size: 12px; line-height: 1.55; margin: 0 0 12px 0; }
    """

    writer = pymupdf.DocumentWriter(str(temporary_path))
    story = pymupdf.Story(html=html, user_css=css)
    more = True
    try:
        while more:
            device = writer.begin_page(PAGE_RECT)
            more, _filled = story.place(CONTENT_RECT)
            story.draw(device)
            writer.end_page()
    finally:
        writer.close()

    document = pymupdf.open(temporary_path)
    try:
        metadata = document.metadata or {}
        metadata.update({"title": clean_title, "producer": "LinguaPDF"})
        document.set_metadata(metadata)
        for index, page in enumerate(document):
            footer = f"{index + 1} / {document.page_count}"
            page.insert_textbox(
                pymupdf.Rect(
                    64, PAGE_RECT.height - 40, PAGE_RECT.width - 64, PAGE_RECT.height - 22
                ),
                footer,
                fontsize=8,
                color=(0.40, 0.45, 0.54),
                align=pymupdf.TEXT_ALIGN_RIGHT,
            )
        document.save(destination_path)
    finally:
        document.close()
        temporary_path.unlink(missing_ok=True)

    check = pymupdf.open(destination_path)
    try:
        if check.page_count < 1 or not check[0].get_text().strip():
            raise RuntimeError("The generated PDF could not be verified.")
    finally:
        check.close()
    return destination_path
