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

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_library_tab(), "Từ vựng")
        self.tabs.addTab(self._build_review_tab(), "Ôn tập")
        root.addWidget(self.tabs)
        self.set_enabled_state(False)

    def _build_library_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        title = QLabel("Kho từ vựng")
        title.setObjectName("sectionTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        self.add_button = QPushButton("＋ Thêm hàng loạt")
        self.add_button.setObjectName("primaryButton")
        self.add_button.clicked.connect(self._show_bulk_import)
        title_row.addWidget(self.add_button)
        layout.addLayout(title_row)

        self.stats_label = QLabel("Mở một tài liệu để bắt đầu")
        self.stats_label.setObjectName("mutedLabel")
        layout.addWidget(self.stats_label)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Tìm theo tiếng Anh hoặc tiếng Việt…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        layout.addWidget(self.search)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["English", "Tiếng Việt", "Tiến độ"])
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
        self.delete_button = QPushButton("Xóa thẻ đã chọn")
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

        title = QLabel("Ôn tập thông minh")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        direction_row = QHBoxLayout()
        direction_row.addWidget(QLabel("Chiều ôn:"))
        self.direction = QComboBox()
        self.direction.addItem("English → Tiếng Việt", "en_vi")
        self.direction.addItem("Tiếng Việt → English", "vi_en")
        self.direction.addItem("Trộn hai chiều", "mixed")
        direction_row.addWidget(self.direction, 1)
        layout.addLayout(direction_row)

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
        message = QLabel("Ôn những thẻ đến hạn theo nhịp độ của riêng bạn.")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        message.setObjectName("mutedLabel")
        layout.addWidget(message)
        self.start_button = QPushButton("Bắt đầu phiên ôn")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self.start_review)
        layout.addWidget(self.start_button, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        return page

    def _build_review_card(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)
        self.progress_label = QLabel()
        self.progress_label.setObjectName("mutedLabel")
        layout.addWidget(self.progress_label)

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
        self.prompt_label.setStyleSheet("font-size: 26px; font-weight: 800; color: #0F172A;")
        card_layout.addWidget(self.prompt_label, 1)
        self.answer_label = QLabel()
        self.answer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.answer_label.setWordWrap(True)
        self.answer_label.setStyleSheet("font-size: 19px; color: #4338CA; font-weight: 650;")
        self.answer_label.hide()
        card_layout.addWidget(self.answer_label)
        self.reveal_button = QPushButton("Hiện đáp án   Space")
        self.reveal_button.setObjectName("primaryButton")
        self.reveal_button.clicked.connect(self.reveal_answer)
        card_layout.addWidget(self.reveal_button, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(card, 1)

        self.rating_row = QWidget()
        rating_layout = QHBoxLayout(self.rating_row)
        rating_layout.setContentsMargins(0, 0, 0, 0)
        for label, rating, color in (
            ("1  Học lại", 0, "#BE123C"),
            ("2  Khó", 2, "#B45309"),
            ("3  Tốt", 3, "#15803D"),
            ("4  Dễ", 4, "#0369A1"),
        ):
            button = QPushButton(label)
            button.setStyleSheet(f"color: {color};")
            button.clicked.connect(lambda _checked=False, value=rating: self.rate_card(value))
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
        back = QPushButton("Xem kho từ vựng")
        back.clicked.connect(lambda: self.tabs.setCurrentIndex(0))
        layout.addWidget(back, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        return page

    def set_document(self, document_id: str | None, title: str = "") -> None:
        self.document_id = document_id
        self.document_title = title
        self.set_enabled_state(bool(document_id))
        self.review_stack.setCurrentIndex(0)
        self.refresh()

    def set_enabled_state(self, enabled: bool) -> None:
        for widget in (self.add_button, self.search, self.table, self.delete_button, self.start_button):
            widget.setEnabled(enabled)

    def refresh(self) -> None:
        self.table.setRowCount(0)
        if not self.document_id:
            self.stats_label.setText("Mở một tài liệu để bắt đầu")
            return
        cards = self.library.cards_for_document(self.document_id, self.search.text())
        self.table.setRowCount(len(cards))
        for row_index, card in enumerate(cards):
            english = QTableWidgetItem(card.english)
            english.setData(Qt.ItemDataRole.UserRole, card.id)
            vietnamese = QTableWidgetItem(card.vietnamese)
            accuracy = round(card.correct / card.attempts * 100) if card.attempts else 0
            progress = QTableWidgetItem(
                f"{accuracy}%" if card.attempts else "Mới"
            )
            progress.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_index, 0, english)
            self.table.setItem(row_index, 1, vietnamese)
            self.table.setItem(row_index, 2, progress)
        stats = self.library.stats(self.document_id)
        self.stats_label.setText(
            f"{stats['total']} thẻ  •  {stats['due']} đến hạn  •  {stats['learning']} đang học"
        )

    def _show_bulk_import(self) -> None:
        if not self.document_id:
            return
        dialog = BulkImportDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        added, skipped = self.library.add_cards(self.document_id, dialog.cards)
        self.refresh()
        self.cards_changed.emit()
        message = f"Đã thêm {added} thẻ."
        if skipped:
            message += f" Bỏ qua {skipped} thẻ trùng."
        QMessageBox.information(self, "Đã cập nhật", message)

    def _delete_selected(self) -> None:
        ids = {
            int(self.table.item(index.row(), 0).data(Qt.ItemDataRole.UserRole))
            for index in self.table.selectionModel().selectedRows()
        }
        if not ids:
            return
        response = QMessageBox.question(
            self,
            "Xóa thẻ",
            f"Xóa {len(ids)} thẻ đã chọn và toàn bộ lịch sử ôn của chúng?",
        )
        if response == QMessageBox.StandardButton.Yes:
            self.library.delete_cards(ids)
            self.refresh()
            self.cards_changed.emit()

    def start_review(self) -> None:
        if not self.document_id:
            return
        self.review_cards = self.library.due_cards(self.document_id)
        if not self.review_cards:
            QMessageBox.information(
                self,
                "Đã hoàn tất",
                "Không có thẻ nào đến hạn. Hãy thêm từ mới hoặc quay lại sau nhé.",
            )
            return
        random.shuffle(self.review_cards)
        self.reviewed_count = 0
        self.review_stack.setCurrentIndex(1)
        self._show_next_card()

    def _show_next_card(self) -> None:
        if not self.review_cards:
            self.current_card = None
            self.done_label.setText(f"Bạn đã ôn xong {self.reviewed_count} thẻ hôm nay.")
            self.review_stack.setCurrentIndex(2)
            self.refresh()
            return
        self.current_card = self.review_cards.pop()
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
                "TIẾNG VIỆT",
            )
        self.prompt_language.setText(language)
        self.prompt_label.setText(prompt)
        self.answer_label.setText(answer)
        self.answer_label.hide()
        self.reveal_button.show()
        self.rating_row.hide()
        total = self.reviewed_count + len(self.review_cards) + 1
        self.progress_label.setText(f"Thẻ {self.reviewed_count + 1} / {total}")

    def reveal_answer(self) -> None:
        if self.review_stack.currentIndex() != 1 or not self.current_card:
            return
        self.answer_label.show()
        self.reveal_button.hide()
        self.rating_row.show()

    def rate_card(self, rating: int) -> None:
        if not self.current_card or not self.answer_label.isVisible():
            return
        self.library.record_review(self.current_card, self.current_card_direction, rating)
        self.reviewed_count += 1
        self._show_next_card()

