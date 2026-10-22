import pymupdf
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from linguapdf.domain.models import Annotation
from linguapdf.services.pdf_service import PdfDocumentSession
from linguapdf.ui.pdf_viewer import PdfViewer


def _viewer_with_text(tmp_path):
    pdf_path = tmp_path / "selection.pdf"
    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 100), "select these words", fontsize=14)
    document.save(pdf_path)
    document.close()

    app = QApplication.instance() or QApplication([])
    session = PdfDocumentSession(pdf_path)
    viewer = PdfViewer()
    viewer.resize(720, 640)
    viewer.set_document(session)
    viewer.show()
    app.processEvents()
    app.processEvents()
    return app, viewer, session


def test_cursor_changes_only_over_pdf_text(tmp_path) -> None:
    app, viewer, session = _viewer_with_text(tmp_path)
    layout = viewer._page_layouts[0]
    word = viewer._words_for_page(0)[0]
    word_scene = QPointF(
        layout.bounds.left() + (word[0] + word[2]) / 2 * viewer._render_scale,
        layout.bounds.top() + (word[1] + word[3]) / 2 * viewer._render_scale,
    )

    QTest.mouseMove(viewer.viewport(), viewer.mapFromScene(word_scene))
    app.processEvents()
    assert viewer.viewport().cursor().shape() == Qt.CursorShape.IBeamCursor

    empty_scene = QPointF(layout.bounds.center().x(), layout.bounds.bottom() - 40)
    QTest.mouseMove(viewer.viewport(), viewer.mapFromScene(empty_scene))
    app.processEvents()
    assert viewer.viewport().cursor().shape() == Qt.CursorShape.ArrowCursor
    viewer.close()
    session.close()
    app.processEvents()


def test_double_click_selects_one_word_and_drag_selection_is_blue(tmp_path) -> None:
    app, viewer, session = _viewer_with_text(tmp_path)
    layout = viewer._page_layouts[0]
    words = viewer._words_for_page(0)
    first = words[0]
    first_scene = QPointF(
        layout.bounds.left() + (first[0] + first[2]) / 2 * viewer._render_scale,
        layout.bounds.top() + (first[1] + first[3]) / 2 * viewer._render_scale,
    )
    captured = []
    viewer._show_selection_menu = lambda _page, result, _event: captured.append(result)

    QTest.mouseDClick(
        viewer.viewport(),
        Qt.MouseButton.LeftButton,
        pos=viewer.mapFromScene(first_scene),
    )
    app.processEvents()
    assert captured[-1].text == "select"
    assert viewer._temporary_selection_items

    viewer._clear_temporary_selection()
    last = words[-1]
    drag_rect = QRectF(
        layout.bounds.left() + first[0] * viewer._render_scale,
        layout.bounds.top() + first[1] * viewer._render_scale,
        (last[2] - first[0]) * viewer._render_scale,
        (last[3] - first[1]) * viewer._render_scale,
    )
    result = viewer._text_selection(layout, drag_rect, drag_rect.topLeft())
    viewer._show_temporary_selection(layout, result.rects)
    assert result.text == "select these words"
    assert viewer._temporary_selection_items

    viewer.close()
    session.close()
    app.processEvents()


def test_vertical_drag_follows_reading_order_and_trackpad_zoom_is_queued(tmp_path) -> None:
    pdf_path = tmp_path / "multiline.pdf"
    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 100), "one two three", fontsize=14)
    page.insert_text((72, 130), "four five six", fontsize=14)
    document.save(pdf_path)
    document.close()

    app = QApplication.instance() or QApplication([])
    session = PdfDocumentSession(pdf_path)
    viewer = PdfViewer()
    viewer.resize(720, 640)
    viewer.set_document(session)
    viewer.show()
    app.processEvents()
    app.processEvents()

    layout = viewer._page_layouts[0]
    words = viewer._words_for_page(0)

    def scene_center(word):
        return QPointF(
            layout.bounds.left() + (word[0] + word[2]) / 2 * viewer._render_scale,
            layout.bounds.top() + (word[1] + word[3]) / 2 * viewer._render_scale,
        )

    selection = viewer._selection_between(layout, scene_center(words[1]), scene_center(words[4]))
    assert selection.text == "two three four five"
    assert len(selection.rects) == 2

    original_zoom = viewer.zoom
    viewer._apply_gesture_zoom(1.08)
    assert viewer.zoom > original_zoom
    assert viewer._gesture_render_timer.isActive()
    viewer._gesture_render_timer.stop()

    viewer.close()
    session.close()
    app.processEvents()


def test_pdf_search_finds_all_pages_and_wraps_navigation(tmp_path) -> None:
    pdf_path = tmp_path / "search.pdf"
    document = pymupdf.open()
    first = document.new_page(width=595, height=842)
    first.insert_text((72, 100), "Search this lesson. Search again.", fontsize=14)
    second = document.new_page(width=595, height=842)
    second.insert_text((72, 100), "The last search result.", fontsize=14)
    document.save(pdf_path)
    document.close()

    app = QApplication.instance() or QApplication([])
    session = PdfDocumentSession(pdf_path)
    viewer = PdfViewer()
    viewer.resize(720, 640)
    viewer.set_document(session)
    viewer.show()
    app.processEvents()

    assert viewer.search_text("search") == (1, 3)
    assert len(viewer._search_items) == 3
    assert viewer.next_search_match() == (2, 3)
    assert viewer.next_search_match() == (3, 3)
    assert viewer.next_search_match() == (1, 3)
    assert viewer.previous_search_match() == (3, 3)
    assert viewer.search_text("missing") == (0, 0)

    viewer.close()
    session.close()
    app.processEvents()


def test_clicking_outside_selection_toolbar_clears_temporary_selection(tmp_path) -> None:
    app, viewer, session = _viewer_with_text(tmp_path)
    layout = viewer._page_layouts[0]
    first_word = viewer._words_for_page(0)[0]
    selection = viewer._selection_from_words([first_word])
    viewer._show_temporary_selection(layout, selection.rects)
    word_position = QPointF(
        layout.bounds.left() + first_word[0] * viewer._render_scale,
        layout.bounds.top() + first_word[1] * viewer._render_scale,
    )
    global_position = viewer.viewport().mapToGlobal(viewer.mapFromScene(word_position))
    viewer._open_selection_toolbar(0, selection, global_position)
    app.processEvents()

    assert viewer._selection_toolbar is not None
    assert viewer._temporary_selection_items
    outside_position = viewer.viewport().rect().bottomRight() - QPoint(8, 8)
    QTest.mouseClick(viewer.viewport(), Qt.MouseButton.LeftButton, pos=outside_position)
    app.processEvents()

    assert viewer._selection_toolbar is None
    assert not viewer._temporary_selection_items
    viewer.close()
    session.close()
    app.processEvents()


def test_note_height_tracks_content_instead_of_leaving_empty_space(tmp_path) -> None:
    app, viewer, session = _viewer_with_text(tmp_path)
    note = Annotation(
        page=0,
        kind="text",
        rect=(90, 145, 265, 175),
        text="Short note",
        font_size=14,
    )
    session.add_annotation(note)
    viewer.render_document()
    app.processEvents()
    item = viewer._note_items[note.id]
    one_line_height = item.rect().height()

    item.editor.setPlainText(
        "This is a deliberately longer note that wraps across several compact lines."
    )
    app.processEvents()
    wrapped_height = item.rect().height()
    assert wrapped_height > one_line_height

    item.editor.setPlainText("Short again")
    app.processEvents()
    assert item.rect().height() < wrapped_height
    assert item.rect().height() <= one_line_height + 1

    viewer.close()
    session.close()
    app.processEvents()
