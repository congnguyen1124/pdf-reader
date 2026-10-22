from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QDropEvent, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from linguapdf.domain.models import StudyFolder, StudyProject
from linguapdf.ui.i18n import tr
from linguapdf.ui.icons import (
    explorer_action_icon,
    explorer_folder_icon,
    explorer_workspace_icon,
    search_icon,
)

ROLE_TYPE = Qt.ItemDataRole.UserRole
ROLE_ID = Qt.ItemDataRole.UserRole + 1
ROLE_FOLDER_ID = Qt.ItemDataRole.UserRole + 2


class WorkspaceTree(QTreeWidget):
    project_moved = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

    def dropEvent(self, event: QDropEvent) -> None:
        source = self.currentItem()
        if not source or source.data(0, ROLE_TYPE) != "project":
            event.ignore()
            return
        target = self.itemAt(event.position().toPoint())
        if target and target.data(0, ROLE_TYPE) == "folder":
            folder_id = str(target.data(0, ROLE_ID))
        elif target and target.data(0, ROLE_TYPE) == "project":
            value = target.data(0, ROLE_FOLDER_ID)
            folder_id = str(value) if value else None
        else:
            folder_id = None
        self.project_moved.emit(str(source.data(0, ROLE_ID)), folder_id)
        event.ignore()


class ProjectLibraryPanel(QWidget):
    project_selected = Signal(str)
    import_requested = Signal(object)
    create_requested = Signal(object)
    add_folder_requested = Signal(object)
    delete_requested = Signal(str)
    delete_folder_requested = Signal(str)
    move_project_requested = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("libraryPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(210)
        self.setMaximumWidth(320)
        self._projects: list[StudyProject] = []
        self._folders: list[StudyFolder] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 7)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(11, 7, 5, 6)
        header.setSpacing(1)
        self.brand = QLabel()
        self.brand.setObjectName("explorerTitle")
        header.addWidget(self.brand)
        header.addStretch()

        self.import_button = self._header_button("import")
        self.import_button.clicked.connect(
            lambda: self.import_requested.emit(self.current_folder_id)
        )
        header.addWidget(self.import_button)
        self.create_button = self._header_button("file")
        self.create_button.clicked.connect(
            lambda: self.create_requested.emit(self.current_folder_id)
        )
        header.addWidget(self.create_button)
        self.folder_button = self._header_button("folder")
        self.folder_button.clicked.connect(
            lambda: self.add_folder_requested.emit(self.current_folder_id)
        )
        header.addWidget(self.folder_button)
        self.collapse_button = self._header_button("collapse")
        self.collapse_button.clicked.connect(self.tree_collapse_all)
        header.addWidget(self.collapse_button)
        self.delete_button = self._header_button("delete")
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self._delete_current)
        header.addWidget(self.delete_button)
        layout.addLayout(header)

        section = QHBoxLayout()
        section.setContentsMargins(11, 4, 9, 5)
        self.subtitle = QLabel()
        self.subtitle.setObjectName("eyebrowLabel")
        section.addWidget(self.subtitle)
        section.addStretch()
        self.count_label = QLabel()
        self.count_label.setObjectName("explorerCount")
        section.addWidget(self.count_label)
        layout.addLayout(section)

        self.search = QLineEdit()
        self.search.setObjectName("librarySearch")
        self.search.addAction(search_icon(), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._apply_filter)
        search_row = QHBoxLayout()
        search_row.setContentsMargins(7, 0, 7, 6)
        search_row.addWidget(self.search)
        layout.addLayout(search_row)

        self.tree = WorkspaceTree()
        self.tree.setObjectName("projectTree")
        self.tree.setHeaderHidden(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setAnimated(True)
        self.tree.setIndentation(14)
        self.tree.setIconSize(QSize(16, 16))
        self.tree.setUniformRowHeights(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setExpandsOnDoubleClick(True)
        self.tree.currentItemChanged.connect(self._selection_changed)
        self.tree.project_moved.connect(self.move_project_requested)
        layout.addWidget(self.tree, 1)
        self.retranslate_ui()

    def _header_button(self, kind: str) -> QToolButton:
        button = QToolButton(self)
        button.setObjectName("libraryActionButton")
        button.setIcon(explorer_action_icon(kind))
        button.setIconSize(QSize(18, 18))
        button.setFixedSize(27, 27)
        button.setAutoRaise(True)
        return button

    def tree_collapse_all(self) -> None:
        self.tree.collapseAll()

    @property
    def current_folder_id(self) -> str | None:
        item = self.tree.currentItem()
        if not item:
            return None
        if item.data(0, ROLE_TYPE) == "folder":
            return str(item.data(0, ROLE_ID))
        folder_id = item.data(0, ROLE_FOLDER_ID)
        return str(folder_id) if folder_id else None

    def set_library(
        self,
        folders: list[StudyFolder],
        projects: list[StudyProject],
        selected_id: str | None = None,
    ) -> None:
        expanded = {
            str(item.data(0, ROLE_ID))
            for item in self._all_items()
            if item.data(0, ROLE_TYPE) == "folder" and item.isExpanded()
        }
        self._folders = folders
        self._projects = projects
        self.tree.blockSignals(True)
        self.tree.clear()
        folder_items: dict[str, QTreeWidgetItem] = {}

        pending = sorted(folders, key=lambda folder: folder.name.casefold())
        while pending:
            added_any = False
            for folder in pending[:]:
                if folder.parent_id and folder.parent_id not in folder_items:
                    continue
                item = QTreeWidgetItem([folder.name])
                item.setData(0, ROLE_TYPE, "folder")
                item.setData(0, ROLE_ID, folder.id)
                item.setIcon(0, explorer_folder_icon())
                item.setSizeHint(0, QSize(0, 26))
                item.setFlags(
                    (item.flags() | Qt.ItemFlag.ItemIsDropEnabled) & ~Qt.ItemFlag.ItemIsDragEnabled
                )
                parent = folder_items.get(folder.parent_id or "")
                (parent.addChild if parent else self.tree.addTopLevelItem)(item)
                item.setExpanded(folder.id in expanded)
                folder_items[folder.id] = item
                pending.remove(folder)
                added_any = True
            if not added_any:
                break

        selected_item: QTreeWidgetItem | None = None
        for project in sorted(projects, key=lambda value: value.title.casefold()):
            item = self._project_item(project)
            parent = folder_items.get(project.folder_id or "")
            (parent.addChild if parent else self.tree.addTopLevelItem)(item)
            if project.id == selected_id:
                selected_item = item
                ancestor = item.parent()
                while ancestor:
                    ancestor.setExpanded(True)
                    ancestor = ancestor.parent()

        if selected_item:
            self.tree.setCurrentItem(selected_item)
        self.tree.blockSignals(False)
        self.delete_button.setEnabled(self.tree.currentItem() is not None)
        self._apply_filter(self.search.text())
        self.count_label.setText(tr("documents_count", count=len(projects)))

    def set_projects(self, projects: list[StudyProject], selected_id: str | None = None) -> None:
        self.set_library(self._folders, projects, selected_id)

    def select_project(self, project_id: str) -> None:
        for item in self._all_items():
            if item.data(0, ROLE_TYPE) == "project" and item.data(0, ROLE_ID) == project_id:
                parent = item.parent()
                while parent:
                    parent.setExpanded(True)
                    parent = parent.parent()
                self.tree.setCurrentItem(item)
                return

    def retranslate_ui(self) -> None:
        self.brand.setText(tr("explorer"))
        self.subtitle.setText(tr("lesson_library"))
        self.search.setPlaceholderText(tr("search_workspaces"))
        open_key = QKeySequence(QKeySequence.StandardKey.Open).toString(
            QKeySequence.SequenceFormat.NativeText
        )
        new_key = QKeySequence(QKeySequence.StandardKey.New).toString(
            QKeySequence.SequenceFormat.NativeText
        )
        self.import_button.setToolTip(f"{tr('import_pdf_description')}  ·  {open_key}")
        self.create_button.setToolTip(f"{tr('new_workspace_description')}  ·  {new_key}")
        self.folder_button.setToolTip(tr("new_folder"))
        self.collapse_button.setToolTip(tr("collapse_all"))
        self.delete_button.setToolTip(tr("delete"))
        self.count_label.setText(tr("documents_count", count=len(self._projects)))
        if self._projects or self._folders:
            selected = self.tree.currentItem()
            selected_id = (
                str(selected.data(0, ROLE_ID))
                if selected and selected.data(0, ROLE_TYPE) == "project"
                else None
            )
            self.set_library(self._folders, self._projects, selected_id)

    def _project_item(self, project: StudyProject) -> QTreeWidgetItem:
        kind = "PDF" if project.kind == "pdf" else tr("flashcards")
        suffix = f"{kind}  •  {tr('words_count', count=project.card_count)}"
        item = QTreeWidgetItem([project.title])
        item.setData(0, ROLE_TYPE, "project")
        item.setData(0, ROLE_ID, project.id)
        item.setData(0, ROLE_FOLDER_ID, project.folder_id)
        location = project.path if project.path else tr("no_pdf")
        item.setToolTip(0, f"{suffix}\n{location}")
        item.setSizeHint(0, QSize(0, 27))
        item.setIcon(0, explorer_workspace_icon(project.kind))
        item.setFlags(
            (item.flags() | Qt.ItemFlag.ItemIsDragEnabled) & ~Qt.ItemFlag.ItemIsDropEnabled
        )
        return item

    def _all_items(self) -> list[QTreeWidgetItem]:
        items: list[QTreeWidgetItem] = []

        def collect(item: QTreeWidgetItem) -> None:
            items.append(item)
            for child_index in range(item.childCount()):
                collect(item.child(child_index))

        for index in range(self.tree.topLevelItemCount()):
            collect(self.tree.topLevelItem(index))
        return items

    def _apply_filter(self, query: str) -> None:
        needle = query.strip().casefold()

        def filter_item(item: QTreeWidgetItem) -> bool:
            child_matches = any(
                filter_item(item.child(index)) for index in range(item.childCount())
            )
            own_match = not needle or needle in item.text(0).casefold()
            visible = own_match or child_matches
            item.setHidden(not visible)
            if needle and child_matches:
                item.setExpanded(True)
            return visible

        for index in range(self.tree.topLevelItemCount()):
            filter_item(self.tree.topLevelItem(index))

    def _selection_changed(self, current: QTreeWidgetItem | None) -> None:
        self.delete_button.setEnabled(current is not None)
        if current and current.data(0, ROLE_TYPE) == "project":
            self.project_selected.emit(str(current.data(0, ROLE_ID)))

    def _delete_current(self) -> None:
        item = self.tree.currentItem()
        if not item:
            return
        item_id = str(item.data(0, ROLE_ID))
        if item.data(0, ROLE_TYPE) == "folder":
            self.delete_folder_requested.emit(item_id)
        else:
            self.delete_requested.emit(item_id)
