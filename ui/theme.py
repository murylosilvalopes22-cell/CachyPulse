"""
Theme manager and QSS stylesheets for CachyPulse.
Provides Dark and Light modern dashboard styling.
"""

DARK_THEME_QSS = """
QMainWindow, QDialog, QWidget {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

/* Sidebar navigation */
QFrame#Sidebar {
    background-color: #161b22;
    border-right: 1px solid #30363d;
}

QListWidget#NavList {
    background-color: transparent;
    border: none;
    outline: none;
}

QListWidget#NavList::item {
    height: 42px;
    padding-left: 12px;
    border-radius: 6px;
    margin: 2px 8px;
    color: #8b949e;
    font-weight: 500;
}

QListWidget#NavList::item:hover {
    background-color: #21262d;
    color: #f0f6fc;
}

QListWidget#NavList::item:selected {
    background-color: #1f6feb;
    color: #ffffff;
    font-weight: 600;
}

/* Cards */
QFrame.Card {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 16px;
}

QFrame.Card:hover {
    border: 1px solid #58a6ff;
}

/* Buttons */
QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #161b22;
}

QPushButton.Primary {
    background-color: #238636;
    border-color: #2ea043;
    color: #ffffff;
}

QPushButton.Primary:hover {
    background-color: #2ea043;
}

QPushButton.Danger {
    background-color: #da3633;
    border-color: #f85149;
    color: #ffffff;
}

QPushButton.Danger:hover {
    background-color: #b62324;
}

/* Tables */
QTableWidget {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    gridline-color: #21262d;
    color: #e6edf3;
}

QHeaderView::section {
    background-color: #0d1117;
    color: #8b949e;
    font-weight: 600;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #30363d;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #0d1117;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #8b949e;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Inputs */
QLineEdit, QComboBox, QSpinBox {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    color: #e6edf3;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border-color: #58a6ff;
}

QProgressBar {
    background-color: #21262d;
    border: none;
    border-radius: 4px;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
    height: 12px;
}

QProgressBar::chunk {
    background-color: #238636;
    border-radius: 4px;
}
"""

LIGHT_THEME_QSS = """
QMainWindow, QDialog, QWidget {
    background-color: #f6f8fa;
    color: #1f2328;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

QFrame#Sidebar {
    background-color: #ffffff;
    border-right: 1px solid #d0d7de;
}

QListWidget#NavList {
    background-color: transparent;
    border: none;
}

QListWidget#NavList::item {
    height: 42px;
    padding-left: 12px;
    border-radius: 6px;
    margin: 2px 8px;
    color: #656d76;
    font-weight: 500;
}

QListWidget#NavList::item:hover {
    background-color: #f3f4f6;
    color: #1f2328;
}

QListWidget#NavList::item:selected {
    background-color: #0969da;
    color: #ffffff;
    font-weight: 600;
}

QFrame.Card {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 16px;
}

QPushButton {
    background-color: #f6f8fa;
    color: #24292f;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #f3f4f6;
}

QPushButton.Primary {
    background-color: #1f883d;
    color: #ffffff;
    border-color: #1a7f37;
}

QPushButton.Primary:hover {
    background-color: #1a7f37;
}

QTableWidget {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    gridline-color: #f0f2f5;
    color: #1f2328;
}

QHeaderView::section {
    background-color: #f6f8fa;
    color: #656d76;
    font-weight: 600;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #d0d7de;
}
"""
