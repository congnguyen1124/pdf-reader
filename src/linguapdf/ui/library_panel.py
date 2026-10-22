from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from linguapdf.domain.models import StudyProject


class ProjectLibraryPanel(QWidget):
    project_selected = Signal(str)
    import_requested = Signal()
    create_requested = Signal()
    delete_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("libraryPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(230)
        self.setMaximumWidth(330)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 18, 16, 14)
        layout.setSpacing(12)

        brand = QLabel("LinguaPDF")
        brand.setObjectName("brandLabel")
        layout.addWidget(brand)
        subtitle = QLabel("THƯ VIỆN BÀI HỌC")
        subtitle.setObjectName("eyebrowLabel")
        layout.addWidget(subtitle)

        import_button = QPushButton("＋  Nhập PDF")
        import_button.setObjectName("primaryButton")
        import_button.clicked.connect(self.import_requested)
        layout.addWidget(import_button)

        create_button = QPushButton("✦  Bộ từ vựng mới")
        create_button.clicked.connect(self.create_requested)
        layout.addWidget(create_button)

        self.list = QListWidget()
        self.list.setObjectName("projectList")
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setSpacing(4)
        self.list.currentItemChanged.connect(self._selection_changed)
        layout.addWidget(self.list, 1)

        footer = QHBoxLayout()
        self.count_label = QLabel("0 tài liệu")
        self.count_label.setObjectName("mutedLabel")
        footer.addWidget(self.count_label)
        footer.addStretch()
        self.delete_button = QPushButton("Xóa")
        self.delete_button.setObjectName("smallDangerButton")
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self._delete_current)
        footer.addWidget(self.delete_button)
        layout.addLayout(footer)

    def set_projects(self, projects: list[StudyProject], selected_id: str | None = None) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        selected_item: QListWidgetItem | None = None
        for project in projects:
            kind = "PDF" if project.kind == "pdf" else "FLASHCARDS"
            suffix = f"{kind}  •  {project.card_count} từ"
            item = QListWidgetItem(f"{project.title}\n{suffix}")
            item.setData(Qt.ItemDataRole.UserRole, project.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, project.kind)
            item.setToolTip(project.path if project.path else "Bộ từ vựng không có PDF")
            item.setSizeHint(QSize(0, 62))
            self.list.addItem(item)
            if project.id == selected_id:
                selected_item = item
        self.count_label.setText(f"{len(projects)} tài liệu")
        if selected_item:
            self.list.setCurrentItem(selected_item)
        self.list.blockSignals(False)
        self.delete_button.setEnabled(self.list.currentItem() is not None)

    def select_project(self, project_id: str) -> None:
        for index in range(self.list.count()):
            item = self.list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == project_id:
                self.list.setCurrentItem(item)
                return

    def _selection_changed(self, current: QListWidgetItem | None) -> None:
        self.delete_button.setEnabled(current is not None)
        if current:
            self.project_selected.emit(str(current.data(Qt.ItemDataRole.UserRole)))

    def _delete_current(self) -> None:
        item = self.list.currentItem()
        if item:
            self.delete_requested.emit(str(item.data(Qt.ItemDataRole.UserRole)))

