BASE_STYLESHEET = """
* {
    font-family: Inter, "SF Pro Text", "Noto Sans", sans-serif;
    font-size: 13px;
    color: #172033;
}
QMainWindow, QWidget#appRoot { background: #F3F6FB; }
QWidget#libraryPanel {
    background-color: #181A1F;
    border-right: 1px solid #2A2D33;
}
QWidget#libraryPanel QLabel { color: #CCCCCC; }
QWidget#libraryPanel QLabel#explorerTitle {
    color: #D4D4D4;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
}
QWidget#libraryPanel QLabel#eyebrowLabel {
    color: #BBBBBB;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QWidget#libraryPanel QLabel#explorerCount {
    color: #858585;
    font-size: 10px;
}
QToolButton#libraryActionButton {
    background: transparent;
    border: none;
    border-radius: 3px;
    padding: 3px;
}
QToolButton#libraryActionButton:hover { background: #2A2D33; }
QToolButton#libraryActionButton:pressed { background: #33363D; }
QToolButton#libraryActionButton:disabled { background: transparent; }
QLineEdit#librarySearch {
    min-height: 20px;
    padding: 3px 5px;
    color: #D4D4D4;
    background: #24262C;
    border: 1px solid #3B3E46;
    border-radius: 3px;
    selection-background-color: #264F78;
}
QLineEdit#librarySearch:focus {
    border: 1px solid #4C9BD6;
}
QTreeWidget#projectTree {
    background: transparent;
    border: none;
    outline: none;
    color: #CCCCCC;
    selection-background-color: #264F78;
    selection-color: #FFFFFF;
}
QTreeWidget#projectTree::item {
    background: transparent;
    border: none;
    border-radius: 2px;
    padding: 2px 4px;
    color: #CCCCCC;
}
QTreeWidget#projectTree::item:hover { background: #25282E; }
QTreeWidget#projectTree::item:selected {
    background: #264F78;
    color: #FFFFFF;
}
QTreeWidget#projectTree::branch:selected { background: transparent; }
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
QWidget#pdfSearchBar {
    background: #FFFFFF;
    border-bottom: 1px solid #CBD5E1;
}
QLineEdit#pdfSearchInput { padding: 7px 10px; }
QLabel#searchResultLabel { color: #64748B; font-size: 12px; font-weight: 650; }
QToolButton#searchNavButton, QToolButton#searchCloseButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 7px;
    padding: 5px 9px;
    font-size: 16px;
    font-weight: 700;
}
QToolButton#searchNavButton:hover, QToolButton#searchCloseButton:hover {
    background: #EEF2FF;
    border-color: #C7D2FE;
}
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
QPushButton#primaryButton:disabled { color: #E2E8F0; background: #94A3B8; border-color: #94A3B8; }
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
QLabel#eyebrowLabelDark { color: #64748B; font-size: 10px; font-weight: 800; }
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
QDialog#selectionToolbar {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 10px;
}
QToolButton#selectionToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 7px;
    padding: 4px;
}
QToolButton#selectionToolButton:hover {
    background: #EEF2FF;
    border-color: #C7D2FE;
}
QFrame#selectionSeparator { color: #E2E8F0; }
QWidget#workspacePage { background: #E8EDF4; }
QFrame#workspaceCard {
    background: #FFFFFF;
    border: 1px solid #D8E0EA;
    border-radius: 18px;
}
QLabel#workspaceName { color: #4F46E5; font-size: 12px; font-weight: 800; }
QLabel#workspaceTitle { color: #0F172A; font-size: 24px; font-weight: 800; }
QLabel#errorLabel { color: #BE123C; }
QLabel#reviewPrompt { color: #0F172A; font-size: 26px; font-weight: 800; }
QLabel#reviewAnswer { color: #4338CA; font-size: 19px; font-weight: 650; }
QLabel#englishPreview {
    color: #0F172A;
    background: #EEF2FF;
    border: 1px solid #C7D2FE;
    border-radius: 9px;
    padding: 12px;
    font-size: 20px;
    font-weight: 750;
}
QFrame#noteToolbar {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
}
QToolButton#noteColorButton, QToolButton#noteToolButton, QToolButton#noteDeleteButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 5px;
    min-width: 22px;
    min-height: 22px;
    padding: 2px;
}
QToolButton#noteColorButton:hover, QToolButton#noteToolButton:hover {
    background: #EEF2FF;
    border-color: #C7D2FE;
}
QToolButton#noteDeleteButton { color: #BE123C; font-size: 18px; }
QToolButton#noteDeleteButton:hover { background: #FFF1F2; border-color: #FECDD3; }
QDialog#bulkImportDialog { background: #F8FAFC; }
QLabel#dialogTitle { color: #0F172A; font-size: 22px; font-weight: 800; }
QFrame#inputHelpBox {
    background: #EEF2FF;
    border: 1px solid #C7D2FE;
    border-radius: 10px;
}
QLabel#pasteBadge {
    color: #4338CA;
    background: #FFFFFF;
    border: 1px solid #C7D2FE;
    border-radius: 6px;
    padding: 4px 7px;
    font-weight: 800;
}
QLabel#inputHelpText { color: #475569; }
QLabel#columnHint { color: #64748B; font-size: 10px; font-weight: 800; padding-left: 42px; }
QTableWidget#vocabularyInputTable {
    border: 1px solid #CBD5E1;
    border-radius: 12px;
    gridline-color: #E2E8F0;
    selection-background-color: #E0E7FF;
    selection-color: #172033;
}
QTableWidget#vocabularyInputTable::item { padding: 9px 11px; }
QFrame#inputTools { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; }
QPushButton#softPrimaryButton { color: #4338CA; background: #EEF2FF; border-color: #C7D2FE; }
QLabel#importStatus { color: #64748B; font-weight: 650; padding: 2px 4px; }
QLabel#importStatus[state="ready"] { color: #15803D; }
QLabel#importStatus[state="warning"] { color: #BE123C; }
QPushButton#compactButton { padding: 5px 8px; font-size: 11px; }
"""


DARK_OVERRIDES = """
* { color: #E5E7EB; }
QMainWindow, QWidget#appRoot, QDialog { background: #0F172A; }
QWidget#libraryPanel { background: #141518; border-right-color: #292B30; }
QWidget#libraryPanel QLabel { color: #CBD5E1; }
QToolBar, QStatusBar, QMenuBar {
    background: #111827;
    border-color: #334155;
    color: #E5E7EB;
}
QWidget#pdfSearchBar { background: #111827; border-color: #334155; }
QLabel#searchResultLabel { color: #94A3B8; }
QToolButton#searchNavButton:hover, QToolButton#searchCloseButton:hover { background: #312E81; border-color: #4338CA; }
QMenuBar::item:selected, QToolBar QToolButton:hover { background: #1E293B; }
QPushButton, QLineEdit, QPlainTextEdit, QComboBox, QSpinBox {
    background: #1E293B;
    color: #E5E7EB;
    border-color: #475569;
}
QPushButton:hover { background: #273449; border-color: #818CF8; }
QTabWidget::pane, QTabBar::tab, QTableWidget { background: #111827; }
QTabBar::tab { color: #94A3B8; }
QTabBar::tab:selected { color: #A5B4FC; }
QTableWidget { alternate-background-color: #182235; border-color: #334155; gridline-color: #273449; }
QHeaderView::section { background: #1E293B; color: #CBD5E1; border-color: #334155; }
QFrame#statCard, QFrame#reviewCard { background: #182235; border-color: #334155; }
QLabel#sectionTitle, QLabel#workspaceTitle, QLabel#reviewPrompt { color: #F8FAFC; }
QLabel#mutedLabel, QLabel#eyebrowLabelDark { color: #94A3B8; }
QGraphicsView, QWidget#workspacePage { background: #020617; }
QFrame#workspaceCard { background: #111827; border-color: #334155; }
QMenu, QDialog#selectionToolbar { background: #1E293B; border-color: #475569; }
QMenu::item:selected, QToolButton#selectionToolButton:hover { background: #312E81; }
QLabel#englishPreview { color: #F8FAFC; background: #1E1B4B; border-color: #4338CA; }
QFrame#noteToolbar, QFrame#inputTools { background: #1E293B; border-color: #475569; }
QDialog#bulkImportDialog { background: #0F172A; }
QLabel#dialogTitle { color: #F8FAFC; }
QFrame#inputHelpBox { background: #1E1B4B; border-color: #4338CA; }
QLabel#pasteBadge { color: #C7D2FE; background: #312E81; border-color: #4F46E5; }
QLabel#inputHelpText, QLabel#columnHint { color: #CBD5E1; }
QTableWidget#vocabularyInputTable { selection-background-color: #312E81; selection-color: #FFFFFF; }
QSplitter::handle { background: #334155; }
QScrollBar::handle:vertical { background: #475569; }
"""


def build_stylesheet(theme: str) -> str:
    return BASE_STYLESHEET + (DARK_OVERRIDES if theme == "dark" else "")


APP_STYLESHEET = build_stylesheet("light")
