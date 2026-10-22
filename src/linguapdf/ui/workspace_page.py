from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from linguapdf.ui.i18n import tr


class WorkspacePage(QWidget):
    attach_pdf_requested = Signal()
    create_from_text_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("workspacePage")
        self.workspace_name = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(50, 50, 50, 50)
        root.addStretch()

        card = QFrame()
        card.setObjectName("workspaceCard")
        card.setMaximumWidth(720)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(38, 34, 38, 34)
        card_layout.setSpacing(12)

        self.name_label = QLabel()
        self.name_label.setObjectName("workspaceName")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.name_label)

        self.title_label = QLabel()
        self.title_label.setObjectName("workspaceTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.title_label)

        self.body_label = QLabel()
        self.body_label.setObjectName("mutedLabel")
        self.body_label.setWordWrap(True)
        self.body_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.body_label)

        choices = QHBoxLayout()
        choices.setSpacing(14)
        self.attach_button = QPushButton()
        self.attach_button.setObjectName("workspaceChoiceButton")
        self.attach_button.clicked.connect(self.attach_pdf_requested)
        choices.addWidget(self.attach_button)
        self.create_button = QPushButton()
        self.create_button.setObjectName("primaryButton")
        self.create_button.clicked.connect(self.create_from_text_requested)
        choices.addWidget(self.create_button)
        card_layout.addLayout(choices)

        self.attach_hint = QLabel()
        self.attach_hint.setObjectName("mutedLabel")
        self.attach_hint.setWordWrap(True)
        self.attach_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.attach_hint)
        self.create_hint = QLabel()
        self.create_hint.setObjectName("mutedLabel")
        self.create_hint.setWordWrap(True)
        self.create_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.create_hint)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(card)
        row.addStretch()
        root.addLayout(row)
        root.addStretch()
        self.retranslate_ui()

    def set_workspace(self, name: str) -> None:
        self.workspace_name = name
        self.name_label.setText(name)

    def retranslate_ui(self) -> None:
        self.title_label.setText(tr("workspace_ready_title"))
        self.body_label.setText(tr("workspace_ready_body"))
        self.attach_button.setText(f"PDF  {tr('attach_pdf')}")
        self.create_button.setText(f"T  {tr('create_from_text')}")
        self.attach_hint.setText(tr("attach_pdf_hint"))
        self.create_hint.setText(tr("create_text_hint"))
