from PySide6.QtWidgets import QApplication

from linguapdf.services.library_service import LibraryService
from linguapdf.ui.bulk_import_dialog import BulkImportDialog
from linguapdf.ui.vocabulary_panel import VocabularyPanel


def test_wrong_card_repeats_and_session_can_restart(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    library = LibraryService(tmp_path / "review.sqlite3")
    project = library.create_vocabulary_project("review_words")
    library.add_cards(project.id, [("persistent", "kiên trì")])

    panel = VocabularyPanel(library)
    panel.set_document(project.id, project.title)
    panel.review_scope.setCurrentIndex(1)
    panel.start_review()
    card_id = panel.current_card.id

    panel.reveal_answer()
    panel.rate_card(0)
    assert panel.review_attempts == 1
    assert panel.reviewed_count == 0
    assert panel.current_card.id == card_id

    panel.reveal_answer()
    panel.rate_card(3)
    assert panel.review_stack.currentIndex() == 2
    assert panel.reviewed_count == 1

    panel.restart_review()
    assert panel.review_stack.currentIndex() == 1
    assert panel.current_card.id == card_id
    panel.close()
    library.close()
    app.processEvents()


def test_bulk_input_status_and_save_state(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    dialog = BulkImportDialog()
    assert not dialog.save_button.isEnabled()

    dialog.table.setItem(0, 0, dialog.table.item(0, 0) or _item("careful"))
    app.processEvents()
    assert not dialog.save_button.isEnabled()

    dialog.table.setItem(0, 1, _item("cẩn thận"))
    app.processEvents()
    assert dialog.save_button.isEnabled()
    assert "1" in dialog.preview.text()
    dialog.close()


def _item(text: str):
    from PySide6.QtWidgets import QTableWidgetItem

    return QTableWidgetItem(text)
