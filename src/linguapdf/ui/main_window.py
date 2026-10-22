from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QToolBar,
)

from linguapdf.domain.models import Annotation, StudyProject
from linguapdf.services.library_service import LibraryService
from linguapdf.services.pdf_service import PdfDocumentSession
from linguapdf.ui.library_panel import ProjectLibraryPanel
from linguapdf.ui.pdf_viewer import PdfViewer
from linguapdf.ui.vocabulary_panel import VocabularyPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("appRoot")
        self.setWindowTitle("LinguaPDF — PDF & Flashcards")
        self.resize(1540, 920)
        self.setMinimumSize(1120, 700)

        data_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
        self.library = LibraryService(data_dir / "linguapdf.sqlite3")
        self.settings = QSettings()
        self.session: PdfDocumentSession | None = None
        self.current_project: StudyProject | None = None
        self.annotation_save_timer = QTimer(self)
        self.annotation_save_timer.setSingleShot(True)
        self.annotation_save_timer.setInterval(450)
        self.annotation_save_timer.timeout.connect(lambda: self.save_annotations(silent=True))

        self.library_panel = ProjectLibraryPanel()
        self.viewer = PdfViewer()
        self.vocabulary = VocabularyPanel(self.library)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.library_panel)
        splitter.addWidget(self.viewer)
        splitter.addWidget(self.vocabulary)
        splitter.setSizes([255, 875, 410])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(2, True)
        self.setCentralWidget(splitter)

        self._create_actions()
        self._create_toolbar()
        self._create_menu()
        self._connect_signals()
        self._set_pdf_actions_enabled(False)
        self._refresh_library()
        self.statusBar().showMessage("Sẵn sàng — chọn hoặc tạo một bài học ở thư viện")

        last_project = self.settings.value("last_project", "", str)
        if last_project and self.library.project(last_project):
            self.library_panel.select_project(last_project)

    def _create_actions(self) -> None:
        self.import_action = QAction("Nhập PDF…", self)
        self.import_action.setShortcut(QKeySequence.StandardKey.Open)
        self.import_action.triggered.connect(self.choose_pdf)

        self.new_vocabulary_action = QAction("Bộ từ vựng mới…", self)
        self.new_vocabulary_action.setShortcut(QKeySequence("Ctrl+N"))
        self.new_vocabulary_action.triggered.connect(self.create_vocabulary_project)

        self.save_action = QAction("Lưu thay đổi", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self.save_annotations)

        self.export_action = QAction("Xuất PDF đã chỉnh sửa…", self)
        self.export_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.export_action.triggered.connect(self.export_pdf)

        self.zoom_out_action = QAction("−", self)
        self.zoom_out_action.setToolTip("Thu nhỏ (Ctrl+-)")
        self.zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self.zoom_out_action.triggered.connect(self.viewer.zoom_out)
        self.zoom_in_action = QAction("＋", self)
        self.zoom_in_action.setToolTip("Phóng to (Ctrl++)")
        self.zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        self.zoom_in_action.triggered.connect(self.viewer.zoom_in)
        self.fit_action = QAction("Vừa chiều rộng", self)
        self.fit_action.triggered.connect(self.viewer.fit_width)

        self.mode_group = QActionGroup(self)
        self.mode_group.setExclusive(True)
        self.select_action = QAction("Chọn chữ", self, checkable=True)
        self.select_action.setChecked(True)
        self.note_action = QAction("Ghi chú", self, checkable=True)
        for action, mode in ((self.select_action, "select"), (self.note_action, "note")):
            self.mode_group.addAction(action)
            action.triggered.connect(lambda _checked=False, value=mode: self.viewer.set_mode(value))

        self.show_edits_action = QAction("Hiện chỉnh sửa", self, checkable=True)
        self.show_edits_action.setChecked(True)
        self.show_edits_action.toggled.connect(self.viewer.set_annotations_visible)

        self.autosave_action = QAction("Tự động lưu", self, checkable=True)
        self.autosave_action.setChecked(self.settings.value("autosave", True, bool))
        self.autosave_action.toggled.connect(self._autosave_changed)

        self.undo_action = QAction("Hoàn tác chỉnh sửa cuối", self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.triggered.connect(self.undo_last_annotation)

        self.delete_annotation_action = QAction("Xóa vùng đã chọn", self)
        self.delete_annotation_action.setShortcut(QKeySequence.StandardKey.Delete)
        self.delete_annotation_action.triggered.connect(self.delete_selected_annotations)
        self.delete_annotation_action.setEnabled(False)

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Công cụ PDF", self)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        self.addToolBar(toolbar)
        toolbar.addAction(self.import_action)
        toolbar.addAction(self.new_vocabulary_action)
        toolbar.addSeparator()
        toolbar.addAction(self.zoom_out_action)
        self.zoom_label = QLabel("85%")
        self.zoom_label.setMinimumWidth(44)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar.addWidget(self.zoom_label)
        toolbar.addAction(self.zoom_in_action)
        toolbar.addAction(self.fit_action)
        toolbar.addSeparator()
        toolbar.addAction(self.select_action)
        toolbar.addAction(self.note_action)
        space_hint = QLabel("Giữ Space để di chuyển")
        space_hint.setObjectName("mutedLabel")
        toolbar.addWidget(space_hint)
        toolbar.addAction(self.delete_annotation_action)
        toolbar.addSeparator()
        toolbar.addAction(self.show_edits_action)
        toolbar.addAction(self.autosave_action)
        toolbar.addAction(self.save_action)

    def _create_menu(self) -> None:
        file_menu = self.menuBar().addMenu("Tệp")
        file_menu.addAction(self.import_action)
        file_menu.addAction(self.new_vocabulary_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.export_action)
        file_menu.addSeparator()
        file_menu.addAction("Thoát", self.close, QKeySequence.StandardKey.Quit)

        edit_menu = self.menuBar().addMenu("Chỉnh sửa")
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.delete_annotation_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.show_edits_action)
        edit_menu.addAction(self.autosave_action)

    def _connect_signals(self) -> None:
        self.viewer.annotations_created.connect(self._add_annotations)
        self.viewer.annotation_updated.connect(self._update_annotation)
        self.viewer.selection_changed.connect(self.delete_annotation_action.setEnabled)
        self.viewer.zoom_changed.connect(lambda value: self.zoom_label.setText(f"{value}%"))
        self.library_panel.import_requested.connect(self.choose_pdf)
        self.library_panel.create_requested.connect(self.create_vocabulary_project)
        self.library_panel.project_selected.connect(self.open_project)
        self.library_panel.delete_requested.connect(self.delete_project)
        self.vocabulary.cards_changed.connect(self._refresh_library)

    def _set_pdf_actions_enabled(self, enabled: bool) -> None:
        for action in (
            self.save_action,
            self.export_action,
            self.zoom_out_action,
            self.zoom_in_action,
            self.fit_action,
            self.select_action,
            self.note_action,
            self.show_edits_action,
            self.undo_action,
        ):
            action.setEnabled(enabled)

    def _refresh_library(self) -> None:
        selected_id = self.current_project.id if self.current_project else None
        self.library_panel.set_projects(self.library.projects(), selected_id)

    def choose_pdf(self) -> None:
        start_directory = self.settings.value("last_directory", str(Path.home()), str)
        path, _ = QFileDialog.getOpenFileName(
            self, "Nhập bài học PDF", start_directory, "PDF (*.pdf)"
        )
        if path:
            self.open_pdf(path)

    def open_pdf(self, path: str) -> None:
        try:
            validation = PdfDocumentSession(path)
            title = validation.title
            validation.close()
            project = self.library.import_pdf(path, title)
        except (OSError, RuntimeError, ValueError) as error:
            QMessageBox.critical(self, "Không thể nhập PDF", str(error))
            return
        self.settings.setValue("last_directory", str(Path(path).resolve().parent))
        self._refresh_library()
        self.library_panel.select_project(project.id)

    def create_vocabulary_project(self) -> None:
        title, accepted = QInputDialog.getText(
            self,
            "Bộ từ vựng mới",
            "Tên bài học hoặc chủ đề:",
            text="Bộ từ vựng mới",
        )
        if not accepted:
            return
        try:
            project = self.library.create_vocabulary_project(title)
        except ValueError as error:
            QMessageBox.warning(self, "Tên chưa hợp lệ", str(error))
            return
        self._refresh_library()
        self.library_panel.select_project(project.id)

    def open_project(self, project_id: str) -> None:
        if self.current_project and self.current_project.id == project_id:
            return
        if not self._can_close_current():
            if self.current_project:
                self.library_panel.select_project(self.current_project.id)
            return
        project = self.library.project(project_id)
        if project is None:
            return
        if self.session:
            self.session.close()
            self.session = None

        if project.kind == "pdf":
            try:
                self.session = PdfDocumentSession(project.path)
            except (OSError, RuntimeError, ValueError) as error:
                QMessageBox.critical(self, "Không thể mở PDF", str(error))
                return
            self.viewer.set_document(self.session)
            self._set_pdf_actions_enabled(True)
            status = (
                f"{self.session.page_count} trang • "
                f"{len(self.session.annotations)} chỉnh sửa đã lưu"
            )
        else:
            self.viewer.set_document(None, f"{project.title}\nBộ từ vựng độc lập")
            self._set_pdf_actions_enabled(False)
            status = "Bộ từ vựng không có PDF"

        self.current_project = project
        self.library.touch_project(project.id)
        self.vocabulary.set_document(project.id, project.title)
        self.settings.setValue("last_project", project.id)
        self.setWindowTitle(f"{project.title} — LinguaPDF")
        self.statusBar().showMessage(status, 5000)
        self._refresh_library()

    def delete_project(self, project_id: str) -> None:
        project = self.library.project(project_id)
        if project is None:
            return
        response = QMessageBox.question(
            self,
            "Xóa khỏi thư viện",
            f"Xóa “{project.title}”, toàn bộ từ vựng và lịch sử ôn của tài liệu này?",
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
            self.vocabulary.set_document(None)
            self._set_pdf_actions_enabled(False)
            self.setWindowTitle("LinguaPDF — PDF & Flashcards")
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
            self.statusBar().showMessage("Có thay đổi chưa lưu", 3000)

    def _save_if_enabled(self) -> None:
        if self.autosave_action.isChecked():
            self.save_annotations(silent=True)
        else:
            self.statusBar().showMessage("Có thay đổi chưa lưu", 3000)

    def save_annotations(self, _checked: bool = False, *, silent: bool = False) -> None:
        if not self.session:
            return
        try:
            saved_path = self.session.save_annotations()
        except OSError as error:
            QMessageBox.critical(self, "Không thể lưu", str(error))
            return
        if not silent:
            self.statusBar().showMessage(f"Đã lưu thay đổi: {saved_path.name}", 5000)

    def export_pdf(self) -> None:
        if not self.session:
            return
        default_name = Path.home() / f"{self.session.path.stem}.annotated.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "Xuất PDF đã chỉnh sửa", str(default_name), "PDF (*.pdf)"
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            exported = self.session.export_annotated_pdf(path)
        except (OSError, RuntimeError, ValueError) as error:
            QMessageBox.critical(self, "Không thể xuất PDF", str(error))
            return
        self.statusBar().showMessage(f"Đã xuất {exported.name}", 6000)

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

    def _autosave_changed(self, enabled: bool) -> None:
        self.settings.setValue("autosave", enabled)
        if enabled:
            if self.session and self.session.dirty:
                self.save_annotations(silent=True)
        else:
            self.annotation_save_timer.stop()
        state = "bật" if enabled else "tắt"
        self.statusBar().showMessage(f"Tự động lưu đã {state}", 3000)

    def _can_close_current(self) -> bool:
        if not self.session or not self.session.dirty:
            return True
        if self.autosave_action.isChecked():
            self.annotation_save_timer.stop()
            self.save_annotations(silent=True)
            return not self.session.dirty
        response = QMessageBox.warning(
            self,
            "Thay đổi chưa lưu",
            "Bạn có muốn lưu các highlight và ghi chú trước khi tiếp tục?",
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

