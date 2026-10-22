from pathlib import Path

import pymupdf

from linguapdf.services.library_service import LibraryService


def _make_pdf(path) -> None:
    document = pymupdf.open()
    document.new_page()
    document.save(path)
    document.close()


def test_cards_are_isolated_per_document(tmp_path) -> None:
    library = LibraryService(tmp_path / "library.sqlite3")
    library.register_document("one", "/lesson-one.pdf", "Lesson one")
    library.register_document("two", "/lesson-two.pdf", "Lesson two")

    added, skipped = library.add_cards("one", [("hello", "xin chào"), ("world", "thế giới")])
    library.add_cards("two", [("hello", "chào bạn")])

    assert (added, skipped) == (2, 0)
    assert len(library.cards_for_document("one")) == 2
    assert len(library.cards_for_document("two")) == 1
    library.close()


def test_duplicate_card_is_skipped(tmp_path) -> None:
    library = LibraryService(tmp_path / "library.sqlite3")
    library.register_document("doc", "/lesson.pdf", "Lesson")

    assert library.add_cards("doc", [("Book", "quyển sách")]) == (1, 0)
    assert library.add_cards("doc", [("book", "quyển sách")]) == (0, 1)
    library.close()


def test_pdf_and_vocabulary_only_projects(tmp_path) -> None:
    source = tmp_path / "source.pdf"
    _make_pdf(source)
    library = LibraryService(tmp_path / "data" / "library.sqlite3")

    pdf_project = library.import_pdf(source, "Imported lesson")
    vocabulary_project = library.create_vocabulary_project("Travel")
    library.add_cards(vocabulary_project.id, [("departure", "khởi hành")])

    assert pdf_project.kind == "pdf"
    assert pdf_project.path != str(source)
    assert tmp_path.joinpath("data", "pdfs").resolve() in Path(pdf_project.path).parents
    assert vocabulary_project.kind == "vocabulary"
    assert vocabulary_project.path == ""
    assert library.project(vocabulary_project.id).card_count == 1

    copied_pdf = Path(pdf_project.path)
    library.delete_project(pdf_project.id)
    assert not copied_pdf.exists()
    assert source.exists()
    library.close()

