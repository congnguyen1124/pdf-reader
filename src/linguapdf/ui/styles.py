APP_STYLESHEET = """
* {
    font-family: Inter, "SF Pro Text", "Noto Sans", sans-serif;
    font-size: 13px;
    color: #172033;
}
QMainWindow, QWidget#appRoot { background: #F3F6FB; }
QWidget#libraryPanel {
    background-color: #111827;
    border-right: 1px solid #1F2937;
}
QWidget#libraryPanel QLabel { color: #CBD5E1; }
QWidget#libraryPanel QLabel#brandLabel {
    color: #FFFFFF;
    font-size: 22px;
    font-weight: 800;
}
QWidget#libraryPanel QLabel#eyebrowLabel {
    color: #94A3B8;
    font-size: 10px;
    font-weight: 800;
}
QListWidget#projectList {
    background: transparent;
    border: none;
    outline: none;
    color: #E2E8F0;
}
QListWidget#projectList::item {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 9px;
    padding: 10px 9px;
    color: #E2E8F0;
}
QListWidget#projectList::item:hover { background: #1F2937; }
QListWidget#projectList::item:selected {
    background: #312E81;
    border-color: #4F46E5;
    color: #FFFFFF;
}
QPushButton#smallDangerButton {
    padding: 4px 8px;
    color: #FDA4AF;
    background: transparent;
    border-color: #7F1D1D;
}
QToolBar {
    background: #FFFFFF;
    border: none;
    border-bottom: 1px solid #E2E8F0;
    spacing: 6px;
    padding: 7px 10px;
}
QToolBar QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 7px 10px;
    font-weight: 600;
}
QToolBar QToolButton:hover { background: #F1F5F9; }
QToolBar QToolButton:checked {
    color: #FFFFFF;
    background: #4F46E5;
}
QToolButton:disabled, QPushButton:disabled { color: #94A3B8; }
QPushButton {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 7px 12px;
    font-weight: 600;
}
QPushButton:hover { border-color: #818CF8; background: #F8FAFC; }
QPushButton#primaryButton {
    color: #FFFFFF;
    background: #4F46E5;
    border-color: #4F46E5;
}
QPushButton#primaryButton:hover { background: #4338CA; }
QPushButton#dangerButton { color: #BE123C; border-color: #FECDD3; }
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 7px 9px;
    selection-background-color: #6366F1;
}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 2px solid #818CF8;
}
QComboBox::drop-down { border: none; width: 24px; }
QTabWidget::pane { border: none; background: #FFFFFF; }
QTabBar::tab {
    background: #FFFFFF;
    color: #64748B;
    padding: 11px 16px;
    border-bottom: 2px solid transparent;
    font-weight: 600;
}
QTabBar::tab:selected { color: #4F46E5; border-bottom-color: #4F46E5; }
QTableWidget {
    background: #FFFFFF;
    alternate-background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    gridline-color: #EEF2F7;
}
QHeaderView::section {
    background: #F8FAFC;
    border: none;
    border-bottom: 1px solid #E2E8F0;
    padding: 8px;
    color: #475569;
    font-weight: 700;
}
QTableWidget::item { padding: 7px; }
QScrollBar:vertical { width: 10px; background: transparent; margin: 2px; }
QScrollBar::handle:vertical { background: #CBD5E1; border-radius: 5px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSplitter::handle { background: #E2E8F0; width: 1px; }
QStatusBar { background: #FFFFFF; border-top: 1px solid #E2E8F0; color: #64748B; }
QLabel#mutedLabel { color: #64748B; }
QLabel#sectionTitle { font-size: 18px; font-weight: 750; color: #0F172A; }
QLabel#statNumber { font-size: 20px; font-weight: 800; color: #4338CA; }
QFrame#statCard, QFrame#reviewCard {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
}
QGraphicsView { border: none; background: #DCE3ED; }
QMenu {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 9px;
    padding: 6px;
}
QMenu::item { padding: 8px 18px; border-radius: 6px; }
QMenu::item:selected { background: #EEF2FF; color: #4338CA; }
"""

