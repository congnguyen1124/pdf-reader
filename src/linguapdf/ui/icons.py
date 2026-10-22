from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap


def panel_toggle_icon(side: str) -> QIcon:
    icon = QIcon()
    icon.addPixmap(_panel_pixmap(side, active=False), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(_panel_pixmap(side, active=True), QIcon.Mode.Normal, QIcon.State.On)
    return icon


def search_icon() -> QIcon:
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("#64748B"), 2.0)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(QRectF(4.0, 4.0, 11.5, 11.5))
    painter.drawLine(14.0, 14.0, 20.0, 20.0)
    painter.end()
    return QIcon(pixmap)


def explorer_action_icon(kind: str) -> QIcon:
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("#C5C5C5"), 1.45)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    if kind in {"import", "file"}:
        painter.drawRoundedRect(QRectF(3.5, 2.5, 10, 14.5), 1.4, 1.4)
        painter.drawLine(10.5, 2.5, 13.5, 5.5)
    if kind == "import":
        painter.drawLine(15.5, 9, 15.5, 16)
        painter.drawLine(12.8, 13.4, 15.5, 16)
        painter.drawLine(18.2, 13.4, 15.5, 16)
    elif kind == "file":
        painter.drawLine(11.5, 13.5, 18, 13.5)
        painter.drawLine(14.75, 10.25, 14.75, 16.75)
    elif kind == "folder":
        path = QRectF(2.5, 5.5, 13.5, 10.5)
        painter.drawRoundedRect(path, 1.5, 1.5)
        painter.drawLine(3.5, 5.5, 6.5, 3.5)
        painter.drawLine(6.5, 3.5, 10, 3.5)
        painter.drawLine(10, 3.5, 11.5, 5.5)
        painter.drawLine(13.5, 13.5, 19, 13.5)
        painter.drawLine(16.25, 10.75, 16.25, 16.25)
    elif kind == "collapse":
        painter.drawLine(5, 7, 10, 12)
        painter.drawLine(10, 12, 15, 7)
        painter.drawLine(5, 11, 10, 16)
        painter.drawLine(10, 16, 15, 11)
    elif kind == "delete":
        painter.drawRoundedRect(QRectF(6, 6, 8, 11), 1, 1)
        painter.drawLine(4.5, 5, 15.5, 5)
        painter.drawLine(8, 2.8, 12, 2.8)
        painter.drawLine(8.5, 8, 8.5, 14.5)
        painter.drawLine(11.5, 8, 11.5, 14.5)
    painter.end()
    return QIcon(pixmap)


def explorer_folder_icon() -> QIcon:
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#8AA4B0"))
    painter.drawRoundedRect(QRectF(1.5, 5, 15, 10.5), 1.6, 1.6)
    painter.drawRoundedRect(QRectF(2.5, 2.5, 7, 5), 1.2, 1.2)
    painter.end()
    return QIcon(pixmap)


def explorer_workspace_icon(kind: str) -> QIcon:
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = QColor("#E06C75" if kind == "pdf" else "#61AFEF")
    painter.setPen(QPen(color, 1.45))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(QRectF(3, 1.5, 11, 15), 1.4, 1.4)
    painter.drawLine(10, 1.5, 14, 5.5)
    if kind == "pdf":
        painter.setFont(QFont("Inter", 5, QFont.Weight.Bold))
        painter.drawText(QRectF(2.5, 7, 12, 7), Qt.AlignmentFlag.AlignCenter, "PDF")
    else:
        painter.drawLine(6, 8, 11, 8)
        painter.drawLine(6, 11, 11, 11)
    painter.end()
    return QIcon(pixmap)


def _panel_pixmap(side: str, *, active: bool) -> QPixmap:
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    foreground = QColor("#FFFFFF") if active else QColor("#94A3B8")
    panel_fill = QColor(255, 255, 255, 105) if active else QColor("#CBD5E1")
    painter.setPen(QPen(foreground, 1.6))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(QRectF(2.5, 3.5, 19, 17), 3, 3)
    if side == "left":
        painter.fillRect(QRectF(3.5, 4.5, 5.5, 15), panel_fill)
        painter.drawLine(9.5, 4.5, 9.5, 19.5)
    else:
        painter.fillRect(QRectF(15, 4.5, 5.5, 15), panel_fill)
        painter.drawLine(14.5, 4.5, 14.5, 19.5)
    painter.end()
    return pixmap
