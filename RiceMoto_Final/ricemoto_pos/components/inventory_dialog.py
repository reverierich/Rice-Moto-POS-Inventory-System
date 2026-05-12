"""
Inventory Management Dialog for RiceMoto POS.
Allowed kitchen/manager to toggle "Sold Out" status.
"""
from PyQt6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QScrollArea, QFrame, QPushButton, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from assets.ui.styles import (
    TEXT, MUTED, BORDER, SURFACE, 
    TEAL_DARK, TEAL_PALE, RED, GREEN, get_shadow
)

class InventoryItemRow(QFrame):
    """Row in the inventory manager."""
    toggled = pyqtSignal(str, bool)

    def __init__(self, item):
        super().__init__()
        self.item = item
        self.setFixedHeight(60)
        self.setStyleSheet(f"background: {SURFACE}; border-bottom: 1.5px solid {TEAL_PALE};")
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        
        icon = QLabel(self.item["emoji"])
        icon.setStyleSheet("font-size: 20px;")
        
        name = QLabel(self.item["name"])
        name.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {TEXT};")
        
        layout.addWidget(icon)
        layout.addWidget(name)
        layout.addStretch()
        
        self.status_btn = QPushButton()
        self.status_btn.setFixedSize(100, 32)
        self.status_btn.clicked.connect(self._on_toggle)
        self._update_btn()
        
        layout.addWidget(self.status_btn)

    def _update_btn(self):
        is_soldout = self.item.get("soldout", False)
        if is_soldout:
            self.status_btn.setText("SOLD OUT")
            self.status_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {RED}; color: white;
                    border-radius: 8px; font-size: 10px; font-weight: 800;
                }}
            """)
        else:
            self.status_btn.setText("AVAILABLE")
            self.status_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {GREEN}; color: white;
                    border-radius: 8px; font-size: 10px; font-weight: 800;
                }}
            """)

    def _on_toggle(self):
        new_state = not self.item.get("soldout", False)
        self.item["soldout"] = new_state
        self._update_btn()
        self.toggled.emit(self.item["name"], new_state)


class InventoryDialog(QDialog):
    """Dialog for managing stock status."""
    def __init__(self, dc, parent=None):
        super().__init__(parent)
        self.dc = dc
        self.setWindowTitle("Kitchen Inventory Manager")
        self.setFixedSize(400, 500)
        self.setStyleSheet(f"background: {SURFACE};")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Toggle Item Availability")
        title.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {TEXT}; margin-bottom: 5px;")
        layout.addWidget(title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        container = QWidget()
        self.list_layout = QVBoxLayout(container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(0)
        
        for item in self.dc.get_menu():
            row = InventoryItemRow(item)
            row.toggled.connect(self.dc.set_sold_out)
            self.list_layout.addWidget(row)
            
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(40)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {TEAL_DARK}; color: white;
                border-radius: 10px; font-weight: 700; margin-top: 10px;
            }}
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
