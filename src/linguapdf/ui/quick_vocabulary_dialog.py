from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from linguapdf.ui.i18n import tr


class QuickVocabularyDialog(QDialog):
    def __init__(self, english: str, parent=None):
        super().__init__(parent)
        self.english = " ".join(english.split())
        self.setWindowTitle(tr("quick_dialog_title"))
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(12)

        title = QLabel(tr("quick_dialog_heading"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        caption = QLabel("ENGLISH")
        caption.setObjectName("eyebrowLabelDark")
        layout.addWidget(caption)

        english_label = QLabel(self.english)
        english_label.setObjectName("englishPreview")
        english_label.setWordWrap(True)
        english_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(english_label)

        meaning_caption = QLabel(tr("meaning"))
        meaning_caption.setObjectName("eyebrowLabelDark")
        layout.addWidget(meaning_caption)

        self.meaning_input = QLineEdit()
        self.meaning_input.setPlaceholderText(tr("meaning_placeholder"))
        self.meaning_input.returnPressed.connect(self._accept_if_valid)
        layout.addWidget(self.meaning_input)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #BE123C;")
        self.error_label.hide()
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        save_button.setText(tr("add_vocabulary"))
        save_button.setObjectName("primaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("cancel"))
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self._accept_if_valid)
        layout.addWidget(buttons)
        self.meaning_input.setFocus()

    @property
    def vietnamese(self) -> str:
        return self.meaning_input.text().strip()

    def _accept_if_valid(self) -> None:
        if not self.vietnamese:
            self.error_label.setText(tr("meaning_required"))
            self.error_label.show()
            self.meaning_input.setFocus()
            return
        self.accept()
