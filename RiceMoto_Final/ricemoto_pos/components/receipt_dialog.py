from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPainter, QPen, QColor
from datetime import datetime
from decimal import Decimal

class ZigZagFrame(QFrame):
    """A custom frame that draws jagged edges at the top and bottom to simulate a torn receipt."""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), QColor("#FFFFFF"))
        
        # Draw zig-zag edges
        pen = QPen(QColor("#E0E0E0"))
        pen.setWidth(1)
        painter.setPen(pen)
        
        w = self.width()
        h = self.height()
        step = 8
        
        # Top edge
        for x in range(0, w, step):
            painter.drawLine(x, 0, x + step // 2, 6)
            painter.drawLine(x + step // 2, 6, x + step, 0)
            
        # Bottom edge
        for x in range(0, w, step):
            painter.drawLine(x, h, x + step // 2, h - 6)
            painter.drawLine(x + step // 2, h - 6, x + step, h)

class ReceiptDialog(QDialog):
    def __init__(self, order_code, order_type=None, items=None, cashier_name="Manager", payment_method="Cash", parent=None, customer_details=None, dc=None):
        super().__init__(parent)
        self.order_code = order_code
        self.dc = dc
        
        # If dc is provided, fetch real data from database to ensure it's "connected"
        if self.dc:
            db_data = self.dc.get_order_details(order_code)
            if db_data:
                self.order_type = db_data.get("order_type") or order_type
                # Fallback to passed items if DB returns empty list (sync delay)
                self.items = db_data.get("items_list") or items
                self.cashier_name = db_data.get("cashier") or cashier_name
                self.payment_method = db_data.get("payment_method_raw") or payment_method
                
                # Fetch header totals for accuracy
                self.db_subtotal = db_data.get("subtotal")
                self.db_tax = db_data.get("tax")
                self.db_total = db_data.get("total")
                
                self.customer_details = {
                    "name": db_data.get("customer_name"),
                    "contact": db_data.get("customer_contact"),
                    "address": db_data.get("customer_address"),
                    "delivery_fee": db_data.get("delivery_fee", 0)
                } if db_data.get("customer_name") else customer_details
            else:
                self.db_subtotal = None
                self.db_tax = None
                self.db_total = None
                self.order_type = order_type
                self.items = items
                self.cashier_name = cashier_name
                self.payment_method = payment_method
                self.customer_details = customer_details
        else:
            self.order_type = order_type
            self.items = items
            self.cashier_name = cashier_name
            self.payment_method = payment_method
            self.customer_details = customer_details
        # Use a standard dialog — no frameless/translucent hacks
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # The physical "paper" receipt
        self.paper = ZigZagFrame()
        self.paper.setFixedWidth(320)
        self.paper.setMinimumHeight(450)
        paper_layout = QVBoxLayout(self.paper)
        paper_layout.setContentsMargins(20, 25, 20, 25)
        paper_layout.setSpacing(10)
        
        # Base style for text
        style = "font-family: 'Courier New', Courier, monospace; color: #111; font-size: 13px; background: transparent;"
        
        # Header
        header = QLabel("RiceMoto")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-family: 'Courier New', Courier, monospace; color: #000; font-size: 20px; font-weight: 900; background: transparent;")

        sub_header = QLabel("Eugenio Lacaba St, Poblacion 2,\n Calatagan, 4215 Batangas\nEmail: ricemoto88@gmail.com")
        sub_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_header.setStyleSheet(style + " font-size: 11px;")
        
        paper_layout.addWidget(header)
        paper_layout.addWidget(sub_header)
        
        # Separator
        def make_sep():
            lbl = QLabel("-" * 38)
            lbl.setStyleSheet(style)
            return lbl
            
        paper_layout.addWidget(make_sep())
        
        # Meta Info
        meta_text = (f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                      f"Order: {self.order_code}\n"
                      f"Type: {self.order_type}\n"
                      f"Cashier: {self.cashier_name}\n"
                      f"Payment: {self.payment_method.upper()}")
                      
        if self.customer_details:
            name = self.customer_details.get("name", "")
            contact = self.customer_details.get("contact", "")
            address = self.customer_details.get("address", "")
            meta_text += f"\n\nDelivery To:\n{name} ({contact})\n{address}"

        meta = QLabel(meta_text)
        meta.setStyleSheet(style)
        paper_layout.addWidget(meta)
        
        paper_layout.addWidget(make_sep())
        
        # Items Header
        item_hdr = QHBoxLayout()
        qty_lbl = QLabel("QTY ITEM")
        qty_lbl.setStyleSheet(style + " font-weight: bold;")
        price_lbl = QLabel("PRICE")
        price_lbl.setStyleSheet(style + " font-weight: bold;")
        item_hdr.addWidget(qty_lbl)
        item_hdr.addStretch()
        item_hdr.addWidget(price_lbl)
        paper_layout.addLayout(item_hdr)
        
        # Items List
        subtotal = Decimal("0.00")
        for item in self.items:
            row = QHBoxLayout()
            
            qty = int(item["qty"])
            price = Decimal(str(item["price"]))
            item_total = price * qty
            subtotal += item_total
            
            name = item["name"]
            if len(name) > 15:
                name = name[:13] + ".."
                
            left = QLabel(f"{qty:<2} {name}")
            left.setStyleSheet(style)
            
            right = QLabel(f"{item_total:.2f}")
            right.setStyleSheet(style)
            
            row.addWidget(left)
            row.addStretch()
            row.addWidget(right)
            paper_layout.addLayout(row)
            
        paper_layout.addWidget(make_sep())
        
        # Totals
        tax = subtotal * Decimal("0.12")
        total = subtotal + tax
        
        def add_total_row(label, val, bold=False):
            row = QHBoxLayout()
            lbl = QLabel(label)
            val_lbl = QLabel(val)
            s = style + (" font-weight: bold; font-size: 15px;" if bold else "")
            lbl.setStyleSheet(s)
            val_lbl.setStyleSheet(s)
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val_lbl)
            paper_layout.addLayout(row)
            
        add_total_row("Subtotal:", f"₱ {subtotal:.2f}")
        add_total_row("Tax (12%):", f"₱ {tax:.2f}")
        
        # Delivery Fee (NOT affected by tax)
        delivery_fee = Decimal("0.00")
        if self.customer_details and "delivery_fee" in self.customer_details:
            delivery_fee = Decimal(str(self.customer_details["delivery_fee"]))
            
        if delivery_fee > 0:
            add_total_row("Delivery Fee:", f"₱ {delivery_fee:.2f}")
            
        final_total = total + delivery_fee
        add_total_row("TOTAL:", f"₱ {final_total:.2f}", bold=True)
        
        paper_layout.addWidget(make_sep())
        
        # Footer
        footer = QLabel("Anything & Everything\nthat goes well with Rice\n\nThank you for dining\nwith us!")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(style + " font-weight: bold;")
        paper_layout.addWidget(footer)
        
        paper_layout.addStretch()
        
        # ── Action Buttons (INSIDE the paper to prevent ghost box) ──
        btn_sep = QFrame()
        btn_sep.setFixedHeight(1)
        btn_sep.setStyleSheet("background: #E0E0E0; border: none;")
        paper_layout.addWidget(btn_sep)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.setContentsMargins(0, 8, 0, 0)
        
        save_btn = QPushButton("💾 Save Digital")
        save_btn.setFixedHeight(40)
        save_btn.setStyleSheet("background: #007B6E; color: white; border-radius: 8px; font-weight: bold; font-size: 13px;")
        
        done_btn = QPushButton("✅ Done")
        done_btn.setFixedHeight(40)
        done_btn.setStyleSheet("background: #0F172A; color: white; border-radius: 8px; font-weight: bold; font-size: 13px;")
        done_btn.clicked.connect(self.accept)
        save_btn.clicked.connect(self._save_digital)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(done_btn)
        paper_layout.addLayout(btn_layout)
        
        main_layout.addWidget(self.paper, alignment=Qt.AlignmentFlag.AlignCenter)

    def _save_digital(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        
        import os
        export_dir = os.path.join(os.getcwd(), "exports", "receipts")
        default_file = os.path.join(export_dir, f"Receipt_{self.order_code.replace('#', '')}.png")

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Digital Receipt", 
            default_file, 
            "PNG Images (*.png)"
        )
        
        if file_path:
            pixmap = self.paper.grab()
            pixmap.save(file_path, "PNG")
            
            msg = QMessageBox(self)
            msg.setWindowTitle("Success")
            msg.setText(f"Receipt saved successfully to:\n{file_path}")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setStyleSheet("""
                QMessageBox { background-color: white; }
                QLabel { color: black; font-weight: bold; }
                QPushButton { background-color: #007B6E; color: white; border-radius: 5px; padding: 6px 20px; font-weight: bold; }
            """)
            msg.exec()

    def paintEvent(self, event):
        """Paint a dark semi-transparent overlay behind the receipt."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Dark backdrop overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))
        painter.end()

    def showEvent(self, event):
        super().showEvent(event)
        # Cover the ENTIRE main application window, not just the parent widget
        if self.parent():
            main_window = self.parent().window()
            self.setGeometry(main_window.geometry())
