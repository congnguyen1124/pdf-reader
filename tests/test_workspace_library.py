import sqlite3
from pathlib import Path

import pymupdf

from linguapdf.services.library_service import LibraryService, snake_case_name
from linguapdf.services.text_pdf_service import create_pdf_from_text


def test_existing_library_migrates_into_tree_root(tmp_path) -> None:
    database = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute(
        "CREATE TABLE documents(id TEXT PRIMARY KEY, path TEXT NOT NULL, "
        "title TEXT NOT NULL, last_opened TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT INTO documents VALUES ('legacy', '/lesson.pdf', 'Old lesson', 'now')"
    )
    connection.commit()
    connection.close()

    library = LibraryService(database)
    project = library.project("legacy")
    assert project is not None
    assert project.folder_id is None
    assert project.title == "Old lesson"
    library.close()


def test_nested_folders_and_snake_case_workspace_names(tmp_path) -> None:
    library = LibraryService(tmp_path / "data" / "library.sqlite3")
    lessons = library.create_folder("Bài học tiếng Anh")
    travel = library.create_folder("Travel Plans", lessons.id)
    first = library.create_vocabulary_project("Bài Học Du Lịch!", travel.id)
    second = library.create_vocabulary_project("Bài Học Du Lịch!", travel.id)

    assert lessons.name == "bai_hoc_tieng_anh"
    assert travel.name == "travel_plans"
    assert first.title == "bai_hoc_du_lich"
    assert second.title == "bai_hoc_du_lich_2"
    assert first.folder_id == travel.id
    assert not library.folder_is_empty(travel.id)
    assert not library.delete_folder(travel.id)

    library.move_project(first.id, None)
    assert library.project(first.id).folder_id is None
    assert snake_case_name("  Đọc & Viết Cơ Bản  ") == "doc_viet_co_ban"
    library.close()


def test_text_pdf_is_selectable_unicode_and_can_attach_to_workspace(tmp_path) -> None:
    library = LibraryService(tmp_path / "data" / "library.sqlite3")
    project = library.create_vocabulary_project("Reading Practice")
    destination = library.generated_pdf_path(project.id)
    assert destination.name == "reading_practice.pdf"
    paragraph = "Đây là bài học tiếng Anh có đầy đủ dấu. Vocabulary and reading practice."
    content = "\n\n".join(f"{index}. {paragraph} " * 8 for index in range(1, 24))

    result = create_pdf_from_text(destination, "Bài học đọc hiểu", content)
    attached = library.attach_generated_pdf(project.id, result)

    assert attached.kind == "pdf"
    assert Path(attached.path) == destination
    document = pymupdf.open(destination)
    assert document.page_count > 1
    assert document.metadata["title"] == "Bài học đọc hiểu"
    extracted = "".join(page.get_text() for page in document)
    assert "Đây là bài học tiếng Anh" in extracted
    assert f"{document.page_count} / {document.page_count}" in document[-1].get_text()
    document.close()
    library.close()
