from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QFrame, QTextEdit, QGraphicsDropShadowEffect, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import assets.ui.styles as styles

DELIVERY_FEES = {
    "Bagong Silang": 45.00,
    "Balibago": 50.00,
    "Balitoc": 20.00,
    "Barangay 1": 15.00,
    "Barangay 2": 10.00,
    "Barangay 3": 15.00,
    "Barangay 4": 15.00,
    "Carretunan": 35.00,
    "Gulod": 25.00,
    "Lucsuhin": 30.00,
    "Quilitisan": 30.00,
    "Sta. Ana": 40.00,
    "Talisay": 45.00,
    "Tanagan": 35.00
}

class DeliveryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.customer_details = {}
        self.delivery_fee = 0.0
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        card = QFrame()
        card.setFixedWidth(380)
        card.setStyleSheet(f"""
            QFrame {{
                background: {styles.SURFACE};
                border-radius: 20px;
                border: 1px solid {styles.BORDER};
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 5)
        card.setGraphicsEffect(shadow)
        
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet(f"""
            background: {styles.TEAL_DARK};
            border-top-left-radius: 20px;
            border-top-right-radius: 20px;
            border-bottom-left-radius: 0px;
            border-bottom-right-radius: 0px;
            border: none;
        """)
        hl = QVBoxLayout(header)
        hl.setContentsMargins(20, 15, 20, 15)
        
        title = QLabel("🛵 Delivery Details")
        title.setStyleSheet("color: white; font-size: 18px; font-weight: 800;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(title)
        
        cl.addWidget(header)
        
        # Body
        body = QFrame()
        body.setStyleSheet("border: none; background: transparent;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(25, 20, 25, 25)
        bl.setSpacing(15)
        
        # Input styled helper
        input_style = f"""
            QLineEdit, QTextEdit, QComboBox {{
                background: {styles.BG};
                border: 1.5px solid {styles.BORDER};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                color: {styles.TEXT};
                font-weight: 600;
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 2px solid {styles.TEAL};
                background: {styles.SURFACE};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
            }}
        """
        
        # Customer Name
        name_lbl = QLabel("Customer Name")
        name_lbl.setStyleSheet(f"color: {styles.MUTED}; font-size: 12px; font-weight: 700; border: none;")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. John Doe")
        self.name_input.setStyleSheet(input_style)
        self.name_input.textChanged.connect(self._validate)
        
        bl.addWidget(name_lbl)
        bl.addWidget(self.name_input)
        
        # Contact Number
        contact_lbl = QLabel("Contact Number")
        contact_lbl.setStyleSheet(f"color: {styles.MUTED}; font-size: 12px; font-weight: 700; border: none;")
        self.contact_input = QLineEdit()
        self.contact_input.setPlaceholderText("e.g. 09123456789")
        self.contact_input.setStyleSheet(input_style)
        self.contact_input.textChanged.connect(self._validate)
        
        self.contact_err = QLabel("")
        self.contact_err.setFixedHeight(15)
        self.contact_err.setStyleSheet("color: transparent; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        
        bl.addWidget(contact_lbl)
        bl.addWidget(self.contact_input)
        bl.addWidget(self.contact_err)
        
        # Delivery Address
        address_lbl = QLabel("Delivery Address (Calatagan)")
        address_lbl.setStyleSheet(f"color: {styles.MUTED}; font-size: 12px; font-weight: 700; border: none;")
        self.address_input = QComboBox()
        self.address_input.addItems([
            "Bagong Silang", "Balibago", "Balitoc", "Barangay 1",
            "Barangay 2", "Barangay 3", "Barangay 4", "Carretunan",
            "Gulod", "Lucsuhin", "Quilitisan", "Sta. Ana",
            "Talisay", "Tanagan"
        ])
        self.address_input.setFixedHeight(46)
        self.address_input.setStyleSheet(input_style)
        self.address_input.currentTextChanged.connect(self._validate)
        
        bl.addWidget(address_lbl)
        bl.addWidget(self.address_input)
        
        # Delivery Fee Display
        fee_box = QFrame()
        fee_box.setStyleSheet(f"background: {styles.BG}; border-radius: 8px; border: 1px dashed {styles.BORDER};")
        fl = QHBoxLayout(fee_box)
        fl.setContentsMargins(15, 10, 15, 10)
        
        fee_title = QLabel("Estimated Delivery Fee:")
        fee_title.setStyleSheet(f"color: {styles.MUTED}; font-size: 12px; font-weight: 600; border: none;")
        self.fee_lbl = QLabel("₱0.00")
        self.fee_lbl.setStyleSheet(f"color: {styles.TEXT}; font-size: 14px; font-weight: 800; border: none;")
        
        fl.addWidget(fee_title)
        fl.addStretch()
        fl.addWidget(self.fee_lbl)
        bl.addWidget(fee_box)
        
        bl.addSpacing(10)
        
        # Buttons
        btns = QHBoxLayout()
        btns.setSpacing(12)
        
        cancel = QPushButton("Cancel")
        cancel.setFixedHeight(45)
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {styles.TEXT};
                border: 1.5px solid {styles.BORDER};
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: {styles.BG};
            }}
        """)
        cancel.clicked.connect(self.reject)
        
        self.confirm_btn = QPushButton("Continue to Payment")
        self.confirm_btn.setFixedHeight(45)
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background: {styles.TEAL_DARK};
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: {styles.TEAL};
            }}
            QPushButton:disabled {{
                background: {styles.BORDER};
                color: {styles.MUTED};
            }}
        """)
        self.confirm_btn.clicked.connect(self._on_confirm)
        
        btns.addWidget(cancel)
        btns.addWidget(self.confirm_btn)
        bl.addLayout(btns)
        
        cl.addWidget(body)
        root.addWidget(card)

    def _validate(self, *args):
        name = self.name_input.text().strip()
        contact = self.contact_input.text().replace(" ", "").strip()
        address = self.address_input.currentText().strip()
        
        # Update delivery fee display
        self.delivery_fee = DELIVERY_FEES.get(address, 0.0)
        self.fee_lbl.setText(f"₱{self.delivery_fee:,.2f}")
        
        valid_contact = False
        
        if not contact:
            self.contact_err.setText("")
            self.contact_err.setStyleSheet("color: transparent; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        elif not contact.isdigit():
            self.contact_err.setText("Invalid number. Must contain digits only.")
            self.contact_err.setStyleSheet("color: #DC2626; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        elif len(contact) != 11:
            self.contact_err.setText("Invalid number. Must be exactly 11 digits.")
            self.contact_err.setStyleSheet("color: #DC2626; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        else:
            self.contact_err.setText("")
            self.contact_err.setStyleSheet("color: transparent; font-size: 11px; font-weight: 600; border: none; background: transparent;")
            valid_contact = True
        
        # All fields are required
        if name and valid_contact and address:
            self.confirm_btn.setEnabled(True)
        else:
            self.confirm_btn.setEnabled(False)
            
        self.update()
            
    def _on_confirm(self):
        self.customer_details = {
            "name": self.name_input.text().strip(),
            "contact": self.contact_input.text().strip(),
            "address": self.address_input.currentText().strip(),
            "delivery_fee": self.delivery_fee
        }
        self.accept()

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QColor
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        super().paintEvent(event)
