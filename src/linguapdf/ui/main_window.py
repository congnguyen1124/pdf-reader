from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from linguapdf.domain.models import Annotation, StudyProject
from linguapdf.services.library_service import LibraryService
from linguapdf.services.pdf_service import PdfDocumentSession
from linguapdf.services.text_pdf_service import create_pdf_from_text
from linguapdf.ui.i18n import set_language, tr
from linguapdf.ui.icons import panel_toggle_icon, search_icon
from linguapdf.ui.library_panel import ProjectLibraryPanel
from linguapdf.ui.pdf_search_bar import PdfSearchBar
from linguapdf.ui.pdf_viewer import PdfViewer
from linguapdf.ui.styles import build_stylesheet
from linguapdf.ui.text_pdf_dialog import TextPdfDialog
from linguapdf.ui.vocabulary_panel import VocabularyPanel
from linguapdf.ui.workspace_page import WorkspacePage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("appRoot")
        self.resize(1540, 920)
        self.setMinimumSize(1120, 700)

        self.settings = QSettings()
        self.language_code = self.settings.value("language", "en", str)
        self.theme = self.settings.value("theme", "light", str)
        set_language(self.language_code)
        application = QApplication.instance()
        if application:
            application.setStyleSheet(build_stylesheet(self.theme))

        data_dir = Path(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        )
        self.library = LibraryService(data_dir / "linguapdf.sqlite3")
        self.session: PdfDocumentSession | None = None
        self.current_project: StudyProject | None = None
        self.annotation_save_timer = QTimer(self)
        self.annotation_save_timer.setSingleShot(True)
        self.annotation_save_timer.setInterval(450)
        self.annotation_save_timer.timeout.connect(lambda: self.save_annotations(silent=True))

        self.library_panel = ProjectLibraryPanel()
        self.viewer = PdfViewer()
        self.workspace_page = WorkspacePage()
        self.reader_stack = QStackedWidget()
        self.reader_stack.addWidget(self.viewer)
        self.reader_stack.addWidget(self.workspace_page)
        self.pdf_search_bar = PdfSearchBar()
        self.reader_container = QWidget()
        reader_layout = QVBoxLayout(self.reader_container)
        reader_layout.setContentsMargins(0, 0, 0, 0)
        reader_layout.setSpacing(0)
        reader_layout.addWidget(self.pdf_search_bar)
        reader_layout.addWidget(self.reader_stack, 1)
        self.vocabulary = VocabularyPanel(self.library)

        self.pdf_search_timer = QTimer(self)
        self.pdf_search_timer.setSingleShot(True)
        self.pdf_search_timer.setInterval(180)
        self.pdf_search_timer.timeout.connect(self._search_pdf)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.library_panel)
        self.splitter.addWidget(self.reader_container)
        self.splitter.addWidget(self.vocabulary)
        self.splitter.setSizes([240, 890, 410])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        self.splitter.setCollapsible(0, True)
        self.splitter.setCollapsible(2, True)
        self.setCentralWidget(self.splitter)

        self._create_actions()
        self._create_toolbar()
        self._create_menu()
        self._connect_signals()
        self._set_library_visible(self.toggle_library_action.isChecked())
        self._set_vocabulary_visible(self.toggle_vocabulary_action.isChecked())
        self._set_pdf_actions_enabled(False)
        self._retranslate_ui()
        self._refresh_library()
        self.statusBar().showMessage(tr("ready"))

        last_project = self.settings.value("last_project", "", str)
        if last_project and self.library.project(last_project):
            self.library_panel.select_project(last_project)

    def _create_actions(self) -> None:
        self.toggle_library_action = QAction(panel_toggle_icon("left"), "", self, checkable=True)
        self.toggle_library_action.setChecked(
            self.settings.value("library_panel_visible", True, bool)
        )
        self.toggle_library_action.toggled.connect(self._set_library_visible)

        self.toggle_vocabulary_action = QAction(
            panel_toggle_icon("right"), "", self, checkable=True
        )
        self.toggle_vocabulary_action.setChecked(
            self.settings.value("vocabulary_panel_visible", True, bool)
        )
        self.toggle_vocabulary_action.toggled.connect(self._set_vocabulary_visible)

        self.import_action = QAction(self)
        self.import_action.triggered.connect(lambda: self.choose_pdf(None))
        self.new_vocabulary_action = QAction(self)
        self.new_vocabulary_action.triggered.connect(lambda: self.create_vocabulary_project(None))
        self.new_folder_action = QAction(self)
        self.new_folder_action.triggered.connect(lambda: self.create_folder(None))

        self.save_action = QAction(self)
        self.save_action.triggered.connect(self.save_annotations)
        self.export_action = QAction(self)
        self.export_action.triggered.connect(self.export_pdf)

        self.zoom_out_action = QAction("−", self)
        self.zoom_out_action.triggered.connect(self.viewer.zoom_out)
        self.zoom_in_action = QAction("＋", self)
        self.zoom_in_action.triggered.connect(self.viewer.zoom_in)
        self.fit_action = QAction(self)
        self.fit_action.triggered.connect(self.viewer.fit_width)
        self.find_action = QAction(search_icon(), "", self)
        self.find_action.triggered.connect(self.show_pdf_search)

        self.mode_group = QActionGroup(self)
        self.mode_group.setExclusive(True)
        self.select_action = QAction(self, checkable=True)
        self.select_action.setChecked(True)
        self.note_action = QAction(self, checkable=True)
        for action, mode in ((self.select_action, "select"), (self.note_action, "note")):
            self.mode_group.addAction(action)
            action.triggered.connect(lambda _checked=False, value=mode: self.viewer.set_mode(value))

        self.show_edits_action = QAction(self, checkable=True)
        self.show_edits_action.setChecked(True)
        self.show_edits_action.toggled.connect(self.viewer.set_annotations_visible)
        self.autosave_action = QAction(self, checkable=True)
        self.autosave_action.setChecked(self.settings.value("autosave", True, bool))
        self.autosave_action.toggled.connect(self._autosave_changed)

        self.undo_action = QAction(self)
        self.undo_action.triggered.connect(self.undo_last_annotation)
        self.delete_annotation_action = QAction(self)
        self.delete_annotation_action.triggered.connect(self.delete_selected_annotations)
        self.delete_annotation_action.setEnabled(False)
        self.close_action = QAction(self)
        self.close_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.close_action.triggered.connect(self.close)

        self.language_group = QActionGroup(self)
        self.language_group.setExclusive(True)
        self.language_actions: dict[str, QAction] = {}
        for code, label in (("en", "English"), ("vi", "Tiếng Việt")):
            action = QAction(label, self, checkable=True)
            action.setChecked(code == self.language_code)
            action.triggered.connect(lambda _checked=False, value=code: self._set_language(value))
            self.language_group.addAction(action)
            self.language_actions[code] = action

        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)
        self.theme_actions: dict[str, QAction] = {}
        for theme in ("light", "dark"):
            action = QAction(self, checkable=True)
            action.setChecked(theme == self.theme)
            action.triggered.connect(lambda _checked=False, value=theme: self._set_theme(value))
            self.theme_group.addAction(action)
            self.theme_actions[theme] = action

    def _create_toolbar(self) -> None:
        self.toolbar = QToolBar(self)
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.addToolBar(self.toolbar)
        self.toolbar.addAction(self.toggle_library_action)
        self.toolbar.addAction(self.toggle_vocabulary_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.zoom_out_action)
        self.zoom_label = QLabel("85%")
        self.zoom_label.setMinimumWidth(44)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.toolbar.addWidget(self.zoom_label)
        self.toolbar.addAction(self.zoom_in_action)
        self.toolbar.addAction(self.fit_action)
        self.toolbar.addAction(self.find_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.select_action)
        self.toolbar.addAction(self.note_action)
        self.space_hint = QLabel()
        self.space_hint.setObjectName("mutedLabel")
        self.toolbar.addWidget(self.space_hint)
        self.toolbar.addAction(self.delete_annotation_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.show_edits_action)
        self.toolbar.addAction(self.autosave_action)
        self.toolbar.addAction(self.save_action)

    def _create_menu(self) -> None:
        self.file_menu = self.menuBar().addMenu("")
        self.file_menu.addAction(self.import_action)
        self.file_menu.addAction(self.new_vocabulary_action)
        self.file_menu.addAction(self.new_folder_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.save_action)
        self.file_menu.addAction(self.export_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.close_action)

        self.edit_menu = self.menuBar().addMenu("")
        self.edit_menu.addAction(self.undo_action)
        self.edit_menu.addAction(self.delete_annotation_action)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.find_action)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.show_edits_action)
        self.edit_menu.addAction(self.autosave_action)

        self.view_menu = self.menuBar().addMenu("")
        self.view_menu.addAction(self.toggle_library_action)
        self.view_menu.addAction(self.toggle_vocabulary_action)
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.fit_action)

        self.settings_menu = self.menuBar().addMenu("")
        self.language_menu = self.settings_menu.addMenu("")
        for action in self.language_actions.values():
            self.language_menu.addAction(action)
        self.theme_menu = self.settings_menu.addMenu("")
        for action in self.theme_actions.values():
            self.theme_menu.addAction(action)

    @staticmethod
    def _configure_shortcut(
        action: QAction, shortcut: str | QKeySequence.StandardKey, description: str
    ) -> None:
        sequence = QKeySequence(shortcut)
        action.setShortcut(sequence)
        shortcut_text = sequence.toString(QKeySequence.SequenceFormat.NativeText)
        action.setToolTip(f"{description}  ·  {shortcut_text}")
        action.setStatusTip(f"{description} ({shortcut_text})")

    def _retranslate_ui(self) -> None:
        title = self.current_project.title if self.current_project else None
        self.setWindowTitle(f"{title} - LinguaPDF" if title else tr("app_title"))
        self.toolbar.setWindowTitle(tr("pdf_tools"))
        self.file_menu.setTitle(tr("file_menu"))
        self.edit_menu.setTitle(tr("edit_menu"))
        self.view_menu.setTitle(tr("view_menu"))
        self.settings_menu.setTitle(tr("settings_menu"))
        self.language_menu.setTitle(tr("language_menu"))
        self.theme_menu.setTitle(tr("theme_menu"))

        self.toggle_library_action.setText(tr("library"))
        self._configure_shortcut(self.toggle_library_action, "Ctrl+Shift+L", tr("toggle_library"))
        self.toggle_vocabulary_action.setText(tr("vocabulary"))
        self._configure_shortcut(
            self.toggle_vocabulary_action, "Ctrl+Shift+F", tr("toggle_vocabulary")
        )
        self.import_action.setText(f"{tr('import_pdf')}...")
        self._configure_shortcut(
            self.import_action, QKeySequence.StandardKey.Open, tr("import_pdf_description")
        )
        self.new_vocabulary_action.setText(f"{tr('new_workspace')}...")
        self._configure_shortcut(
            self.new_vocabulary_action,
            QKeySequence.StandardKey.New,
            tr("new_workspace_description"),
        )
        self.new_folder_action.setText(f"{tr('new_folder')}...")
        self._configure_shortcut(self.new_folder_action, "Ctrl+Shift+N", tr("new_folder"))
        self.save_action.setText(tr("save_changes"))
        self._configure_shortcut(
            self.save_action, QKeySequence.StandardKey.Save, tr("save_description")
        )
        self.export_action.setText(tr("export_pdf"))
        self._configure_shortcut(self.export_action, "Ctrl+Shift+S", tr("export_description"))
        self._configure_shortcut(
            self.zoom_out_action, QKeySequence.StandardKey.ZoomOut, tr("zoom_out")
        )
        self._configure_shortcut(
            self.zoom_in_action, QKeySequence.StandardKey.ZoomIn, tr("zoom_in")
        )
        self.fit_action.setText(tr("fit_width"))
        self._configure_shortcut(self.fit_action, "Ctrl+0", tr("fit_description"))
        self.find_action.setText(tr("find_in_pdf"))
        self._configure_shortcut(
            self.find_action, QKeySequence.StandardKey.Find, tr("find_in_pdf_description")
        )
        self.select_action.setText(tr("select_text"))
        self._configure_shortcut(self.select_action, "Ctrl+1", tr("select_description"))
        self.note_action.setText(tr("note"))
        self._configure_shortcut(self.note_action, "Ctrl+2", tr("note_description"))
        self.show_edits_action.setText(tr("show_edits"))
        self._configure_shortcut(
            self.show_edits_action, "Ctrl+Shift+E", tr("show_edits_description")
        )
        self.autosave_action.setText(tr("autosave"))
        self._configure_shortcut(self.autosave_action, "Ctrl+Shift+A", tr("autosave_description"))
        self.undo_action.setText(tr("undo"))
        self._configure_shortcut(self.undo_action, QKeySequence.StandardKey.Undo, tr("undo"))
        self.delete_annotation_action.setText(tr("delete_selection"))
        self._configure_shortcut(
            self.delete_annotation_action,
            QKeySequence.StandardKey.Delete,
            tr("delete_selection_description"),
        )
        self.close_action.setText(tr("quit"))
        self.theme_actions["light"].setText(tr("light"))
        self.theme_actions["dark"].setText(tr("dark"))
        self.space_hint.setText(tr("space_pan"))
        self.library_panel.retranslate_ui()
        self.workspace_page.retranslate_ui()
        self.vocabulary.retranslate_ui()
        self.viewer.retranslate_ui()
        self.pdf_search_bar.retranslate_ui()

    def _set_language(self, code: str) -> None:
        self.language_code = code
        self.settings.setValue("language", code)
        set_language(code)
        self.language_actions[code].setChecked(True)
        self._retranslate_ui()
        self._refresh_library()

    def _set_theme(self, theme: str) -> None:
        self.theme = theme if theme in {"light", "dark"} else "light"
        self.settings.setValue("theme", self.theme)
        self.theme_actions[self.theme].setChecked(True)
        application = QApplication.instance()
        if application:
            application.setStyleSheet(build_stylesheet(self.theme))

    def _set_library_visible(self, visible: bool) -> None:
        self.library_panel.setVisible(visible)
        self.settings.setValue("library_panel_visible", visible)

    def _set_vocabulary_visible(self, visible: bool) -> None:
        self.vocabulary.setVisible(visible)
        self.settings.setValue("vocabulary_panel_visible", visible)

    def _connect_signals(self) -> None:
        self.viewer.annotations_created.connect(self._add_annotations)
        self.viewer.annotation_updated.connect(self._update_annotation)
        self.viewer.annotation_style_updated.connect(self._update_annotation_style)
        self.viewer.annotation_delete_requested.connect(self._delete_annotation)
        self.viewer.selection_changed.connect(self.delete_annotation_action.setEnabled)
        self.viewer.zoom_changed.connect(lambda value: self.zoom_label.setText(f"{value}%"))
        self.viewer.quick_vocabulary_requested.connect(self.vocabulary.add_quick_vocabulary)
        self.pdf_search_bar.query_changed.connect(self._queue_pdf_search)
        self.pdf_search_bar.next_requested.connect(self._next_pdf_search_result)
        self.pdf_search_bar.previous_requested.connect(self._previous_pdf_search_result)
        self.pdf_search_bar.close_requested.connect(self._close_pdf_search)
        self.library_panel.import_requested.connect(self.choose_pdf)
        self.library_panel.create_requested.connect(self.create_vocabulary_project)
        self.library_panel.add_folder_requested.connect(self.create_folder)
        self.library_panel.project_selected.connect(self.open_project)
        self.library_panel.delete_requested.connect(self.delete_project)
        self.library_panel.delete_folder_requested.connect(self.delete_folder)
        self.library_panel.move_project_requested.connect(self.move_project)
        self.workspace_page.attach_pdf_requested.connect(self.attach_pdf_to_workspace)
        self.workspace_page.create_from_text_requested.connect(self.create_workspace_pdf)
        self.vocabulary.cards_changed.connect(self._refresh_library)

    def _set_pdf_actions_enabled(self, enabled: bool) -> None:
        for action in (
            self.save_action,
            self.export_action,
            self.zoom_out_action,
            self.zoom_in_action,
            self.fit_action,
            self.find_action,
            self.select_action,
            self.note_action,
            self.show_edits_action,
            self.undo_action,
        ):
            action.setEnabled(enabled)

    def _refresh_library(self) -> None:
        selected_id = self.current_project.id if self.current_project else None
        self.library_panel.set_library(self.library.folders(), self.library.projects(), selected_id)

    def choose_pdf(self, folder_id: str | None = None) -> None:
        if isinstance(folder_id, bool):
            folder_id = None
        start_directory = self.settings.value("last_directory", str(Path.home()), str)
        path, _ = QFileDialog.getOpenFileName(
            self, tr("open_pdf_title"), start_directory, "PDF (*.pdf)"
        )
        if path:
            self.open_pdf(path, folder_id)

    def open_pdf(self, path: str, folder_id: str | None = None) -> None:
        try:
            validation = PdfDocumentSession(path)
            title = validation.title
            validation.close()
            project = self.library.import_pdf(path, title, folder_id)
        except (OSError, RuntimeError, ValueError) as error:
            QMessageBox.critical(self, tr("cannot_import_pdf"), str(error))
            return
        self.settings.setValue("last_directory", str(Path(path).resolve().parent))
        self._refresh_library()
        self.library_panel.select_project(project.id)

    def create_vocabulary_project(self, folder_id: str | None = None) -> None:
        if isinstance(folder_id, bool):
            folder_id = None
        title, accepted = QInputDialog.getText(
            self,
            tr("new_workspace_title"),
            tr("workspace_name"),
            text=tr("default_workspace_name"),
        )
        if not accepted:
            return
        try:
            project = self.library.create_vocabulary_project(title, folder_id)
        except ValueError as error:
            QMessageBox.warning(self, tr("invalid_name"), str(error))
            return
        self._refresh_library()
        self.library_panel.select_project(project.id)

    def create_folder(self, parent_id: str | None = None) -> None:
        if isinstance(parent_id, bool):
            parent_id = None
        title, accepted = QInputDialog.getText(
            self,
            tr("new_folder_title"),
            tr("folder_name"),
            text=tr("default_folder_name"),
        )
        if not accepted:
            return
        try:
            self.library.create_folder(title, parent_id)
        except ValueError as error:
            QMessageBox.warning(self, tr("invalid_name"), str(error))
            return
        self._refresh_library()

    def open_project(self, project_id: str, *, force: bool = False) -> None:
        if self.current_project and self.current_project.id == project_id and not force:
            return
        if not self._can_close_current():
            if self.current_project:
                self.library_panel.select_project(self.current_project.id)
            return
        project = self.library.project(project_id)
        if project is None:
            return
        self._close_pdf_search()
        if self.session:
            self.session.close()
            self.session = None

        if project.kind == "pdf":
            try:
                self.session = PdfDocumentSession(project.path)
            except (OSError, RuntimeError, ValueError) as error:
                QMessageBox.critical(self, tr("cannot_open_pdf"), str(error))
                return
            self.viewer.set_document(self.session)
            self.reader_stack.setCurrentWidget(self.viewer)
            self._set_pdf_actions_enabled(True)
            status = tr(
                "pdf_status",
                pages=self.session.page_count,
                annotations=len(self.session.annotations),
            )
        else:
            self._close_pdf_search()
            self.viewer.set_document(None, project.title)
            self.workspace_page.set_workspace(project.title)
            self.reader_stack.setCurrentWidget(self.workspace_page)
            self._set_pdf_actions_enabled(False)
            status = tr("workspace_no_pdf_status")

        self.current_project = project
        self.library.touch_project(project.id)
        self.vocabulary.set_document(project.id, project.title)
        self.settings.setValue("last_project", project.id)
        self.setWindowTitle(f"{project.title} - LinguaPDF")
        self.statusBar().showMessage(status, 5000)
        self._refresh_library()

    def attach_pdf_to_workspace(self) -> None:
        if not self.current_project:
            return
        start_directory = self.settings.value("last_directory", str(Path.home()), str)
        path, _ = QFileDialog.getOpenFileName(
            self, tr("attach_pdf_title"), start_directory, "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            validation = PdfDocumentSession(path)
            validation.close()
            self.library.attach_pdf(self.current_project.id, path)
        except (OSError, RuntimeError, ValueError) as error:
            QMessageBox.critical(self, tr("cannot_import_pdf"), str(error))
            return
        self.settings.setValue("last_directory", str(Path(path).resolve().parent))
        self.open_project(self.current_project.id, force=True)
        self.statusBar().showMessage(tr("pdf_attached"), 5000)

    def create_workspace_pdf(self) -> None:
        if not self.current_project:
            return
        dialog = TextPdfDialog(self.current_project.title, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            destination = self.library.generated_pdf_path(self.current_project.id)
            create_pdf_from_text(destination, dialog.document_title, dialog.content)
            self.library.attach_generated_pdf(self.current_project.id, destination)
        except (OSError, RuntimeError, ValueError) as error:
            QMessageBox.critical(self, tr("cannot_create_pdf"), str(error))
            return
        self.open_project(self.current_project.id, force=True)
        self.statusBar().showMessage(tr("pdf_created"), 5000)

    def delete_folder(self, folder_id: str) -> None:
        folder = next((item for item in self.library.folders() if item.id == folder_id), None)
        if not folder:
            return
        if not self.library.folder_is_empty(folder_id):
            QMessageBox.information(self, tr("folder_not_empty_title"), tr("folder_not_empty"))
            return
        response = QMessageBox.question(
            self,
            tr("delete_folder_title"),
            tr("delete_folder_question", name=folder.name),
        )
        if response == QMessageBox.StandardButton.Yes:
            self.library.delete_folder(folder_id)
            self._refresh_library()

    def move_project(self, project_id: str, folder_id: str | None) -> None:
        self.library.move_project(project_id, folder_id)
        if self.current_project and self.current_project.id == project_id:
            self.current_project = self.library.project(project_id)
        self._refresh_library()

    def delete_project(self, project_id: str) -> None:
        project = self.library.project(project_id)
        if project is None:
            return
        response = QMessageBox.question(
            self,
            tr("delete_project_title"),
            tr("delete_project_question", name=project.title),
        )
        if response != QMessageBox.StandardButton.Yes:
            return
        if self.current_project and self.current_project.id == project_id:
            if not self._can_close_current():
                return
            if self.session:
                self.session.close()
            self.session = None
            self.current_project = None
            self.viewer.set_document(None)
            self._close_pdf_search()
            self.reader_stack.setCurrentWidget(self.viewer)
            self.vocabulary.set_document(None)
            self._set_pdf_actions_enabled(False)
            self.setWindowTitle(tr("app_title"))
        self.library.delete_project(project_id)
        self._refresh_library()

    def _add_annotations(self, annotations: list[Annotation]) -> None:
        if not self.session:
            return
        for annotation in annotations:
            self.session.add_annotation(annotation)
        self.viewer.render_document(preserve_scroll=True)
        if len(annotations) == 1 and annotations[0].kind == "text":
            QTimer.singleShot(0, lambda: self.viewer.begin_edit_annotation(annotations[0].id))
        self._save_if_enabled()

    def _update_annotation(
        self,
        annotation_id: str,
        rect: tuple[float, float, float, float] | None,
        text: str | None,
    ) -> None:
        if not self.session:
            return
        self.session.update_annotation(annotation_id, rect=rect, text=text)
        if self.autosave_action.isChecked():
            self.annotation_save_timer.start()
        else:
            self.statusBar().showMessage(tr("unsaved"), 3000)

    def _update_annotation_style(
        self, annotation_id: str, font_size: float, text_color: str
    ) -> None:
        if not self.session:
            return
        self.session.update_annotation(
            annotation_id, font_size=font_size, text_color=text_color
        )
        if self.autosave_action.isChecked():
            self.annotation_save_timer.start()
        else:
            self.statusBar().showMessage(tr("unsaved"), 3000)

    def show_pdf_search(self) -> None:
        if not self.session:
            return
        self.pdf_search_bar.open_search()
        if self.pdf_search_bar.search_input.text().strip():
            self._search_pdf()

    def _queue_pdf_search(self, _query: str) -> None:
        self.pdf_search_timer.start()

    def _search_pdf(self) -> None:
        current, total = self.viewer.search_text(self.pdf_search_bar.search_input.text())
        self.pdf_search_bar.set_result(current, total)

    def _next_pdf_search_result(self) -> None:
        if self.pdf_search_timer.isActive():
            self.pdf_search_timer.stop()
            self._search_pdf()
            return
        self.pdf_search_bar.set_result(*self.viewer.next_search_match())

    def _previous_pdf_search_result(self) -> None:
        if self.pdf_search_timer.isActive():
            self.pdf_search_timer.stop()
            self._search_pdf()
            return
        self.pdf_search_bar.set_result(*self.viewer.previous_search_match())

    def _close_pdf_search(self) -> None:
        self.pdf_search_timer.stop()
        self.pdf_search_bar.hide()
        self.viewer.clear_search()
        self.viewer.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _save_if_enabled(self) -> None:
        if self.autosave_action.isChecked():
            self.save_annotations(silent=True)
        else:
            self.statusBar().showMessage(tr("unsaved"), 3000)

    def save_annotations(self, _checked: bool = False, *, silent: bool = False) -> None:
        if not self.session:
            return
        try:
            saved_path = self.session.save_annotations()
        except OSError as error:
            QMessageBox.critical(self, tr("cannot_save"), str(error))
            return
        if not silent:
            self.statusBar().showMessage(tr("saved", name=saved_path.name), 5000)

    def export_pdf(self) -> None:
        if not self.session:
            return
        default_name = Path.home() / f"{self.session.path.stem}.annotated.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, tr("export_title"), str(default_name), "PDF (*.pdf)"
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            exported = self.session.export_annotated_pdf(path)
        except (OSError, RuntimeError, ValueError) as error:
            QMessageBox.critical(self, tr("cannot_export"), str(error))
            return
        self.statusBar().showMessage(tr("exported", name=exported.name), 6000)

    def undo_last_annotation(self) -> None:
        if not self.session or not self.session.undo_last():
            return
        self.viewer.render_document(preserve_scroll=True)
        self._save_if_enabled()

    def delete_selected_annotations(self) -> None:
        if not self.session:
            return
        selected = self.viewer.selected_annotation_ids()
        if self.session.remove_annotations(selected):
            self.viewer.render_document(preserve_scroll=True)
            self._save_if_enabled()

    def _delete_annotation(self, annotation_id: str) -> None:
        if not self.session:
            return
        if self.session.remove_annotations({annotation_id}):
            self.viewer.render_document(preserve_scroll=True)
            self._save_if_enabled()

    def _autosave_changed(self, enabled: bool) -> None:
        self.settings.setValue("autosave", enabled)
        if enabled:
            if self.session and self.session.dirty:
                self.save_annotations(silent=True)
        else:
            self.annotation_save_timer.stop()
        self.statusBar().showMessage(
            tr("autosave_state", state=tr("on") if enabled else tr("off")), 3000
        )

    def _can_close_current(self) -> bool:
        if not self.session or not self.session.dirty:
            return True
        if self.autosave_action.isChecked():
            self.annotation_save_timer.stop()
            self.save_annotations(silent=True)
            return not self.session.dirty
        response = QMessageBox.warning(
            self,
            tr("unsaved_title"),
            tr("unsaved_question"),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if response == QMessageBox.StandardButton.Cancel:
            return False
        if response == QMessageBox.StandardButton.Save:
            self.save_annotations()
            return not self.session.dirty
        return True

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._can_close_current():
            event.ignore()
            return
        if self.session:
            self.session.close()
        self.library.close()
        event.accept()
