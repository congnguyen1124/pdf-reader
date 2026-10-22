from __future__ import annotations

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from linguapdf.domain.vocabulary_parser import parse_vocabulary
from linguapdf.ui.i18n import tr


class VocabularyInputTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(7, 2, parent)
        self.setObjectName("vocabularyInputTable")
        self.setHorizontalHeaderLabels(["English", tr("vietnamese")])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setMinimumHeight(42)
        self.verticalHeader().setDefaultSectionSize(44)
        self.verticalHeader().setMinimumWidth(36)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QTableWidget.SelectionMode.ContiguousSelection)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.setTabKeyNavigation(True)
        self.setWordWrap(True)
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
        self.setWindowTitle(tr("bulk_dialog_title"))
        self.setObjectName("bulkImportDialog")
        self.resize(780, 620)
        self.setMinimumSize(660, 500)
        self._cards: list[tuple[str, str]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 22)
        layout.setSpacing(14)

        title = QLabel(tr("bulk_heading"))
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        help_box = QFrame()
        help_box.setObjectName("inputHelpBox")
        help_layout = QHBoxLayout(help_box)
        help_layout.setContentsMargins(12, 10, 12, 10)
        tip_icon = QLabel("⌘V")
        tip_icon.setObjectName("pasteBadge")
        help_layout.addWidget(tip_icon)
        help_text = QLabel(tr("bulk_help"))
        help_text.setObjectName("inputHelpText")
        help_text.setWordWrap(True)
        help_layout.addWidget(help_text, 1)
        layout.addWidget(help_box)

        column_hint = QHBoxLayout()
        english_hint = QLabel(tr("english_column_hint"))
        english_hint.setObjectName("columnHint")
        vietnamese_hint = QLabel(tr("vietnamese_column_hint"))
        vietnamese_hint.setObjectName("columnHint")
        column_hint.addWidget(english_hint, 1)
        column_hint.addWidget(vietnamese_hint, 1)
        layout.addLayout(column_hint)

        self.table = VocabularyInputTable()
        self.table.cellChanged.connect(self._table_changed)
        layout.addWidget(self.table, 1)

        tools_frame = QFrame()
        tools_frame.setObjectName("inputTools")
        tools = QHBoxLayout(tools_frame)
        tools.setContentsMargins(8, 7, 8, 7)
        tools.setSpacing(7)
        paste_shortcut = QKeySequence(QKeySequence.StandardKey.Paste).toString(
            QKeySequence.SequenceFormat.NativeText
        )
        self.paste_button = QPushButton(f"{paste_shortcut}  {tr('paste_clipboard')}")
        self.paste_button.setObjectName("softPrimaryButton")
        self.paste_button.clicked.connect(self.table.paste_clipboard)
        tools.addWidget(self.paste_button)
        self.add_rows_button = QPushButton(f"＋ {tr('add_rows')}")
        self.add_rows_button.clicked.connect(lambda: self._add_rows(5))
        tools.addWidget(self.add_rows_button)
        self.swap_button = QPushButton(f"⇄  {tr('swap_columns')}")
        self.swap_button.clicked.connect(self.table.swap_columns)
        tools.addWidget(self.swap_button)
        tools.addStretch()
        layout.addWidget(tools_frame)

        self.preview = QLabel(tr("no_data"))
        self.preview.setObjectName("importStatus")
        layout.addWidget(self.preview)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        self.save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        self.save_button.setText(tr("add_to_lesson"))
        self.save_button.setObjectName("primaryButton")
        self.save_button.setEnabled(False)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("cancel"))
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self._accept_if_valid)
        layout.addWidget(buttons)
        self.table.setCurrentCell(0, 0)
        self.table.setFocus()

    @property
    def cards(self) -> list[tuple[str, str]]:
        return self._cards

    def _add_rows(self, count: int) -> None:
        for _ in range(count):
            self.table.insertRow(self.table.rowCount())

    def _table_changed(self, *_args) -> None:
        self.table.ensure_empty_rows()
        cards, incomplete = self.table.cards()
        self.save_button.setEnabled(bool(cards) and not incomplete)
        self.preview.setStyleSheet("")
        if incomplete:
            self.preview.setText(tr("rows_need_attention", count=len(incomplete)))
            self.preview.setProperty("state", "warning")
        elif cards:
            self.preview.setText(tr("cards_ready", count=len(cards)))
            self.preview.setProperty("state", "ready")
        else:
            self.preview.setText(tr("no_data"))
            self.preview.setProperty("state", "empty")
        self.preview.style().unpolish(self.preview)
        self.preview.style().polish(self.preview)

    def _accept_if_valid(self) -> None:
        cards, incomplete = self.table.cards()
        if incomplete:
            first = incomplete[0]
            self.table.selectRow(first)
            target = self.table.item(first, 0) or self.table.item(first, 1)
            if target:
                self.table.scrollToItem(target)
            self.preview.setText(tr("incomplete_row", row=first + 1))
            self.preview.setProperty("state", "warning")
            return
        if not cards:
            self.preview.setText(tr("at_least_one_card"))
            self.preview.setProperty("state", "warning")
            return
        self._cards = cards
        self.accept()
