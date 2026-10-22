"""
CachyPulse Theme — Faithful to ResetExplode's Monochromatic & Neon Aesthetic.
Deep OLED blacks (#000000, #080808, #0E0E0E), 16px smooth rounded cards,
monospace metrics, and crisp white/cyan typography.
"""

DARK_THEME_QSS = """
/* ===== Base Window & Backgrounds ===== */
QMainWindow, QDialog {
    background-color: #000000;
    color: #F5F5F5;
    font-family: "Fira Sans", "Segoe UI Variable Text", "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

QWidget {
    background-color: transparent;
    color: #F5F5F5;
    font-family: "Fira Sans", "Segoe UI Variable Text", "Segoe UI", "Inter", sans-serif;
}

/* ===== Sidebar Navigation ===== */
QFrame#Sidebar {
    background-color: #070707;
    border-right: 1px solid #181818;
}

QListWidget#NavList {
    background-color: transparent;
    border: none;
    outline: none;
}

QListWidget#NavList::item {
    height: 44px;
    padding-left: 14px;
    border-radius: 12px;
    margin: 2px 8px;
    color: #8C8C8C;
    font-size: 13.5px;
    font-weight: 500;
}

QListWidget#NavList::item:hover {
    background-color: #141414;
    color: #FFFFFF;
}

QListWidget#NavList::item:selected {
    background-color: #1A1A1A;
    color: #FFFFFF;
    font-weight: 600;
    border: 1px solid #282828;
}

/* ===== Cards (ResetExplode 16px CardBorder) ===== */
QFrame.Card {
    background-color: #0B0B0B;
    border: 1px solid #1C1C1C;
    border-radius: 16px;
    padding: 18px;
}

QFrame.Card:hover {
    border: 1px solid #2C2C2C;
}

/* ===== Typography Labels ===== */
QLabel.CardTitle {
    color: #8C8C8C;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    margin-bottom: 6px;
}

QLabel.BigNumber {
    color: #FFFFFF;
    font-family: "JetBrains Mono", "Cascadia Mono", "Consolas", monospace;
    font-size: 26px;
    font-weight: 700;
    margin: 4px 0;
}

QLabel.SubText {
    color: #707070;
    font-size: 12px;
}

/* ===== Buttons (ResetExplode Primary White Pill) ===== */
QPushButton {
    background-color: #161616;
    color: #F0F0F0;
    border: 1px solid #262626;
    border-radius: 10px;
    padding: 9px 20px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #222222;
    border-color: #404040;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #0E0E0E;
}

QPushButton.Primary {
    background-color: #FFFFFF;
    color: #000000;
    border: 1px solid #FFFFFF;
    border-radius: 10px;
    padding: 10px 24px;
    font-weight: 700;
}

QPushButton.Primary:hover {
    background-color: #E2E2E2;
    color: #000000;
}

QPushButton.Primary:pressed {
    background-color: #CCCCCC;
}

QPushButton.Danger {
    background-color: #B91C1C;
    color: #FFFFFF;
    border: 1px solid #DC2626;
    border-radius: 10px;
}

QPushButton.Danger:hover {
    background-color: #DC2626;
}

/* ===== Tabs (Clean Minimalist TabBar) ===== */
QTabWidget::pane {
    border: none;
    background-color: transparent;
}

QTabBar::tab {
    background-color: #0D0D0D;
    color: #8C8C8C;
    border: 1px solid #1C1C1C;
    border-radius: 10px;
    padding: 8px 18px;
    margin-right: 8px;
    margin-bottom: 12px;
    font-weight: 600;
    font-size: 12.5px;
}

QTabBar::tab:hover {
    background-color: #161616;
    color: #FFFFFF;
}

QTabBar::tab:selected {
    background-color: #202020;
    color: #FFFFFF;
    border: 1px solid #383838;
}

/* ===== Tables (Sleek Dark Borderless Rows) ===== */
QTableWidget {
    background-color: #0A0A0A;
    border: 1px solid #1C1C1C;
    border-radius: 12px;
    gridline-color: #141414;
    color: #F5F5F5;
    outline: none;
}

QTableWidget::item {
    padding: 10px;
    border-bottom: 1px solid #141414;
}

QTableWidget::item:selected {
    background-color: #1E1E1E;
    color: #FFFFFF;
}

QHeaderView::section {
    background-color: #060606;
    color: #737373;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 10px;
    border: none;
    border-bottom: 1px solid #1C1C1C;
}

/* ===== Inputs & Selectors ===== */
QLineEdit, QComboBox, QSpinBox {
    background-color: #0C0C0C;
    border: 1px solid #242424;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F5F5F5;
    font-size: 13px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #4A4A4A;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}

/* ===== Sleek 4px Meters (ResetExplode Meter style) ===== */
QProgressBar {
    background-color: #1A1A1A;
    border: none;
    border-radius: 2px;
    height: 4px;
    text-align: right;
}

QProgressBar::chunk {
    background-color: #FFFFFF;
    border-radius: 2px;
}

/* ===== Scrollbars (Ultra-thin & Dark) ===== */
QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollBar:vertical {
    background: #000000;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #242424;
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #4A4A4A;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

LIGHT_THEME_QSS = """
QMainWindow, QDialog {
    background-color: #FAFAFA;
    color: #111111;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13px;
}

QWidget {
    background-color: transparent;
    color: #111111;
}

QFrame#Sidebar {
    background-color: #F0F0F0;
    border-right: 1px solid #E0E0E0;
}

QListWidget#NavList::item {
    height: 44px;
    padding-left: 14px;
    border-radius: 12px;
    margin: 2px 8px;
    color: #555555;
    font-size: 13.5px;
}

QListWidget#NavList::item:selected {
    background-color: #E0E0E0;
    color: #000000;
    font-weight: 600;
}

QFrame.Card {
    background-color: #FFFFFF;
    border: 1px solid #E5E5E5;
    border-radius: 16px;
    padding: 18px;
}

QPushButton.Primary {
    background-color: #000000;
    color: #FFFFFF;
    border: 1px solid #000000;
    border-radius: 10px;
    padding: 10px 24px;
    font-weight: 700;
}
"""
