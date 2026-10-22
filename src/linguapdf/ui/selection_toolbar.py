from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QFrame, QHBoxLayout, QToolButton

from linguapdf.ui.i18n import tr


class SelectionToolbar(QDialog):
    """Compact, icon-only popup shown for a PDF text selection."""

    action_selected = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("selectionToolbar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.choice: tuple[str, str, str] | None = None
        self.finished.connect(self._remove_global_filter)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(7, 6, 7, 6)
        layout.setSpacing(4)

        for name, color in (
            (tr("highlight_yellow"), "#FDE047"),
            (tr("highlight_green"), "#86EFAC"),
            (tr("highlight_pink"), "#FDA4AF"),
            (tr("highlight_blue"), "#93C5FD"),
        ):
            button = self._button(_color_icon(color), name)
            button.clicked.connect(
                lambda _checked=False, value=color: self._choose("format", "highlight", value)
            )
            layout.addWidget(button)

        layout.addWidget(self._separator())

        underline = self._button(_text_decoration_icon("U", underline=True), tr("underline"))
        underline.clicked.connect(lambda: self._choose("format", "underline", "#4F46E5"))
        layout.addWidget(underline)

        strike = self._button(_text_decoration_icon("S", strike=True), tr("strike"))
        strike.clicked.connect(lambda: self._choose("format", "strike", "#E11D48"))
        layout.addWidget(strike)

        layout.addWidget(self._separator())

        vocabulary = self._button(_vocabulary_icon(), tr("quick_add"))
        vocabulary.clicked.connect(lambda: self._choose("vocabulary", "", ""))
        layout.addWidget(vocabulary)

    def open_at(self, global_position: QPoint) -> None:
        self.adjustSize()
        screen = QGuiApplication.screenAt(global_position) or QGuiApplication.primaryScreen()
        available = screen.availableGeometry()
        x = min(
            max(global_position.x() - self.width() // 2, available.left()),
            available.right() - self.width(),
        )
        y = global_position.y() - self.height() - 12
        if y < available.top():
            y = global_position.y() + 14
        self.move(x, y)
        application = QApplication.instance()
        if application:
            application.installEventFilter(self)
        self.show()
        self.raise_()
        self.activateWindow()

    def _choose(self, action_type: str, kind: str, color: str) -> None:
        self.choice = (action_type, kind, color)
        self.accept()
        self.action_selected.emit(action_type, kind, color)

    def _remove_global_filter(self, _result: int = 0) -> None:
        application = QApplication.instance()
        if application:
            application.removeEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress and self.isVisible():
            global_position = event.globalPosition().toPoint()
            if not self.frameGeometry().contains(global_position):
                self.reject()
                return True
        return super().eventFilter(watched, event)

    def event(self, event) -> bool:
        if event.type() == QEvent.Type.WindowDeactivate and self.isVisible():
            QTimer.singleShot(0, self.reject)
        return super().event(event)

    @staticmethod
    def _button(icon: QIcon, tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName("selectionToolButton")
        button.setIcon(icon)
        button.setIconSize(QSize(20, 20))
        button.setFixedSize(32, 32)
        button.setToolTip(tooltip)
        button.setAutoRaise(True)
        return button

    @staticmethod
    def _separator() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setObjectName("selectionSeparator")
        line.setFixedHeight(24)
        return line


def _canvas() -> QPixmap:
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    return pixmap


def _color_icon(color: str) -> QIcon:
    pixmap = _canvas()
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(color).darker(125), 1))
    painter.setBrush(QColor(color))
    painter.drawRoundedRect(QRectF(3.5, 3.5, 17, 17), 4, 4)
    painter.end()
    return QIcon(pixmap)


def _text_decoration_icon(letter: str, *, underline: bool = False, strike: bool = False) -> QIcon:
    pixmap = _canvas()
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QColor("#64748B"))
    painter.setFont(QFont("Inter", 13, QFont.Weight.DemiBold))
    painter.drawText(QRectF(0, 0, 24, 22), Qt.AlignmentFlag.AlignCenter, letter)
    line_y = 20 if underline else 12
    if underline or strike:
        painter.setPen(QPen(QColor("#64748B"), 1.8))
        painter.drawLine(5, line_y, 19, line_y)
    painter.end()
    return QIcon(pixmap)


def _vocabulary_icon() -> QIcon:
    pixmap = _canvas()
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor("#4F46E5"), 1.5))
    painter.setBrush(QColor("#EEF2FF"))
    painter.drawRoundedRect(QRectF(3, 5, 14, 15), 2.5, 2.5)
    painter.drawLine(7, 9, 13, 9)
    painter.drawLine(7, 13, 13, 13)
    painter.setPen(QPen(QColor("#16A34A"), 2))
    painter.drawLine(18, 7, 23, 7)
    painter.drawLine(20.5, 4.5, 20.5, 9.5)
    painter.end()
    return QIcon(pixmap)
