from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pymupdf
from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsProxyWidget,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QPinchGesture,
    QToolButton,
)

from linguapdf.domain.models import Annotation
from linguapdf.services.pdf_service import PdfDocumentSession
from linguapdf.ui.i18n import tr
from linguapdf.ui.selection_toolbar import SelectionToolbar


@dataclass(slots=True)
class PageLayout:
    page_index: int
    bounds: QRectF
    pixmap_item: QGraphicsPixmapItem


@dataclass(slots=True)
class TextSelection:
    rects: list[tuple[float, float, float, float]]
    text: str


@dataclass(slots=True)
class SearchMatch:
    page_index: int
    rect: tuple[float, float, float, float]


class EditableTextItem(QGraphicsTextItem):
    def __init__(
        self,
        text: str,
        on_change: Callable[[str], None],
        on_focus: Callable[[], None],
        parent=None,
    ):
        super().__init__(text, parent)
        self._on_change = on_change
        self._on_focus = on_focus
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self.setTabChangesFocus(True)
        self.document().contentsChanged.connect(lambda: self._on_change(self.toPlainText().strip()))

    def mousePressEvent(self, event) -> None:
        self._on_focus()
        super().mousePressEvent(event)

    def focusOutEvent(self, event) -> None:
        self._on_change(self.toPlainText().strip())
        super().focusOutEvent(event)

    def paint(self, painter, option, widget=None) -> None:
        super().paint(painter, option, widget)
        if self.toPlainText():
            return
        painter.save()
        painter.setPen(QColor("#94A3B8"))
        painter.drawText(
            self.boundingRect().adjusted(3, 2, -3, -2),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            tr("note_placeholder"),
        )
        painter.restore()


class NoteResizeHandle(QGraphicsEllipseItem):
    def __init__(self, note: NoteGraphicsItem):
        super().__init__(note)
        self.note = note
        self._start_scene_position: QPointF | None = None
        self._start_width = 0.0
        self.setBrush(QColor("#FFFFFF"))
        self.setPen(QPen(QColor("#0A70D1"), 2))
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setZValue(4)

    def mousePressEvent(self, event) -> None:
        self.note.setSelected(True)
        self._start_scene_position = event.scenePos()
        self._start_width = self.note.rect().width()
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._start_scene_position is None:
            return
        delta = event.scenePos().x() - self._start_scene_position.x()
        self.note.resize_to(self._start_width + delta)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._start_scene_position = None
        self.note.finish_geometry_change()
        event.accept()


class NoteGraphicsItem(QGraphicsRectItem):
    def __init__(
        self,
        annotation: Annotation,
        scene_rect: QRectF,
        page_bounds: QRectF,
        zoom: float,
        on_text_change: Callable[[str], None],
        on_move: Callable[[QRectF], None],
        on_style_change: Callable[[float, str], None],
        on_delete: Callable[[], None],
    ):
        super().__init__(QRectF(0, 0, scene_rect.width(), scene_rect.height()))
        self._page_bounds = page_bounds
        self._on_move = on_move
        self._on_text_change = on_text_change
        self._on_style_change = on_style_change
        self._font_size = annotation.font_size
        self._text_color = annotation.text_color
        self._zoom = zoom
        self._initializing = True
        self._minimum_width = max(100.0, 112.0 * zoom)
        self.setPos(scene_rect.topLeft())
        self.setBrush(Qt.BrushStyle.NoBrush)
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setData(0, annotation.id)
        self.setZValue(8)

        self.drag_handle = QGraphicsRectItem(self)
        self.drag_handle.setBrush(QColor("#0A70D1"))
        self.drag_handle.setPen(QPen(Qt.PenStyle.NoPen))
        self.drag_handle.setCursor(Qt.CursorShape.SizeAllCursor)
        self.drag_handle.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.drag_handle.setZValue(3)
        self.drag_dots = QGraphicsSimpleTextItem("⋮", self)
        self.drag_dots.setBrush(QColor("#FFFFFF"))
        self.drag_dots.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.drag_dots.setZValue(4)

        self.editor = EditableTextItem(
            annotation.text,
            self._content_changed,
            lambda: self.setSelected(True),
            self,
        )
        self.editor.setDefaultTextColor(QColor(self._text_color))
        self.editor.document().setDocumentMargin(2)

        self.resize_handle = NoteResizeHandle(self)
        self.toolbar = self._create_toolbar(on_delete)
        self._layout_children()
        self._initializing = False
        if self._fit_height_to_content():
            QTimer.singleShot(0, self.finish_geometry_change)
        self._update_controls()

    def _create_toolbar(self, on_delete: Callable[[], None]) -> QGraphicsProxyWidget:
        frame = QFrame()
        frame.setObjectName("noteToolbar")
        row = QHBoxLayout(frame)
        row.setContentsMargins(5, 4, 5, 4)
        row.setSpacing(3)
        for color in ("#2563EB", "#DC2626", "#16A34A", "#111827"):
            button = QToolButton(frame)
            button.setObjectName("noteColorButton")
            button.setText("A")
            button.setToolTip(tr("note_text_color"))
            button.setStyleSheet(f"color: {color}; font-weight: 800;")
            button.clicked.connect(lambda _checked=False, value=color: self.set_text_color(value))
            row.addWidget(button)
        for label, delta, tooltip in (
            ("A−", -1.0, tr("note_smaller")),
            ("A+", 1.0, tr("note_larger")),
        ):
            button = QToolButton(frame)
            button.setObjectName("noteToolButton")
            button.setText(label)
            button.setToolTip(tooltip)
            button.clicked.connect(
                lambda _checked=False, amount=delta: self.change_font_size(amount)
            )
            row.addWidget(button)
        delete_button = QToolButton(frame)
        delete_button.setObjectName("noteDeleteButton")
        delete_button.setText("×")
        delete_button.setToolTip(tr("delete_selection"))
        delete_button.clicked.connect(on_delete)
        row.addWidget(delete_button)
        proxy = QGraphicsProxyWidget(self)
        proxy.setWidget(frame)
        proxy.setZValue(5)
        return proxy

    def _layout_children(self) -> None:
        width = self.rect().width()
        height = self.rect().height()
        handle_width = max(9.0, 10.0 * self._zoom)
        self.drag_handle.setRect(0, 0, handle_width, height)
        self.drag_dots.setFont(QFont("Inter", max(8, round(10 * self._zoom)), QFont.Weight.Bold))
        self.drag_dots.setPos(
            max(-1.0, (handle_width - self.drag_dots.boundingRect().width()) / 2),
            max(0.0, (height - self.drag_dots.boundingRect().height()) / 2),
        )
        self.editor.setFont(QFont("Inter", max(8, round(self._font_size * self._zoom))))
        self.editor.setTextWidth(max(55.0, width - handle_width - 10.0))
        self.editor.setPos(handle_width + 5.0, 2.0)
        diameter = max(11.0, 12.0 * self._zoom)
        self.resize_handle.setRect(0, 0, diameter, diameter)
        self.resize_handle.setPos(width - diameter / 2, height / 2 - diameter / 2)
        toolbar_width = self.toolbar.boundingRect().width()
        self.toolbar.setPos(max(0.0, width - toolbar_width), -self.toolbar.boundingRect().height() - 6)

    def _content_changed(self, text: str) -> None:
        if self._initializing:
            return
        if self._fit_height_to_content():
            self.finish_geometry_change()
        self._on_text_change(text)

    def _fit_height_to_content(self) -> bool:
        minimum_height = max(24.0, self._font_size * self._zoom + 9.0)
        document_height = self.editor.document().size().height() + 3.0
        available_height = max(1.0, self._page_bounds.bottom() - self.pos().y())
        wanted_height = min(max(minimum_height, document_height), available_height)
        if abs(wanted_height - self.rect().height()) <= 0.75:
            return False
        self.setRect(0, 0, self.rect().width(), wanted_height)
        self._layout_children()
        return True

    def resize_to(self, width: float) -> None:
        maximum = max(self._minimum_width, self._page_bounds.right() - self.pos().x())
        width = min(maximum, max(self._minimum_width, width))
        self.setRect(0, 0, width, self.rect().height())
        self._layout_children()
        self._fit_height_to_content()

    def finish_geometry_change(self) -> None:
        self._on_move(self.mapRectToScene(self.rect()))

    def set_text_color(self, color: str) -> None:
        self._text_color = color
        self.editor.setDefaultTextColor(QColor(color))
        self._on_style_change(self._font_size, self._text_color)

    def change_font_size(self, delta: float) -> None:
        self._font_size = min(32.0, max(8.0, self._font_size + delta))
        self._layout_children()
        self._content_changed(self.editor.toPlainText().strip())
        self._on_style_change(self._font_size, self._text_color)

    def focus_editor(self) -> None:
        self.setSelected(True)
        self.editor.setFocus(Qt.FocusReason.MouseFocusReason)
        cursor = self.editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.editor.setTextCursor(cursor)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self.finish_geometry_change()

    def _update_controls(self, selected: bool | None = None) -> None:
        selected = self.isSelected() if selected is None else selected
        self.toolbar.setVisible(selected)
        self.drag_handle.setVisible(selected)
        self.drag_dots.setVisible(selected)
        self.resize_handle.setVisible(selected)
        if selected:
            pen = QPen(QColor("#0A70D1"), max(1.2, self._zoom))
            pen.setStyle(Qt.PenStyle.DashLine)
            self.setPen(pen)
        else:
            self.setPen(QPen(Qt.PenStyle.NoPen))

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            position = value
            width = self.rect().width()
            height = self.rect().height()
            x = min(max(position.x(), self._page_bounds.left()), self._page_bounds.right() - width)
            y = min(max(position.y(), self._page_bounds.top()), self._page_bounds.bottom() - height)
            return QPointF(x, y)
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._update_controls(bool(value))
        return super().itemChange(change, value)


class PdfViewer(QGraphicsView):
    annotations_created = Signal(object)
    annotation_updated = Signal(str, object, object)
    annotation_style_updated = Signal(str, float, str)
    annotation_delete_requested = Signal(str)
    selection_changed = Signal(bool)
    zoom_changed = Signal(int)
    quick_vocabulary_requested = Signal(str)

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
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.grabGesture(Qt.GestureType.PinchGesture)
        self.viewport().grabGesture(Qt.GestureType.PinchGesture)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
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
        self._temporary_selection_items: list[QGraphicsRectItem] = []
        self._selection_toolbar: SelectionToolbar | None = None
        self._search_matches: list[SearchMatch] = []
        self._search_items: list[QGraphicsRectItem] = []
        self._search_index = -1
        self._search_query = ""
        self._word_cache: dict[int, list[tuple]] = {}
        self._space_pan_active = False
        self._gesture_render_timer = QTimer(self)
        self._gesture_render_timer.setSingleShot(True)
        self._gesture_render_timer.setInterval(45)
        self._gesture_render_timer.timeout.connect(
            lambda: self.render_document(preserve_scroll=True)
        )
        self._empty_title = tr("choose_document")
        self._empty_title_is_default = True
        self.set_mode("select")
        self.render_document()

    def set_document(self, session: PdfDocumentSession | None, empty_title: str = "") -> None:
        self.session = session
        self._word_cache.clear()
        self.clear_search()
        self._empty_title = empty_title or tr("choose_document")
        self._empty_title_is_default = not bool(empty_title)
        self.zoom = 0.85
        self.render_document()
        if session:
            QTimer.singleShot(0, self.fit_width)

    def retranslate_ui(self) -> None:
        if self._empty_title_is_default:
            self._empty_title = tr("choose_document")
        self.render_document(preserve_scroll=True)

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        if self._space_pan_active:
            return
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        cursor = Qt.CursorShape.ArrowCursor if mode == "select" else Qt.CursorShape.CrossCursor
        self.viewport().setCursor(cursor)

    def zoom_in(self) -> None:
        self.zoom = min(2.5, self.zoom * 1.16)
        self.render_document(preserve_scroll=True)

    def zoom_out(self) -> None:
        self.zoom = max(0.35, self.zoom / 1.16)
        self.render_document(preserve_scroll=True)

    def _apply_gesture_zoom(self, factor: float) -> None:
        if not self.session or factor <= 0:
            return
        new_zoom = max(0.35, min(2.5, self.zoom * factor))
        if abs(new_zoom - self.zoom) < 0.0001:
            return
        self.zoom = new_zoom
        if not self._gesture_render_timer.isActive():
            self._gesture_render_timer.start()

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
        self._temporary_selection_items.clear()
        self._search_items.clear()
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
        self._render_search_highlights()
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
        title.setDefaultTextColor(self.palette().color(QPalette.ColorRole.Text))
        title.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        title.setPos(60, 62)
        hint = scene.addText(tr("empty_hint"))
        hint.setDefaultTextColor(self.palette().color(QPalette.ColorRole.PlaceholderText))
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
                    self._render_scale,
                    lambda text, item_id=annotation.id: self._note_text_changed(item_id, text),
                    lambda moved, item_id=annotation.id, page_layout=layout: self._note_moved(
                        item_id, page_layout, moved
                    ),
                    lambda font_size, text_color, item_id=annotation.id: self.annotation_style_updated.emit(
                        item_id, font_size, text_color
                    ),
                    lambda item_id=annotation.id: QTimer.singleShot(
                        0, lambda: self.annotation_delete_requested.emit(item_id)
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

    def search_text(self, query: str) -> tuple[int, int]:
        self._search_query = query.strip()
        self._search_matches = []
        self._search_index = -1
        if self.session and self._search_query:
            for page_index, page in enumerate(self.session.document):
                for rect in page.search_for(self._search_query):
                    self._search_matches.append(
                        SearchMatch(page_index, (rect.x0, rect.y0, rect.x1, rect.y1))
                    )
        if self._search_matches:
            self._search_index = 0
        self._render_search_highlights()
        self._focus_search_match()
        return self.search_position()

    def next_search_match(self) -> tuple[int, int]:
        if self._search_matches:
            self._search_index = (self._search_index + 1) % len(self._search_matches)
            self._render_search_highlights()
            self._focus_search_match()
        return self.search_position()

    def previous_search_match(self) -> tuple[int, int]:
        if self._search_matches:
            self._search_index = (self._search_index - 1) % len(self._search_matches)
            self._render_search_highlights()
            self._focus_search_match()
        return self.search_position()

    def search_position(self) -> tuple[int, int]:
        return (
            self._search_index + 1 if self._search_index >= 0 else 0,
            len(self._search_matches),
        )

    def clear_search(self) -> None:
        for item in self._search_items:
            if item.scene() is self.scene():
                self.scene().removeItem(item)
        self._search_items.clear()
        self._search_matches.clear()
        self._search_index = -1
        self._search_query = ""

    def _render_search_highlights(self) -> None:
        for item in self._search_items:
            if item.scene() is self.scene():
                self.scene().removeItem(item)
        self._search_items.clear()
        for index, match in enumerate(self._search_matches):
            if match.page_index >= len(self._page_layouts):
                continue
            layout = self._page_layouts[match.page_index]
            annotation = Annotation(page=match.page_index, kind="search", rect=match.rect)
            rect = self._annotation_scene_rect(layout, annotation)
            active = index == self._search_index
            fill = QColor("#FB923C" if active else "#FDE047")
            fill.setAlpha(150 if active else 92)
            pen = QPen(QColor("#EA580C"), 1.5) if active else QPen(Qt.PenStyle.NoPen)
            item = self.scene().addRect(rect, pen, fill)
            item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            item.setZValue(4)
            self._search_items.append(item)

    def _focus_search_match(self) -> None:
        if self._search_index < 0 or self._search_index >= len(self._search_matches):
            return
        match = self._search_matches[self._search_index]
        if match.page_index >= len(self._page_layouts):
            return
        rect = self._annotation_scene_rect(
            self._page_layouts[match.page_index],
            Annotation(page=match.page_index, kind="search", rect=match.rect),
        )
        self.ensureVisible(rect, 90, 140)
        QTimer.singleShot(0, self._render_visible_pages)

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
            width = min(175.0, page.rect.width - point.x)
            height = min(30.0, page.rect.height - point.y)
            if width >= 80 and height >= 24:
                annotation = Annotation(
                    page=layout.page_index,
                    kind="text",
                    rect=(point.x, point.y, point.x + width, point.y + height),
                    color="#FFFFFF",
                    font_size=14.0,
                    text_color="#2563EB",
                )
                self.annotations_created.emit([annotation])
            event.accept()
            return

        if self.mode == "select":
            if not self._word_at(layout, scene_position):
                self._clear_temporary_selection()
                super().mousePressEvent(event)
                return
            self._selection_origin = scene_position
            self._selection_layout = layout
            self._clear_temporary_selection()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._selection_origin is not None and self._selection_layout is not None:
            current = self.mapToScene(event.position().toPoint())
            if self._drag_distance(self._selection_origin, current) >= 4:
                result = self._selection_between(
                    self._selection_layout, self._selection_origin, current
                )
                self._show_temporary_selection(self._selection_layout, result.rects)
            event.accept()
            return
        if self.mode == "select" and not self._space_pan_active:
            self._update_hover_cursor(event.position().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._selection_origin is not None and self._selection_layout is not None:
            current = self.mapToScene(event.position().toPoint())
            click_point = self._selection_origin
            layout = self._selection_layout
            self._selection_origin = None
            self._selection_layout = None
            if self._drag_distance(click_point, current) >= 4:
                result = self._selection_between(layout, click_point, current)
                if result.rects:
                    self._show_temporary_selection(layout, result.rects)
                    self._show_selection_menu(layout.page_index, result, event)
                else:
                    self._clear_temporary_selection()
            else:
                self._clear_temporary_selection()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if (
            self.session
            and self.mode == "select"
            and event.button() == Qt.MouseButton.LeftButton
            and not self._space_pan_active
        ):
            scene_position = self.mapToScene(event.position().toPoint())
            layout = self._layout_at(scene_position)
            if layout and self._word_at(layout, scene_position):
                result = self._selection_between(layout, scene_position, scene_position)
                if result.rects:
                    self._show_temporary_selection(layout, result.rects)
                    self._show_selection_menu(layout.page_index, result, event)
                    event.accept()
                    return
        super().mouseDoubleClickEvent(event)

    def leaveEvent(self, event) -> None:
        if self.mode == "select" and not self._space_pan_active:
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)

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
            delta = event.angleDelta().y() or event.pixelDelta().y()
            factor = 1.0 + max(-0.25, min(0.25, delta / 600.0))
            self._apply_gesture_zoom(factor)
            event.accept()
            return
        super().wheelEvent(event)

    def viewportEvent(self, event) -> bool:
        if (
            event.type() == QEvent.Type.NativeGesture
            and event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture
        ):
            self._apply_gesture_zoom(max(0.5, 1.0 + float(event.value())))
            event.accept()
            return True
        return super().viewportEvent(event)

    def event(self, event) -> bool:
        if (
            event.type() == QEvent.Type.NativeGesture
            and event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture
        ):
            self._apply_gesture_zoom(max(0.5, 1.0 + float(event.value())))
            event.accept()
            return True
        if event.type() == QEvent.Type.Gesture:
            pinch = event.gesture(Qt.GestureType.PinchGesture)
            if pinch and pinch.changeFlags() & QPinchGesture.ChangeFlag.ScaleFactorChanged:
                self._apply_gesture_zoom(float(pinch.scaleFactor()))
                event.accept()
                return True
        return super().event(event)

    def _show_selection_menu(
        self, page_index: int, selection: TextSelection, event: QMouseEvent
    ) -> None:
        self.viewport().update()
        self._open_selection_toolbar(
            page_index, selection, event.globalPosition().toPoint()
        )

    def _open_selection_toolbar(
        self, page_index: int, selection: TextSelection, global_position: QPoint
    ) -> None:
        if self._selection_toolbar:
            self._selection_toolbar.reject()
        toolbar = SelectionToolbar(self)
        self._selection_toolbar = toolbar
        toolbar.action_selected.connect(
            lambda action_type, kind, color: self._apply_selection_action(
                page_index, selection, action_type, kind, color
            )
        )
        toolbar.finished.connect(
            lambda _result, current=toolbar: self._selection_toolbar_finished(current)
        )
        toolbar.open_at(global_position)

    def _apply_selection_action(
        self,
        page_index: int,
        selection: TextSelection,
        action_type: str,
        kind: str,
        color: str,
    ) -> None:
        self._clear_temporary_selection()
        if action_type == "vocabulary":
            self.quick_vocabulary_requested.emit(selection.text)
            return
        annotations = [
            Annotation(page=page_index, kind=kind, rect=rect, color=color)
            for rect in selection.rects
        ]
        self.annotations_created.emit(annotations)

    def _selection_toolbar_finished(self, toolbar: SelectionToolbar) -> None:
        self._clear_temporary_selection()
        if self._selection_toolbar is toolbar:
            self._selection_toolbar = None
        toolbar.deleteLater()

    def _text_selection(
        self, layout: PageLayout, selection: QRectF, click_point: QPointF
    ) -> TextSelection:
        if selection.width() < 5 and selection.height() < 5:
            return self._selection_between(layout, click_point, click_point)
        return self._selection_between(layout, selection.topLeft(), selection.bottomRight())

    def _selection_between(
        self, layout: PageLayout, anchor: QPointF, cursor: QPointF
    ) -> TextSelection:
        words = self._words_for_page(layout.page_index)
        if not words:
            return TextSelection([], "")
        anchor_index = self._word_index_at(layout, anchor)
        cursor_index = self._word_index_at(layout, cursor)
        if anchor_index is None:
            return TextSelection([], "")
        if cursor_index is None:
            cursor_index = self._nearest_word_index(layout, cursor)
        if cursor_index is None:
            return TextSelection([], "")
        start, end = sorted((anchor_index, cursor_index))
        return self._selection_from_words(words[start : end + 1])

    @staticmethod
    def _selection_from_words(selected_words: list[tuple]) -> TextSelection:
        groups: dict[tuple[int, int], pymupdf.Rect] = {}
        for word in selected_words:
            key = (int(word[5]), int(word[6]))
            word_rect = pymupdf.Rect(word[:4])
            groups[key] = groups[key] | word_rect if key in groups else word_rect
        rects = [(rect.x0, rect.y0, rect.x1, rect.y1) for rect in groups.values()]
        text = " ".join(str(word[4]) for word in selected_words).strip()
        return TextSelection(rects, text)

    def _words_for_page(self, page_index: int) -> list[tuple]:
        if page_index not in self._word_cache and self.session:
            self._word_cache[page_index] = self.session.document[page_index].get_text(
                "words", sort=True
            )
        return self._word_cache.get(page_index, [])

    def _word_at(self, layout: PageLayout, scene_position: QPointF) -> tuple | None:
        index = self._word_index_at(layout, scene_position)
        words = self._words_for_page(layout.page_index)
        return words[index] if index is not None else None

    def _word_index_at(self, layout: PageLayout, scene_position: QPointF) -> int | None:
        point = self._scene_to_pdf_point(layout, scene_position)
        return next(
            (
                index
                for index, word in enumerate(self._words_for_page(layout.page_index))
                if pymupdf.Rect(word[:4]).contains(point)
            ),
            None,
        )

    def _nearest_word_index(self, layout: PageLayout, scene_position: QPointF) -> int | None:
        words = self._words_for_page(layout.page_index)
        if not words:
            return None
        point = self._scene_to_pdf_point(layout, scene_position)
        lines: dict[tuple[int, int], list[tuple[int, tuple]]] = {}
        for index, word in enumerate(words):
            lines.setdefault((int(word[5]), int(word[6])), []).append((index, word))

        def line_distance(line_words: list[tuple[int, tuple]]) -> float:
            top = min(word[1] for _index, word in line_words)
            bottom = max(word[3] for _index, word in line_words)
            if top <= point.y <= bottom:
                return 0.0
            return min(abs(point.y - top), abs(point.y - bottom))

        closest_line = min(lines.values(), key=line_distance)
        if point.x <= closest_line[0][1][0]:
            return closest_line[0][0]
        if point.x >= closest_line[-1][1][2]:
            return closest_line[-1][0]
        return min(
            closest_line,
            key=lambda indexed_word: abs(point.x - (indexed_word[1][0] + indexed_word[1][2]) / 2),
        )[0]

    @staticmethod
    def _drag_distance(first: QPointF, second: QPointF) -> float:
        return abs(first.x() - second.x()) + abs(first.y() - second.y())

    def _update_hover_cursor(self, viewport_position) -> None:
        scene_position = self.mapToScene(viewport_position)
        layout = self._layout_at(scene_position)
        over_word = bool(layout and self._word_at(layout, scene_position))
        cursor = Qt.CursorShape.IBeamCursor if over_word else Qt.CursorShape.ArrowCursor
        self.viewport().setCursor(cursor)

    def _show_temporary_selection(
        self, layout: PageLayout, rects: list[tuple[float, float, float, float]]
    ) -> None:
        self._clear_temporary_selection()
        color = QColor("#4A90E2")
        color.setAlpha(105)
        for rect in rects:
            annotation = Annotation(page=layout.page_index, kind="highlight", rect=rect)
            item = self.scene().addRect(
                self._annotation_scene_rect(layout, annotation),
                QPen(Qt.PenStyle.NoPen),
                color,
            )
            item.setZValue(18)
            item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self._temporary_selection_items.append(item)

    def _clear_temporary_selection(self) -> None:
        for item in self._temporary_selection_items:
            try:
                if item.scene() is self.scene():
                    self.scene().removeItem(item)
            except RuntimeError:
                pass
        self._temporary_selection_items.clear()

    def _layout_at(self, point: QPointF) -> PageLayout | None:
        return next(
            (layout for layout in self._page_layouts if layout.bounds.contains(point)), None
        )

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
