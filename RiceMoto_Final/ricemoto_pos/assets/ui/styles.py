"""
Global styles and design tokens for RiceMoto POS.
"""
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect

# Design Tokens
TEAL = "#6366F1"
TEAL_DARK = "#4338CA"
TEAL_MID = "#818CF8"
TEAL_LIGHT = "#E0E7FF"
TEAL_PALE = "#EEF2FF"
ACCENT = "#FF6B35"
WHITE = "#FFFFFF"
BG = "#F4F7F6"
SURFACE = "#FFFFFF"
TEXT = "#1A2E2C"
MUTED = "#6B8682"
BORDER = "#D0E8E4"
GREEN = "#22C55E"
ORANGE = "#F97316"
BLUE = "#3B82F6"
RED = "#EF4444"

GLOBAL_QSS = f"""
* {{
    outline: none;
}}
QAbstractScrollArea::viewport {{
    background: transparent;
    border: none;
}}
QWidget {{
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
    color: {TEXT};
    border: none;
}}
QLabel {{
    border: none;
    background: transparent;
}}
QMainWindow, QDialog {{
    background: {BG};
    border: none;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    width: 5px; background: transparent; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER}; border-radius: 2px; min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    height: 5px; background: transparent;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER}; border-radius: 2px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
QLineEdit, QComboBox, QDateEdit, QSpinBox {{
    background: {SURFACE};
    border: 1.5px solid {BORDER};
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 13px;
    color: {TEXT};
}}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus {{
    border-color: {TEAL};
    background: {BG};
}}
QLineEdit:hover, QComboBox:hover, QDateEdit:hover, QSpinBox:hover {{
    border-color: {TEAL};
}}
QComboBox::drop-down {{
    border: none; width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {MUTED};
}}
QComboBox QAbstractItemView {{
    background: {SURFACE};
    color: {TEXT};
    selection-background-color: {TEAL_DARK};
    selection-color: white;
    outline: none;
    border: 1px solid {BORDER};
    border-radius: 4px;
}}
QComboBox QAbstractItemView::item {{
    padding: 8px 12px;
    background: {SURFACE};
    color: {TEXT};
}}
QComboBox QAbstractItemView::item:alternate {{
    background: {BG};
}}
QPushButton {{
    background: {TEAL_DARK};
    color: white;
    border: none;
    border-radius: 14px;
    padding: 10px 22px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {TEAL};
}}
QPushButton:pressed {{
    background: #004A42;
    padding-top: 11px;
    padding-bottom: 9px;
}}
QMessageBox QLabel, QDialog QLabel {{
    color: {TEXT} !important;
    font-size: 13px !important;
}}

/* Extremely aggressive style for dialog buttons */
QMessageBox QPushButton, 
QDialog QDialogButtonBox QPushButton,
QPushButton:default {{
    background-color: {TEAL_DARK} !important;
    color: white !important;
    min-width: 90px !important;
    padding: 10px 20px !important;
    border-radius: 10px !important;
    font-weight: 800 !important;
    font-size: 12px !important;
    border: none !important;
}}

QMessageBox QPushButton:hover, 
QDialog QDialogButtonBox QPushButton:hover {{
    background-color: {TEAL} !important;
}}

/* Neutral buttons */
QMessageBox QPushButton:!default,
QDialog QDialogButtonBox QPushButton:!default {{
    background-color: #E2E8F0 !important;
    color: {TEXT} !important;
}}

QTableWidget {{
    background: {SURFACE};
    border: none;
    gridline-color: {TEAL_PALE};
    selection-background-color: {TEAL_LIGHT};
    selection-color: {TEXT};
}}
QTableWidget::item {{
    padding: 8px 14px;
    border-bottom: 1px solid {TEAL_PALE};
}}
QHeaderView::section {{
    background: {TEAL_DARK};
    color: white;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    padding: 10px 14px;
    border: none;
}}
QToolTip {{
    background: {TEAL_DARK};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
}}
"""

def get_shadow(radius=16, color=TEAL, alpha=30):
    e = QGraphicsDropShadowEffect()
    c = QColor(color)
    c.setAlpha(alpha)
    e.setColor(c)
    e.setBlurRadius(radius)
    e.setOffset(0, 4)
    return e
