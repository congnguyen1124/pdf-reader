from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pymupdf
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QKeyEvent, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsTextItem,
    QGraphicsView,
    QMenu,
)

from linguapdf.domain.models import Annotation
from linguapdf.services.pdf_service import PdfDocumentSession


@dataclass(slots=True)
class PageLayout:
    page_index: int
    bounds: QRectF
    pixmap_item: QGraphicsPixmapItem


class EditableTextItem(QGraphicsTextItem):
    def __init__(self, text: str, on_change: Callable[[str], None], parent=None):
        super().__init__(text, parent)
        self._on_change = on_change
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self.setTabChangesFocus(True)
        self.setDefaultTextColor(QColor("#172033"))
        self.document().contentsChanged.connect(
            lambda: self._on_change(self.toPlainText().strip())
        )

    def focusOutEvent(self, event) -> None:
        self._on_change(self.toPlainText().strip())
        super().focusOutEvent(event)


class NoteGraphicsItem(QGraphicsRectItem):
    def __init__(
        self,
        annotation: Annotation,
        scene_rect: QRectF,
        page_bounds: QRectF,
        zoom: float,
        on_text_change: Callable[[str], None],
        on_move: Callable[[QRectF], None],
    ):
        super().__init__(QRectF(0, 0, scene_rect.width(), scene_rect.height()))
        self._page_bounds = page_bounds
        self._on_move = on_move
        self.setPos(scene_rect.topLeft())
        self.setBrush(QColor("#FEF3A3"))
        self.setPen(QPen(QColor("#EAB308"), max(1.0, zoom)))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setData(0, annotation.id)
        self.setZValue(8)

        header = QGraphicsSimpleTextItem("⠿  Ghi chú — kéo tại đây", self)
        header.setBrush(QColor("#92400E"))
        header.setFont(QFont("Inter", max(7, round(8 * zoom)), QFont.Weight.DemiBold))
        header.setPos(7, 3)
        header.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        self.editor = EditableTextItem(annotation.text, on_text_change, self)
        self.editor.setFont(QFont("Inter", max(8, round(10 * zoom))))
        self.editor.document().setDocumentMargin(2)
        self.editor.setTextWidth(max(60, scene_rect.width() - 14))
        self.editor.setPos(6, max(20, 20 * zoom))

    def focus_editor(self) -> None:
        self.editor.setFocus(Qt.FocusReason.MouseFocusReason)
        cursor = self.editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.editor.setTextCursor(cursor)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self._on_move(self.mapRectToScene(self.rect()).boundingRect())

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            position = value
            width = self.rect().width()
            height = self.rect().height()
            x = min(max(position.x(), self._page_bounds.left()), self._page_bounds.right() - width)
            y = min(max(position.y(), self._page_bounds.top()), self._page_bounds.bottom() - height)
            return QPointF(x, y)
        return super().itemChange(change, value)


class PdfViewer(QGraphicsView):
    annotations_created = Signal(object)
    annotation_updated = Signal(str, object, object)
    selection_changed = Signal(bool)
    zoom_changed = Signal(int)

    PAGE_GAP = 24.0
    RENDER_DPI_SCALE = 1.35

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.scene().selectionChanged.connect(self._emit_selection)

        self.session: PdfDocumentSession | None = None
        self.zoom = 0.85
        self.mode = "select"
        self.show_annotations = True
        self._render_scale = 1.0
        self._page_layouts: list[PageLayout] = []
        self._note_items: dict[str, NoteGraphicsItem] = {}
        self._selection_origin: QPointF | None = None
        self._selection_layout: PageLayout | None = None
        self._selection_rect: QGraphicsRectItem | None = None
        self._space_pan_active = False
        self._empty_title = "Chọn một tài liệu trong thư viện"
        self.set_mode("select")
        self.render_document()

    def set_document(self, session: PdfDocumentSession | None, empty_title: str = "") -> None:
        self.session = session
        self._empty_title = empty_title or "Chọn một tài liệu trong thư viện"
        self.zoom = 0.85
        self.render_document()
        if session:
            QTimer.singleShot(0, self.fit_width)

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        if self._space_pan_active:
            return
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        cursor = (
            Qt.CursorShape.IBeamCursor
            if mode == "select"
            else Qt.CursorShape.CrossCursor
        )
        self.viewport().setCursor(cursor)

    def zoom_in(self) -> None:
        self.zoom = min(2.5, self.zoom * 1.16)
        self.render_document(preserve_scroll=True)

    def zoom_out(self) -> None:
        self.zoom = max(0.35, self.zoom / 1.16)
        self.render_document(preserve_scroll=True)

    def fit_width(self) -> None:
        if not self.session:
            return
        widest = max(page.rect.width for page in self.session.document)
        available = max(240, self.viewport().width() - 54)
        self.zoom = max(0.35, min(2.5, available / (widest * self.RENDER_DPI_SCALE)))
        self.render_document()

    def set_annotations_visible(self, visible: bool) -> None:
        self.show_annotations = visible
        self.render_document(preserve_scroll=True)

    def selected_annotation_ids(self) -> set[str]:
        ids: set[str] = set()
        for item in self.scene().selectedItems():
            annotation_id = item.data(0)
            if annotation_id:
                ids.add(str(annotation_id))
        return ids

    def begin_edit_annotation(self, annotation_id: str) -> None:
        item = self._note_items.get(annotation_id)
        if item:
            item.focus_editor()

    def render_document(self, *, preserve_scroll: bool = False) -> None:
        scroll_bar = self.verticalScrollBar()
        old_ratio = scroll_bar.value() / max(1, scroll_bar.maximum()) if preserve_scroll else 0
        scene = self.scene()
        scene.clear()
        self._page_layouts.clear()
        self._note_items.clear()
        if not self.session:
            self._draw_empty_state()
            return

        self._render_scale = self.zoom * self.RENDER_DPI_SCALE
        page_widths = [page.rect.width * self._render_scale for page in self.session.document]
        max_width = max(page_widths)
        y = self.PAGE_GAP
        for page_index, page in enumerate(self.session.document):
            page_width = page.rect.width * self._render_scale
            page_height = page.rect.height * self._render_scale
            x = self.PAGE_GAP + (max_width - page_width) / 2
            bounds = QRectF(x, y, page_width, page_height)
            frame = scene.addRect(
                bounds.adjusted(-1, -1, 1, 1),
                QPen(QColor("#CBD5E1"), 1),
                QColor("#FFFFFF"),
            )
            frame.setZValue(0)
            page_item = QGraphicsPixmapItem()
            scene.addItem(page_item)
            page_item.setPos(x, y)
            page_item.setZValue(1)
            layout = PageLayout(page_index, bounds, page_item)
            self._page_layouts.append(layout)
            if self.show_annotations:
                self._draw_page_annotations(layout)
            y += page_height + self.PAGE_GAP

        scene.setSceneRect(0, 0, max_width + self.PAGE_GAP * 2, y)
        self._render_visible_pages()
        self.zoom_changed.emit(round(self.zoom * 100))
        if preserve_scroll:
            scroll_bar.setValue(round(old_ratio * scroll_bar.maximum()))

    def _render_visible_pages(self) -> None:
        if not self.session or not self._page_layouts:
            return
        visible = self.mapToScene(self.viewport().rect()).boundingRect()
        preload = max(visible.height() * 1.5, 900)
        render_area = visible.adjusted(0, -preload, 0, preload)
        for layout in self._page_layouts:
            if layout.bounds.intersects(render_area):
                if not layout.pixmap_item.pixmap().isNull():
                    continue
                page = self.session.document[layout.page_index]
                pixmap = page.get_pixmap(
                    matrix=pymupdf.Matrix(self._render_scale, self._render_scale), alpha=False
                )
                image = QImage(
                    pixmap.samples,
                    pixmap.width,
                    pixmap.height,
                    pixmap.stride,
                    QImage.Format.Format_RGB888,
                ).copy()
                layout.pixmap_item.setPixmap(QPixmap.fromImage(image))
            elif not layout.pixmap_item.pixmap().isNull():
                layout.pixmap_item.setPixmap(QPixmap())

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        super().scrollContentsBy(dx, dy)
        QTimer.singleShot(0, self._render_visible_pages)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._render_visible_pages)

    def _draw_empty_state(self) -> None:
        scene = self.scene()
        title = scene.addText(self._empty_title)
        title.setDefaultTextColor(QColor("#334155"))
        title.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        title.setPos(60, 62)
        hint = scene.addText("Nhập PDF hoặc tạo một bộ từ vựng mới ở cột bên trái.")
        hint.setDefaultTextColor(QColor("#64748B"))
        hint.setFont(QFont("Inter", 10))
        hint.setPos(60, 108)
        scene.setSceneRect(QRectF(0, 0, 680, 320))

    def _draw_page_annotations(self, layout: PageLayout) -> None:
        if not self.session:
            return
        for annotation in self.session.annotations_for_page(layout.page_index):
            rect = self._annotation_scene_rect(layout, annotation)
            color = QColor(annotation.color)
            if annotation.kind == "highlight":
                color.setAlpha(95)
                item = self.scene().addRect(rect, QPen(Qt.PenStyle.NoPen), color)
                self._configure_annotation_item(item, annotation.id, 5)
            elif annotation.kind in {"underline", "strike"}:
                line_y = rect.bottom() - 1 if annotation.kind == "underline" else rect.center().y()
                item = self.scene().addLine(
                    rect.left(),
                    line_y,
                    rect.right(),
                    line_y,
                    QPen(color, max(1.5, self.zoom * 1.6)),
                )
                self._configure_annotation_item(item, annotation.id, 6)
            elif annotation.kind == "text":
                item = NoteGraphicsItem(
                    annotation,
                    rect,
                    layout.bounds,
                    self.zoom,
                    lambda text, item_id=annotation.id: self._note_text_changed(item_id, text),
                    lambda moved, item_id=annotation.id, page_layout=layout: self._note_moved(
                        item_id, page_layout, moved
                    ),
                )
                self.scene().addItem(item)
                self._note_items[annotation.id] = item

    def _annotation_scene_rect(self, layout: PageLayout, annotation: Annotation) -> QRectF:
        return QRectF(
            layout.bounds.left() + annotation.rect[0] * self._render_scale,
            layout.bounds.top() + annotation.rect[1] * self._render_scale,
            (annotation.rect[2] - annotation.rect[0]) * self._render_scale,
            (annotation.rect[3] - annotation.rect[1]) * self._render_scale,
        )

    def _configure_annotation_item(self, item: QGraphicsItem, annotation_id: str, z: int) -> None:
        item.setData(0, annotation_id)
        item.setZValue(z)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

    def _emit_selection(self) -> None:
        self.selection_changed.emit(bool(self.selected_annotation_ids()))

    def _note_text_changed(self, annotation_id: str, text: str) -> None:
        self.annotation_updated.emit(annotation_id, None, text)

    def _note_moved(self, annotation_id: str, layout: PageLayout, scene_rect: QRectF) -> None:
        rect = self._scene_to_pdf_rect(layout, scene_rect)
        self.annotation_updated.emit(annotation_id, rect, None)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if (
            not self.session
            or event.button() != Qt.MouseButton.LeftButton
            or self._space_pan_active
        ):
            super().mousePressEvent(event)
            return

        scene_position = self.mapToScene(event.position().toPoint())
        clicked_item = self.itemAt(event.position().toPoint())
        if self._annotation_parent(clicked_item):
            super().mousePressEvent(event)
            return

        layout = self._layout_at(scene_position)
        if not layout:
            super().mousePressEvent(event)
            return

        if self.mode == "note":
            page = self.session.document[layout.page_index]
            point = self._scene_to_pdf_point(layout, scene_position)
            width = min(190.0, page.rect.width - point.x)
            height = min(90.0, page.rect.height - point.y)
            if width >= 80 and height >= 45:
                annotation = Annotation(
                    page=layout.page_index,
                    kind="text",
                    rect=(point.x, point.y, point.x + width, point.y + height),
                    color="#FEF3A3",
                )
                self.annotations_created.emit([annotation])
            event.accept()
            return

        if self.mode == "select":
            self._selection_origin = scene_position
            self._selection_layout = layout
            self._selection_rect = self.scene().addRect(
                QRectF(scene_position, scene_position),
                QPen(QColor("#4F46E5"), 1, Qt.PenStyle.DashLine),
                QColor(99, 102, 241, 35),
            )
            self._selection_rect.setZValue(20)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._selection_origin is not None and self._selection_rect is not None:
            current = self.mapToScene(event.position().toPoint())
            selection = QRectF(self._selection_origin, current).normalized()
            if self._selection_layout:
                selection = selection.intersected(self._selection_layout.bounds)
            self._selection_rect.setRect(selection)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._selection_origin is not None and self._selection_rect is not None:
            selection = self._selection_rect.rect()
            click_point = self._selection_origin
            layout = self._selection_layout
            self.scene().removeItem(self._selection_rect)
            self._selection_origin = None
            self._selection_layout = None
            self._selection_rect = None
            if layout:
                selected_rects = self._selected_word_rects(layout, selection, click_point)
                if selected_rects:
                    self._show_format_menu(layout.page_index, selected_rects, event)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        focus_item = self.scene().focusItem()
        editing_note = isinstance(focus_item, QGraphicsTextItem)
        if (
            event.key() == Qt.Key.Key_Space
            and not event.isAutoRepeat()
            and not editing_note
            and self.session
        ):
            self._space_pan_active = True
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat() and self._space_pan_active:
            self._space_pan_active = False
            self.set_mode(self.mode)
            event.accept()
            return
        super().keyReleaseEvent(event)

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom_in() if event.angleDelta().y() > 0 else self.zoom_out()
            event.accept()
            return
        super().wheelEvent(event)

    def _show_format_menu(
        self, page_index: int, rects: list[tuple[float, float, float, float]], event: QMouseEvent
    ) -> None:
        menu = QMenu(self)
        menu.addSection("Định dạng phần chữ đã chọn")
        options = (
            ("●  Tô vàng", "highlight", "#FDE047"),
            ("●  Tô xanh", "highlight", "#86EFAC"),
            ("●  Tô hồng", "highlight", "#FDA4AF"),
            ("●  Tô lam", "highlight", "#93C5FD"),
            ("U̲  Gạch dưới", "underline", "#4F46E5"),
            ("S̶  Gạch ngang", "strike", "#E11D48"),
        )
        for label, kind, color in options:
            action = menu.addAction(label)
            action.setData((kind, color))
        selected_action = menu.exec(event.globalPosition().toPoint())
        if not selected_action:
            return
        kind, color = selected_action.data()
        annotations = [
            Annotation(page=page_index, kind=kind, rect=rect, color=color) for rect in rects
        ]
        self.annotations_created.emit(annotations)

    def _selected_word_rects(
        self, layout: PageLayout, selection: QRectF, click_point: QPointF
    ) -> list[tuple[float, float, float, float]]:
        if not self.session:
            return []
        page = self.session.document[layout.page_index]
        pdf_selection = pymupdf.Rect(*self._scene_to_pdf_rect(layout, selection))
        click = self._scene_to_pdf_point(layout, click_point)
        click_selection = selection.width() < 5 and selection.height() < 5
        selected_words: list[tuple] = []
        for word in page.get_text("words"):
            word_rect = pymupdf.Rect(word[:4])
            if (click_selection and word_rect.contains(click)) or (
                not click_selection and word_rect.intersects(pdf_selection)
            ):
                selected_words.append(word)
        groups: dict[tuple[int, int], pymupdf.Rect] = {}
        for word in selected_words:
            key = (int(word[5]), int(word[6]))
            word_rect = pymupdf.Rect(word[:4])
            groups[key] = groups[key] | word_rect if key in groups else word_rect
        return [(rect.x0, rect.y0, rect.x1, rect.y1) for rect in groups.values()]

    def _layout_at(self, point: QPointF) -> PageLayout | None:
        return next((layout for layout in self._page_layouts if layout.bounds.contains(point)), None)

    def _scene_to_pdf_point(self, layout: PageLayout, point: QPointF) -> pymupdf.Point:
        return pymupdf.Point(
            (point.x() - layout.bounds.left()) / self._render_scale,
            (point.y() - layout.bounds.top()) / self._render_scale,
        )

    def _scene_to_pdf_rect(
        self, layout: PageLayout, rect: QRectF
    ) -> tuple[float, float, float, float]:
        return (
            (rect.left() - layout.bounds.left()) / self._render_scale,
            (rect.top() - layout.bounds.top()) / self._render_scale,
            (rect.right() - layout.bounds.left()) / self._render_scale,
            (rect.bottom() - layout.bounds.top()) / self._render_scale,
        )

    @staticmethod
    def _annotation_parent(item: QGraphicsItem | None) -> QGraphicsItem | None:
        current = item
        while current:
            if current.data(0):
                return current
            current = current.parentItem()
        return None

