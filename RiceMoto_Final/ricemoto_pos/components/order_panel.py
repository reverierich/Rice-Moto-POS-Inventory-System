"""
Order Panel component for RiceMoto POS.
Handles the cart list, totals, and checkout button.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal
from assets.ui.styles import (
    TEAL, TEAL_DARK, TEAL_PALE, TEAL_LIGHT, BORDER, 
    SURFACE, TEXT, MUTED, ACCENT, WHITE
)
from decimal import Decimal

class CartItem(QWidget):
    """Individual item in the cart."""
    qty_changed = pyqtSignal(str, int)
    item_removed = pyqtSignal(str)

    def __init__(self, item):
        super().__init__()
        self.item = item
        self.qty_label_ref = None
        self.setStyleSheet(f"background: {SURFACE}; border-radius: 12px; margin-bottom: 10px;")
        self.setMinimumHeight(80)
        self._setup_ui()

    def _setup_ui(self):
        item = self.item
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Icon
        icon = QLabel(item["emoji"])
        icon.setFixedSize(50, 50)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"font-size: 24px; background: {WHITE}; border-radius: 10px; border: 1px solid {BORDER};")
        
        # Details
        details = QVBoxLayout()
        details.setSpacing(4)
        name = QLabel(item["name"])
        name.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {TEXT};")
        price = QLabel(f"₱{item['price']:.2f} each")
        price.setStyleSheet(f"font-size: 12px; color: {MUTED}; font-weight: 600;")
        details.addWidget(name)
        details.addWidget(price)
        
        # Qty Controls Container
        qty_container = QFrame()
        qty_container.setStyleSheet(f"background: {WHITE}; border-radius: 10px; border: 1px solid {BORDER};")
        qty_ctrl = QHBoxLayout(qty_container)
        qty_ctrl.setContentsMargins(6, 4, 6, 4)
        qty_ctrl.setSpacing(6)
        
        def make_btn(text, delta):
            btn = QPushButton(text)
            btn.setFixedSize(28, 28)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {TEAL};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 0;
                }}
                QPushButton:hover {{
                    background: {TEAL_DARK};
                }}
                QPushButton:pressed {{
                    background: {TEAL_DARK};
                    padding: 2px 0 0 0;
                }}
            """)
            btn.clicked.connect(lambda: self.qty_changed.emit(item["name"], delta))
            return btn
        
        minus_btn = make_btn("−", -1)
        self.qty_lbl = QLabel(str(item["qty"]))
        self.qty_lbl.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {TEXT}; min-width: 20px; text-align: center;")
        self.qty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plus_btn = make_btn("+", 1)
        
        qty_ctrl.addWidget(minus_btn)
        qty_ctrl.addWidget(self.qty_lbl)
        qty_ctrl.addWidget(plus_btn)
        
        layout.addWidget(icon)
        layout.addLayout(details)
        layout.addStretch()
        layout.addWidget(qty_container)



class OrderPanel(QWidget):
    """Responsive Order Summary panel."""
    order_confirmed = pyqtSignal(list, str, str, dict, float) # (items, type, payment_method, customer_details, delivery_fee)

    def __init__(self):
        super().__init__()
        self.cart = []
        self.order_type = "Dine In"
        self.setFixedWidth(400)
        self.setStyleSheet("background: transparent;")
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 15, 20, 20)
        main_layout.setSpacing(0)
        
        from assets.ui.styles import get_shadow
        
        self.glass_frame = QFrame()
        self.glass_frame.setGraphicsEffect(get_shadow(20, alpha=40))
        self.glass_frame.setStyleSheet(f"""
            QFrame#GlassContainer {{
                background: {SURFACE};
                border: 1.5px solid {BORDER};
                border-radius: 24px;
            }}
        """)
        self.glass_frame.setObjectName("GlassContainer")
        
        inner_layout = QVBoxLayout(self.glass_frame)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setStyleSheet(f"""
            background: {TEAL_DARK}; 
            border: none;
            border-top-left-radius: 24px;
            border-top-right-radius: 24px;
            border-bottom-left-radius: 0px;
            border-bottom-right-radius: 0px;
        """)
        header.setFixedHeight(120)
        hv = QVBoxLayout(header)
        hv.setContentsMargins(20, 20, 20, 15)
        
        title = QLabel("Current Order")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: white;")
        self.order_id_lbl = QLabel("Order #1101")
        self.order_id_lbl.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.7);")
        
        # Order Type Tabs
        tabs = QHBoxLayout()
        tabs.setSpacing(8)
        self.type_btns = {}
        for t in ["Dine In", "Take Out", "Delivery"]:
            btn = QPushButton(t)
            btn.setFixedHeight(30)
            self.type_btns[t] = btn
            btn.clicked.connect(lambda checked, x=t: self._set_order_type(x))
            tabs.addWidget(btn)
        self._set_order_type("Dine In")
        
        hv.addWidget(title)
        hv.addWidget(self.order_id_lbl)
        hv.addStretch()
        hv.addLayout(tabs)
        
        inner_layout.addWidget(header)
        
        # Cart Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        
        self.cart_container = QWidget()
        self.cart_layout = QVBoxLayout(self.cart_container)
        self.cart_layout.setContentsMargins(20, 10, 20, 10)
        self.cart_layout.setSpacing(0)
        self.cart_layout.addStretch() # Push items to top
        
        self.scroll.setWidget(self.cart_container)
        inner_layout.addWidget(self.scroll)
        
        # Totals Section
        self.totals_area = QWidget()
        self.totals_area.setStyleSheet(f"""
            QWidget {{
                background: {SURFACE}; 
                border-top: 1.5px solid {BORDER};
                border-bottom-left-radius: 24px;
                border-bottom-right-radius: 24px;
            }}
        """)
        tv = QVBoxLayout(self.totals_area)
        tv.setContentsMargins(20, 15, 20, 15)
        tv.setSpacing(8)
        
        def add_row(label, attr, is_bold=False):
            row = QHBoxLayout()
            lb = QLabel(label)
            val = QLabel("₱0.00")
            setattr(self, attr, val)
            
            style = f"font-size: {'16px' if is_bold else '13px'}; font-weight: {'800' if is_bold else '600'}; color: {TEXT if is_bold else MUTED};"
            lb.setStyleSheet(style)
            val.setStyleSheet(style)
            
            row.addWidget(lb)
            row.addStretch()
            row.addWidget(val)
            tv.addLayout(row)
        
        add_row("Subtotal", "sub_lbl")
        add_row("Tax (12%)", "tax_lbl")
        line = QFrame(); line.setFixedHeight(1); line.setStyleSheet(f"background: {BORDER};")
        tv.addWidget(line)
        add_row("TOTAL", "total_lbl", True)
        
        from PyQt6.QtWidgets import QComboBox
        pm_layout = QHBoxLayout()
        pm_lbl = QLabel("Payment:")
        pm_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {MUTED};")
        self.payment_combo = QComboBox()
        self.payment_combo.addItems(["Cash", "GCash"])
        self.payment_combo.setStyleSheet(f"""
            QComboBox {{
                background: white; 
                border: 1px solid {BORDER}; 
                border-radius: 6px; 
                padding: 4px 8px; 
                color: black; 
                font-weight: bold;
            }}
            QComboBox QAbstractItemView {{
                background: white;
                color: black;
                selection-background-color: #E2E8F0;
                selection-color: black;
            }}
        """)
        pm_layout.addWidget(pm_lbl)
        pm_layout.addStretch()
        pm_layout.addWidget(self.payment_combo)
        tv.addLayout(pm_layout)
        
        self.checkout_btn = QPushButton("Confirm Order")
        self.checkout_btn.setFixedHeight(50)
        self.checkout_btn.setStyleSheet(f"""
            QPushButton {{
                background: {TEAL_DARK}; color: white;
                border-radius: 16px; font-size: 15px; font-weight: 800;
                margin-top: 10px;
            }}
            QPushButton:hover {{ background: {TEAL}; }}
            QPushButton:disabled {{ background: {MUTED}; }}
        """)
        self.checkout_btn.clicked.connect(self._on_confirm)
        tv.addWidget(self.checkout_btn)
        
        inner_layout.addWidget(self.totals_area)
        main_layout.addWidget(self.glass_frame)
        self._update_cart_display()

    def _set_order_type(self, t):
        self.order_type = t
        for name, btn in self.type_btns.items():
            active = name == t
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {ACCENT if active else "rgba(255,255,255,0.15)"};
                    color: {WHITE if active else "rgba(255,255,255,0.8)"};
                    border-radius: 15px; font-size: 10px; font-weight: 700;
                    padding: 0 10px;
                }}
            """)

    def add_item(self, item_data):
        # Check if already in cart
        for item in self.cart:
            if item["name"] == item_data["name"]:
                item["qty"] += 1
                self._update_cart_display()
                return
        
        self.cart.append({
            "name": item_data["name"],
            "emoji": item_data["emoji"],
            "price": item_data["price"],
            "qty": 1
        })
        self._update_cart_display()

    def _change_qty(self, name, delta):
        for item in self.cart:
            if item["name"] == name:
                item["qty"] += delta
                if item["qty"] <= 0:
                    self.cart.remove(item)
                break
        self._update_cart_display()

    def _update_cart_display(self):
        # Clear cart layout (except the stretch at the end)
        # Use immediate removal (not deleteLater) to prevent visual overlap
        while self.cart_layout.count() > 1:
            child = self.cart_layout.takeAt(0)
            w = child.widget()
            if w:
                w.hide()
                w.setParent(None)
        
        if not self.cart:
            placeholder = QLabel("Your cart is empty\nTap a dish to start")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet(f"font-size: 13px; color: {MUTED}; margin-top: 40px;")
            self.cart_layout.insertWidget(0, placeholder)
            self.checkout_btn.setEnabled(False)
            self.sub_lbl.setText("₱0.00")
            self.tax_lbl.setText("₱0.00")
            self.total_lbl.setText("₱0.00")
            return

        self.checkout_btn.setEnabled(True)
        subtotal = Decimal("0.00")
        for item in self.cart:
            price = Decimal(str(item["price"]))
            subtotal += price * item["qty"]
            widget = CartItem(item)
            widget.qty_changed.connect(self._change_qty)
            self.cart_layout.insertWidget(self.cart_layout.count()-1, widget)
        
        tax = subtotal * Decimal("0.12")
        total = subtotal + tax
        
        self.sub_lbl.setText(f"₱{subtotal:,.2f}")
        self.tax_lbl.setText(f"₱{tax:,.2f}")
        self.total_lbl.setText(f"₱{total:,.2f}")

    def _on_confirm(self):
        payment_method = self.payment_combo.currentText()
        customer_details = {}
        
        # 1. Check for Delivery
        if self.order_type == "Delivery":
            from components.delivery_dialog import DeliveryDialog
            delivery_dialog = DeliveryDialog(self.window())
            if delivery_dialog.exec() == 1:
                customer_details = delivery_dialog.customer_details
            else:
                return # User cancelled delivery setup
        
        # 2. Check for GCash Payment
        if payment_method == "GCash":
            from components.gcash_dialog import GCashDialog
            amount = self.total_lbl.text()
            dialog = GCashDialog(amount, self.window())
            if dialog.exec() == 1:
                ref_no = dialog.reference_number
                payment_method = f"GCash (Ref: {ref_no})"
            else:
                # User cancelled payment
                return
                
        delivery_fee = customer_details.get("delivery_fee", 0)
        
        # Snapshot the cart data before clearing
        cart_snapshot = list(self.cart)
        
        # Clear cart FIRST — before the signal triggers a blocking dialog
        self.cart = []
        self._update_cart_display()
        
        # Update order ID for next order
        try:
            current_id = int(self.order_id_lbl.text().replace("Order #", ""))
            self.order_id_lbl.setText(f"Order #{current_id + 1}")
        except:
            pass
        
        # NOW emit — this triggers the receipt dialog (blocking exec())
        self.order_confirmed.emit(cart_snapshot, self.order_type, payment_method, customer_details, float(delivery_fee))
