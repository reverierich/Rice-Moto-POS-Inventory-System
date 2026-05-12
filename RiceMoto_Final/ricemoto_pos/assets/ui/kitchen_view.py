"""
Kitchen Display System (KDS) for RiceMoto POS.
Displays active orders and inventory management for kitchen.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QScrollArea, QFrame, QGridLayout, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from assets.ui.styles import (
    TEXT, MUTED, BORDER, BG, SURFACE, 
    ORANGE, BLUE, GREEN, TEAL_DARK, TEAL_PALE, get_shadow
)
from components.inventory_dialog import InventoryDialog

STATUS_COLORS = {"pending": ORANGE, "preparing": BLUE, "ready": GREEN}
STATUS_NEXT = {"pending": "Start Cooking", "preparing": "Mark Ready", "ready": "Complete"}

class KDSCard(QFrame):
    """Order card for the Kitchen queue."""
    advance = pyqtSignal(str)
    cancel = pyqtSignal(str)

    def __init__(self, order):
        super().__init__()
        self.order = order
        self.setFixedWidth(240)
        self.setGraphicsEffect(get_shadow(10))
        self._setup_ui()

    def _setup_ui(self):
        order = self.order
        status = order["status"]
        color = STATUS_COLORS.get(status, "#000000")
        
        self.setStyleSheet(f"""
            QFrame {{
                background: {SURFACE};
                border-radius: 20px;
                border: 1.5px solid {BORDER};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Color bar top
        bar = QFrame()
        bar.setFixedHeight(5)
        bar.setStyleSheet(f"background: {color}; border-radius: 20px 20px 0 0;")
        layout.addWidget(bar)
        
        # Content
        content = QWidget()
        cv = QVBoxLayout(content)
        cv.setContentsMargins(15, 12, 15, 15)
        cv.setSpacing(10)
        
        # Header
        hdr = QHBoxLayout()
        oid = QLabel(order["id"])
        oid.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {TEXT};")
        time = QLabel(order["time"])
        time.setStyleSheet(f"font-size: 10px; color: {MUTED};")
        hdr.addWidget(oid)
        hdr.addStretch()
        hdr.addWidget(time)
        cv.addLayout(hdr)
        
        table = QLabel(f"📍 {order['table']}")
        table.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {MUTED};")
        cv.addWidget(table)
        
        status_badge = QLabel(order['status'].replace('_', ' ').title())
        status_badge.setStyleSheet(
            f"font-size: 11px; font-weight: 800; color: {color};"
        )
        cv.addWidget(status_badge)

        items_v = QVBoxLayout()
        items_v.setSpacing(4)
        for it in order["items"]:
            item_row = QHBoxLayout()
            dot = QLabel("•")
            dot.setStyleSheet("font-weight: bold; color: teal;")
            label = QLabel(it)
            label.setStyleSheet(f"font-size: 12px; color: {TEXT};")
            item_row.addWidget(dot)
            item_row.addWidget(label)
            item_row.addStretch()
            items_v.addLayout(item_row)
        cv.addLayout(items_v)
        
        cv.addStretch()
        
        # Footer Buttons
        btns = QHBoxLayout()
        btns.setSpacing(8)
        
        self.next_btn = QPushButton(STATUS_NEXT.get(status, "Done"))
        self.next_btn.setFixedHeight(35)
        self.next_btn.setStyleSheet(f"""
            QPushButton {{
                background: {TEAL_DARK}; color: white;
                border-radius: 10px; font-size: 11px; font-weight: 800;
            }}
            QPushButton:hover {{ background: teal; }}
        """)
        self.next_btn.clicked.connect(lambda: self.advance.emit(order["id"]))
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(35)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {TEAL_PALE}; color: {MUTED};
                border-radius: 10px; font-size: 11px; font-weight: 700;
            }}
            QPushButton:hover {{ background: #FFEBEE; color: red; }}
        """)
        cancel_btn.clicked.connect(lambda: self.cancel.emit(order["id"]))
        
        btns.addWidget(cancel_btn)
        btns.addWidget(self.next_btn)
        cv.addLayout(btns)
        
        layout.addWidget(content)


class KitchenView(QWidget):
    """Kitchen Display System Interface."""
    def __init__(self, dc):
        super().__init__()
        self.dc = dc
        self.setStyleSheet(f"background: {BG};")
        self._setup_ui()
        
        # Connect signals
        self.dc.order_status_changed.connect(lambda id, status: self.refresh())

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 25, 30, 25)
        main_layout.setSpacing(20)
        
        header = QHBoxLayout()
        title = QLabel("Kitchen Display System")
        title.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {TEXT};")
        header.addWidget(title)
        
        # Quick Stock Toggle (Sold Out logic)
        stock_btn = QPushButton("Manage Stock Availability")
        stock_btn.setFixedWidth(200)
        stock_btn.setStyleSheet(f"""
            QPushButton {{
                background: white; border: 1.5px solid {BORDER};
                border-radius: 10px; font-size: 11px; font-weight: 700;
                padding: 10px;
            }}
            QPushButton:hover {{ background: {TEAL_PALE}; }}
        """)
        stock_btn.clicked.connect(self._open_inventory_manager)
        header.addStretch()
        header.addWidget(stock_btn)
        main_layout.addLayout(header)
        
        # KDS Queue Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(20)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.scroll.setWidget(self.container)
        main_layout.addWidget(self.scroll)
        
        self.refresh()

    def refresh(self):
        # Clear
        while self.grid.count():
            child = self.grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        orders = self.dc.get_orders()
        if not orders:
            placeholder = QLabel("👨‍🍳 No active orders. Take a breath!")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet(f"color: {MUTED}; font-size: 16px; margin-top: 60px;")
            self.grid.addWidget(placeholder, 0, 0)
            return

        cols = 4 # Responsive grid cols
        for i, order in enumerate(orders):
            card = KDSCard(order)
            card.advance.connect(self.dc.advance_order)
            card.cancel.connect(self.dc.cancel_order)
            self.grid.addWidget(card, i // cols, i % cols)

    def _open_inventory_manager(self):
        """Opens the stock management dialog."""
        dialog = InventoryDialog(self.dc, self)
        dialog.exec()

