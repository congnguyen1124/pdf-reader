from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from linguapdf.ui.i18n import tr


class TextPdfDialog(QDialog):
    def __init__(self, initial_title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("text_pdf_title"))
        self.resize(720, 620)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(10)

        heading = QLabel(tr("text_pdf_title"))
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)
        layout.addWidget(QLabel(tr("document_title")))

        self.title_input = QLineEdit(initial_title.replace("_", " ").title())
        layout.addWidget(self.title_input)
        layout.addWidget(QLabel(tr("document_content")))

        self.content_input = QPlainTextEdit()
        self.content_input.setPlaceholderText(tr("document_content_placeholder"))
        layout.addWidget(self.content_input, 1)

        self.error_label = QLabel()
        self.error_label.setObjectName("errorLabel")
        self.error_label.hide()
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        create_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        create_button.setText(tr("create_pdf"))
        create_button.setObjectName("primaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("cancel"))
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.content_input.setFocus()

    @property
    def document_title(self) -> str:
        return self.title_input.text().strip()

    @property
    def content(self) -> str:
        return self.content_input.toPlainText().strip()

    def _accept_if_valid(self) -> None:
        if not self.document_title or not self.content:
            self.error_label.setText(tr("content_required"))
            self.error_label.show()
            return
        self.accept()
