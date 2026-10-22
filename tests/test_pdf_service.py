import json

import pymupdf

from linguapdf.domain.models import Annotation
from linguapdf.services.pdf_service import PdfDocumentSession


def _make_pdf(path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "English lesson")
    document.save(path)
    document.close()


def test_sidecar_round_trip_and_export(tmp_path) -> None:
    pdf_path = tmp_path / "lesson.pdf"
    _make_pdf(pdf_path)
    session = PdfDocumentSession(pdf_path)
    session.add_annotation(Annotation(page=0, kind="highlight", rect=(60, 60, 170, 80)))
    session.add_annotation(
        Annotation(page=0, kind="text", rect=(80, 100, 250, 160), text="Review this phrase")
    )
    session.add_annotation(
        Annotation(page=0, kind="underline", rect=(60, 170, 180, 190), color="#4F46E5")
    )
    session.add_annotation(
        Annotation(page=0, kind="strike", rect=(60, 200, 180, 220), color="#E11D48")
    )

    sidecar = session.save_annotations()
    exported = session.export_annotated_pdf(tmp_path / "lesson.annotated.pdf")
    session.close()

    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert len(payload["annotations"]) == 4
    assert exported.exists()

    reopened = PdfDocumentSession(pdf_path)
    assert [item.kind for item in reopened.annotations] == [
        "highlight",
        "text",
        "underline",
        "strike",
    ]
    reopened.close()

