from __future__ import annotations

import random

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from linguapdf.domain.models import VocabularyCard
from linguapdf.services.library_service import LibraryService
from linguapdf.ui.bulk_import_dialog import BulkImportDialog
from linguapdf.ui.i18n import tr
from linguapdf.ui.quick_vocabulary_dialog import QuickVocabularyDialog


class VocabularyPanel(QWidget):
    cards_changed = Signal()

    def __init__(self, library: LibraryService, parent=None):
        super().__init__(parent)
        self.library = library
        self.document_id: str | None = None
        self.document_title = ""
        self.review_cards: list[VocabularyCard] = []
        self.current_card: VocabularyCard | None = None
        self.reviewed_count = 0
        self.review_attempts = 0
        self._session_card_ids: list[int] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_library_tab(), "")
        self.tabs.addTab(self._build_review_tab(), "")
        root.addWidget(self.tabs)
        self.set_enabled_state(False)
        self.retranslate_ui()

    def _build_library_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        self.library_title = QLabel()
        self.library_title.setObjectName("sectionTitle")
        title_row.addWidget(self.library_title)
        title_row.addStretch()
        self.add_button = QPushButton()
        self.add_button.setObjectName("primaryButton")
        self.add_button.clicked.connect(self._show_bulk_import)
        title_row.addWidget(self.add_button)
        layout.addLayout(title_row)

        self.stats_label = QLabel()
        self.stats_label.setObjectName("mutedLabel")
        layout.addWidget(self.stats_label)

        self.search = QLineEdit()
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        layout.addWidget(self.search)

        self.table = QTableWidget(0, 3)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        self.delete_button = QPushButton()
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.clicked.connect(self._delete_selected)
        footer.addWidget(self.delete_button)
        layout.addLayout(footer)
        return page

    def _build_review_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        self.review_title = QLabel()
        self.review_title.setObjectName("sectionTitle")
        layout.addWidget(self.review_title)

        direction_row = QHBoxLayout()
        self.direction_label = QLabel()
        direction_row.addWidget(self.direction_label)
        self.direction = QComboBox()
        self.direction.addItem("", "en_vi")
        self.direction.addItem("", "vi_en")
        self.direction.addItem("", "mixed")
        direction_row.addWidget(self.direction, 1)
        layout.addLayout(direction_row)

        scope_row = QHBoxLayout()
        self.scope_label = QLabel()
        scope_row.addWidget(self.scope_label)
        self.review_scope = QComboBox()
        self.review_scope.addItem("", "due")
        self.review_scope.addItem("", "all")
        scope_row.addWidget(self.review_scope, 1)
        layout.addLayout(scope_row)

        self.review_stack = QStackedWidget()
        self.review_stack.addWidget(self._build_review_empty())
        self.review_stack.addWidget(self._build_review_card())
        self.review_stack.addWidget(self._build_review_done())
        layout.addWidget(self.review_stack, 1)
        return page

    def _build_review_empty(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch()
        self.review_message = QLabel()
        self.review_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.review_message.setWordWrap(True)
        self.review_message.setObjectName("mutedLabel")
        layout.addWidget(self.review_message)
        self.start_button = QPushButton()
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self.start_review)
        layout.addWidget(self.start_button, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        return page

    def _build_review_card(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)
        progress_row = QHBoxLayout()
        self.progress_label = QLabel()
        self.progress_label.setObjectName("mutedLabel")
        progress_row.addWidget(self.progress_label)
        progress_row.addStretch()
        self.restart_button = QPushButton()
        self.restart_button.setObjectName("compactButton")
        self.restart_button.clicked.connect(self.restart_review)
        progress_row.addWidget(self.restart_button)
        layout.addLayout(progress_row)

        card = QFrame()
        card.setObjectName("reviewCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 32, 22, 28)
        card_layout.setSpacing(16)
        self.prompt_language = QLabel()
        self.prompt_language.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prompt_language.setObjectName("mutedLabel")
        card_layout.addWidget(self.prompt_language)
        self.prompt_label = QLabel()
        self.prompt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prompt_label.setWordWrap(True)
        self.prompt_label.setObjectName("reviewPrompt")
        card_layout.addWidget(self.prompt_label, 1)
        self.answer_label = QLabel()
        self.answer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.answer_label.setWordWrap(True)
        self.answer_label.setObjectName("reviewAnswer")
        self.answer_label.hide()
        card_layout.addWidget(self.answer_label)
        self.reveal_button = QPushButton()
        self.reveal_button.setObjectName("primaryButton")
        self.reveal_button.clicked.connect(self.reveal_answer)
        card_layout.addWidget(self.reveal_button, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(card, 1)

        self.rating_row = QWidget()
        rating_layout = QHBoxLayout(self.rating_row)
        rating_layout.setContentsMargins(0, 0, 0, 0)
        self.rating_buttons = []
        for key, rating, color in (
            ("again", 0, "#BE123C"),
            ("hard", 2, "#B45309"),
            ("good", 3, "#15803D"),
            ("easy", 4, "#0369A1"),
        ):
            button = QPushButton()
            button.setStyleSheet(f"color: {color};")
            button.clicked.connect(lambda _checked=False, value=rating: self.rate_card(value))
            self.rating_buttons.append((button, key))
            rating_layout.addWidget(button)
        self.rating_row.hide()
        layout.addWidget(self.rating_row)

        QShortcut(QKeySequence("Space"), page, activated=self.reveal_answer)
        for key, rating in (("1", 0), ("2", 2), ("3", 3), ("4", 4)):
            QShortcut(QKeySequence(key), page, activated=lambda value=rating: self.rate_card(value))
        return page

    def _build_review_done(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch()
        done = QLabel("✓")
        done.setAlignment(Qt.AlignmentFlag.AlignCenter)
        done.setStyleSheet("font-size: 54px; color: #16A34A; font-weight: 800;")
        layout.addWidget(done)
        self.done_label = QLabel()
        self.done_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.done_label.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(self.done_label)
        self.repeat_button = QPushButton()
        self.repeat_button.setObjectName("primaryButton")
        self.repeat_button.clicked.connect(self.restart_review)
        layout.addWidget(self.repeat_button, 0, Qt.AlignmentFlag.AlignCenter)
        self.review_all_button = QPushButton()
        self.review_all_button.clicked.connect(self.start_review_all)
        layout.addWidget(self.review_all_button, 0, Qt.AlignmentFlag.AlignCenter)
        self.back_button = QPushButton()
        self.back_button.clicked.connect(lambda: self.tabs.setCurrentIndex(0))
        layout.addWidget(self.back_button, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        return page

    def set_document(self, document_id: str | None, title: str = "") -> None:
        self.document_id = document_id
        self.document_title = title
        self.set_enabled_state(bool(document_id))
        self.review_stack.setCurrentIndex(0)
        self.refresh()

    def retranslate_ui(self) -> None:
        self.tabs.setTabText(0, tr("vocabulary_tab"))
        self.tabs.setTabText(1, tr("review_tab"))
        self.library_title.setText(tr("vocabulary_library"))
        self.add_button.setText(f"+ {tr('bulk_add')}")
        self.search.setPlaceholderText(tr("search_vocabulary"))
        self.table.setHorizontalHeaderLabels(["English", tr("vietnamese"), tr("progress")])
        self.delete_button.setText(tr("delete_cards"))
        self.review_title.setText(tr("smart_review"))
        self.direction_label.setText(tr("review_direction"))
        for index, key in enumerate(("en_to_vi", "vi_to_en", "mixed")):
            self.direction.setItemText(index, tr(key))
        self.scope_label.setText(tr("review_scope"))
        self.review_scope.setItemText(0, tr("due_cards"))
        self.review_scope.setItemText(1, tr("all_cards"))
        self.review_message.setText(tr("review_hint"))
        self.start_button.setText(tr("start_review"))
        self.reveal_button.setText(tr("reveal_answer"))
        for button, key in self.rating_buttons:
            button.setText(tr(key))
        self.restart_button.setText(tr("restart_review"))
        self.repeat_button.setText(tr("review_same_set"))
        self.review_all_button.setText(tr("review_all_from_start"))
        self.back_button.setText(tr("view_vocabulary"))
        self.refresh()

    def set_enabled_state(self, enabled: bool) -> None:
        for widget in (
            self.add_button,
            self.search,
            self.table,
            self.delete_button,
            self.start_button,
            self.review_scope,
        ):
            widget.setEnabled(enabled)

    def refresh(self) -> None:
        self.table.setRowCount(0)
        if not self.document_id:
            self.stats_label.setText(tr("open_to_begin"))
            return
        cards = self.library.cards_for_document(self.document_id, self.search.text())
        self.table.setRowCount(len(cards))
        for row_index, card in enumerate(cards):
            english = QTableWidgetItem(card.english)
            english.setData(Qt.ItemDataRole.UserRole, card.id)
            vietnamese = QTableWidgetItem(card.vietnamese)
            accuracy = round(card.correct / card.attempts * 100) if card.attempts else 0
            progress = QTableWidgetItem(f"{accuracy}%" if card.attempts else tr("new_card"))
            progress.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_index, 0, english)
            self.table.setItem(row_index, 1, vietnamese)
            self.table.setItem(row_index, 2, progress)
        stats = self.library.stats(self.document_id)
        self.stats_label.setText(tr("stats", **stats))

    def add_quick_vocabulary(self, english: str) -> None:
        if not self.document_id or not english.strip():
            return
        dialog = QuickVocabularyDialog(english, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        added, skipped = self.library.add_cards(
            self.document_id, [(dialog.english, dialog.vietnamese)]
        )
        self.tabs.setCurrentIndex(0)
        self.refresh()
        self.cards_changed.emit()
        if skipped:
            QMessageBox.information(
                self,
                tr("duplicate_title"),
                tr("duplicate_card"),
            )
        elif added:
            self.stats_label.setText(tr("quick_added", word=dialog.english))

    def _show_bulk_import(self) -> None:
        if not self.document_id:
            return
        dialog = BulkImportDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        added, skipped = self.library.add_cards(self.document_id, dialog.cards)
        self.refresh()
        self.cards_changed.emit()
        message = tr("cards_added", count=added)
        if skipped:
            message += tr("cards_skipped", count=skipped)
        QMessageBox.information(self, tr("updated"), message)

    def _delete_selected(self) -> None:
        ids = {
            int(self.table.item(index.row(), 0).data(Qt.ItemDataRole.UserRole))
            for index in self.table.selectionModel().selectedRows()
        }
        if not ids:
            return
        response = QMessageBox.question(
            self,
            tr("delete_cards_title"),
            tr("delete_cards_question", count=len(ids)),
        )
        if response == QMessageBox.StandardButton.Yes:
            self.library.delete_cards(ids)
            self.refresh()
            self.cards_changed.emit()

    def start_review(self) -> None:
        if not self.document_id:
            return
        if self.review_scope.currentData() == "all":
            cards = self.library.cards_for_document(self.document_id)
        else:
            cards = self.library.due_cards(self.document_id)
        if not cards:
            QMessageBox.information(
                self,
                tr("no_due_title"),
                tr("no_due"),
            )
            return
        random.shuffle(cards)
        self._begin_review(cards, remember_order=True)

    def start_review_all(self) -> None:
        self.review_scope.setCurrentIndex(1)
        self.start_review()

    def restart_review(self) -> None:
        if not self.document_id or not self._session_card_ids:
            self.start_review()
            return
        cards_by_id = {
            card.id: card for card in self.library.cards_for_document(self.document_id)
        }
        cards = [cards_by_id[card_id] for card_id in self._session_card_ids if card_id in cards_by_id]
        if cards:
            self._begin_review(cards, remember_order=False)

    def _begin_review(self, cards: list[VocabularyCard], *, remember_order: bool) -> None:
        self.review_cards = list(cards)
        if remember_order:
            self._session_card_ids = [card.id for card in cards]
        self.reviewed_count = 0
        self.review_attempts = 0
        self.review_stack.setCurrentIndex(1)
        self._show_next_card()

    def _show_next_card(self) -> None:
        if not self.review_cards:
            self.current_card = None
            self.done_label.setText(tr("review_done", count=self.reviewed_count))
            self.review_stack.setCurrentIndex(2)
            self.refresh()
            return
        self.current_card = self.review_cards.pop(0)
        direction = self.direction.currentData()
        if direction == "mixed":
            direction = random.choice(("en_vi", "vi_en"))
        self.current_card_direction = direction
        if direction == "en_vi":
            prompt, answer, language = (
                self.current_card.english,
                self.current_card.vietnamese,
                "ENGLISH",
            )
        else:
            prompt, answer, language = (
                self.current_card.vietnamese,
                self.current_card.english,
                tr("vietnamese").upper(),
            )
        self.prompt_language.setText(language)
        self.prompt_label.setText(prompt)
        self.answer_label.setText(answer)
        self.answer_label.hide()
        self.reveal_button.show()
        self.rating_row.hide()
        self.progress_label.setText(
            tr(
                "review_remaining",
                remaining=len(self.review_cards) + 1,
                attempts=self.review_attempts,
            )
        )

    def reveal_answer(self) -> None:
        if self.review_stack.currentIndex() != 1 or not self.current_card:
            return
        self.answer_label.show()
        self.reveal_button.hide()
        self.rating_row.show()

    def rate_card(self, rating: int) -> None:
        if not self.current_card or self.answer_label.isHidden():
            return
        updated = self.library.record_review(
            self.current_card, self.current_card_direction, rating
        )
        self.review_attempts += 1
        if rating == 0:
            self.review_cards.append(updated)
        else:
            self.reviewed_count += 1
        self._show_next_card()
