from __future__ import annotations

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from linguapdf.domain.vocabulary_parser import parse_vocabulary


class VocabularyInputTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(12, 2, parent)
        self.setHorizontalHeaderLabels(["English", "Tiếng Việt"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().setDefaultSectionSize(38)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QTableWidget.SelectionMode.ContiguousSelection)
        self.setTabKeyNavigation(True)
        QShortcut(QKeySequence.StandardKey.Paste, self, activated=self.paste_clipboard)

    def paste_clipboard(self) -> None:
        text = QApplication.clipboard().text()
        if not text.strip():
            return
        start_row = max(self.currentRow(), 0)
        start_column = max(self.currentColumn(), 0)
        lines = [line for line in text.splitlines() if line.strip()]
        for row_offset, line in enumerate(lines):
            if "\t" in line:
                values = [value.strip() for value in line.split("\t")]
            else:
                cards, _errors = parse_vocabulary(line)
                values = list(cards[0]) if cards else [line.strip()]
            target_row = start_row + row_offset
            while target_row >= self.rowCount():
                self.insertRow(self.rowCount())
            for column_offset, value in enumerate(values[: 2 - start_column]):
                self.setItem(target_row, start_column + column_offset, QTableWidgetItem(value))
        self.ensure_empty_rows()

    def ensure_empty_rows(self, minimum: int = 3) -> None:
        trailing_empty = 0
        for row in range(self.rowCount() - 1, -1, -1):
            if any(self._cell(row, column) for column in range(2)):
                break
            trailing_empty += 1
        for _ in range(max(0, minimum - trailing_empty)):
            self.insertRow(self.rowCount())

    def cards(self) -> tuple[list[tuple[str, str]], list[int]]:
        cards: list[tuple[str, str]] = []
        incomplete_rows: list[int] = []
        for row in range(self.rowCount()):
            english = self._cell(row, 0)
            vietnamese = self._cell(row, 1)
            if not english and not vietnamese:
                continue
            if not english or not vietnamese:
                incomplete_rows.append(row)
            else:
                cards.append((english, vietnamese))
        return cards, incomplete_rows

    def swap_columns(self) -> None:
        for row in range(self.rowCount()):
            left = self.takeItem(row, 0)
            right = self.takeItem(row, 1)
            self.setItem(row, 0, right)
            self.setItem(row, 1, left)

    def _cell(self, row: int, column: int) -> str:
        item = self.item(row, column)
        return item.text().strip() if item else ""


class BulkImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thêm nhiều từ vựng")
        self.resize(720, 560)
        self._cards: list[tuple[str, str]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        title = QLabel("Nhập danh sách từ vựng")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        help_text = QLabel(
            "Nhập trực tiếp vào bảng hoặc dán 2 cột từ Excel/Google Sheets. "
            "Mỗi hàng sẽ trở thành một flashcard."
        )
        help_text.setObjectName("mutedLabel")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        self.table = VocabularyInputTable()
        self.table.cellChanged.connect(lambda: self.table.ensure_empty_rows())
        layout.addWidget(self.table, 1)

        tools = QHBoxLayout()
        add_rows = QPushButton("＋ Thêm 5 hàng")
        add_rows.clicked.connect(lambda: self._add_rows(5))
        tools.addWidget(add_rows)
        paste = QPushButton("Dán từ clipboard")
        paste.clicked.connect(self.table.paste_clipboard)
        tools.addWidget(paste)
        swap = QPushButton("⇄ Đổi hai cột")
        swap.clicked.connect(self.table.swap_columns)
        tools.addWidget(swap)
        tools.addStretch()
        layout.addLayout(tools)

        self.preview = QLabel("Chưa có dữ liệu")
        self.preview.setObjectName("mutedLabel")
        layout.addWidget(self.preview)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        save_button.setText("Thêm vào bài học")
        save_button.setObjectName("primaryButton")
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self._accept_if_valid)
        layout.addWidget(buttons)

    @property
    def cards(self) -> list[tuple[str, str]]:
        return self._cards

    def _add_rows(self, count: int) -> None:
        for _ in range(count):
            self.table.insertRow(self.table.rowCount())

    def _accept_if_valid(self) -> None:
        cards, incomplete = self.table.cards()
        if incomplete:
            first = incomplete[0]
            self.table.selectRow(first)
            target = self.table.item(first, 0) or self.table.item(first, 1)
            if target:
                self.table.scrollToItem(target)
            self.preview.setText(
                f"Hàng {first + 1} còn thiếu một cột. Hãy nhập đủ English và Tiếng Việt."
            )
            self.preview.setStyleSheet("color: #BE123C;")
            return
        if not cards:
            self.preview.setText("Hãy nhập ít nhất một cặp từ vựng.")
            self.preview.setStyleSheet("color: #BE123C;")
            return
        self._cards = cards
        self.accept()

