from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QToolButton, QWidget

from linguapdf.ui.i18n import tr


class PdfSearchBar(QWidget):
    query_changed = Signal(str)
    next_requested = Signal()
    previous_requested = Signal()
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pdfSearchBar")
        self.setVisible(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(6)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("pdfSearchInput")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(260)
        self.search_input.textChanged.connect(self.query_changed)
        self.search_input.returnPressed.connect(self.next_requested)
        layout.addWidget(self.search_input, 1)

        self.result_label = QLabel()
        self.result_label.setObjectName("searchResultLabel")
        self.result_label.setMinimumWidth(74)
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.result_label)

        self.previous_button = QToolButton()
        self.previous_button.setObjectName("searchNavButton")
        self.previous_button.setText("↑")
        self.previous_button.clicked.connect(self.previous_requested)
        layout.addWidget(self.previous_button)

        self.next_button = QToolButton()
        self.next_button.setObjectName("searchNavButton")
        self.next_button.setText("↓")
        self.next_button.clicked.connect(self.next_requested)
        layout.addWidget(self.next_button)

        self.close_button = QToolButton()
        self.close_button.setObjectName("searchCloseButton")
        self.close_button.setText("×")
        self.close_button.clicked.connect(self.close_requested)
        layout.addWidget(self.close_button)

        QShortcut(QKeySequence("Escape"), self, activated=self.close_requested)
        QShortcut(QKeySequence("Shift+Return"), self.search_input, activated=self.previous_requested)
        self.retranslate_ui()
        self.set_result(0, 0)

    def open_search(self) -> None:
        self.show()
        self.search_input.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.search_input.selectAll()

    def set_result(self, current: int, total: int) -> None:
        has_query = bool(self.search_input.text().strip())
        if not has_query:
            text = ""
        elif total:
            text = f"{current} / {total}"
        else:
            text = tr("search_no_results")
        self.result_label.setText(text)
        enabled = total > 0
        self.previous_button.setEnabled(enabled)
        self.next_button.setEnabled(enabled)

    def retranslate_ui(self) -> None:
        self.search_input.setPlaceholderText(tr("search_pdf_placeholder"))
        self.previous_button.setToolTip(tr("search_previous"))
        self.next_button.setToolTip(tr("search_next"))
        self.close_button.setToolTip(tr("close_search"))
