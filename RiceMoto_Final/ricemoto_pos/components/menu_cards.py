"""
Menu card and category components for RiceMoto POS.
Implements circular categories and shadowed menu cards.
"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QPushButton, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QFont, QPixmap
from assets.ui.styles import (
    TEAL, TEAL_DARK, TEAL_PALE, TEAL_LIGHT, BORDER, 
    SURFACE, TEXT, MUTED, ACCENT, BG, get_shadow
)


class CategoryIcon(QWidget):
    """Circular Category Icon based on visual fidelity requirements."""
    clicked = pyqtSignal(str)

    def __init__(self, emoji, name, active=False):
        super().__init__()
        self.name = name
        self._active = active
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.circle = QLabel(emoji)
        self.circle.setFixedSize(60, 60)
        self.circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_circle_style()
        
        self.label = QLabel(name)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {MUTED};")
        
        layout.addWidget(self.circle)
        layout.addWidget(self.label)

    def _update_circle_style(self):
        border_style = f"3px solid {ACCENT}" if self._active else "none"
        self.circle.setStyleSheet(f"""
            QLabel {{
                font-size: 26px;
                background: {BG};
                border-radius: 30px;
                border: {border_style};
            }}
        """)

    def set_active(self, active):
        self._active = active
        self._update_circle_style()

    def mousePressEvent(self, event):
        self.clicked.emit(self.name)


class MenuCard(QFrame):
    """Menu Item Card with shadow and dynamic state."""
    add_to_cart = pyqtSignal(dict)
    image_updated = pyqtSignal(str, bytes)  # item_name, image_data (binary)

    def __init__(self, item, button_size=56):
        super().__init__()
        self.item = item
        self.button_size = button_size
        self.setFixedSize(380, 480)
        self.setGraphicsEffect(get_shadow(16))
        self._setup_ui()

    def _setup_ui(self):
        item = self.item
        is_soldout = item.get("soldout", False)
        image_data = item.get("image_data", None)
        
        # Main Style
        border_color = "red" if is_soldout else BORDER
        self.setStyleSheet(f"""
            QFrame {{
                background: {SURFACE};
                border-radius: 24px;
                border: 1.5px solid {border_color};
                padding: 0px;
                margin: 0px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 2, 22, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Image Area
        self.img_area = QLabel()
        self.img_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_area.setFixedSize(336, 258)
        self.img_area.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.img_area.setToolTip("Click to add/change photo")
        self.img_area.mousePressEvent = lambda e: self._pick_image()

        if image_data:
            # Convert binary data to QPixmap
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            # Scale to cover the entire image area (stretch/fill)
            scaled_pixmap = pixmap.scaled(
                336, 258,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.img_area.setPixmap(scaled_pixmap)
            self.img_area.setStyleSheet(f"""
                QLabel {{
                    background: {BG};
                    border-radius: 24px 24px 0 0;
                    border: none;
                    padding: 0px;
                    margin: 0px;
                }}
            """)
        else:
            # Show "Add Photo" placeholder
            self.img_area.setText("📷  Add Photo")
            self.img_area.setStyleSheet(f"""
                QLabel {{
                    font-size: 16px;
                    font-weight: 600;
                    color: {MUTED};
                    background: {BG};
                    border-radius: 24px 24px 0 0;
                    border: none;
                    border-bottom: 1.5px dashed {BORDER};
                    padding: 0px;
                    margin: 0px;
                }}
            """)
        
        # Sold Out Badge
        if is_soldout:
            badge = QLabel("SOLD OUT", self.img_area)
            badge.setStyleSheet("""
                background: rgba(0, 0, 0, 0.7);
                color: white;
                font-size: 10px;
                font-weight: bold;
                padding: 4px 10px;
                border-radius: 12px;
            """)
            badge.move(10, 10)

        # Info Area
        info = QWidget()
        info.setStyleSheet("background: transparent; border: none;")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(18, 16, 18, 18)
        info_layout.setSpacing(6)
        
        name = QLabel(item["name"])
        name.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {TEXT};")
        name.setWordWrap(True)
        
        from_lbl = QLabel("Starting From")
        from_lbl.setStyleSheet(f"font-size: 11px; color: {MUTED};")
        
        price_row = QHBoxLayout()
        price = QLabel(f"₱{item['price']:.2f}")
        price.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {TEAL};")
        price_row.addWidget(price)
        price_row.addStretch()

        rating = QLabel(f"★ {item['rating']}  ·  {item['sold']} sold")
        rating.setStyleSheet("font-size: 12px; color: #F97316; font-weight: 600;")

        add_btn = QPushButton("+")
        add_btn.setFixedSize(self.button_size, self.button_size)
        add_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # Create a centered font for the plus symbol
        font_size = int(self.button_size * 0.5)
        btn_font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        btn_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0)
        add_btn.setFont(btn_font)
        
        add_btn.setFlat(True)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {TEAL};
                color: white;
                border-radius: {self.button_size // 2}px;
                padding: 0;
                margin: 0;
                border: 2px solid rgba(255,255,255,0.85);
                text-align: center;
                line-height: {self.button_size}px;
            }}
            QPushButton:hover {{ background: {TEAL_DARK}; }}
            QPushButton:disabled {{ background: {MUTED}; color: #FFFFFF; border-color: rgba(255,255,255,0.35); }}
        """)
        add_btn.setEnabled(not is_soldout)
        add_btn.setToolTip("Add to cart")
        add_btn.clicked.connect(lambda: self.add_to_cart.emit(self.item))

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 10, 0, 0)
        action_row.addStretch()
        action_row.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

        info_layout.addWidget(name)
        info_layout.addWidget(from_lbl)
        info_layout.addLayout(price_row)
        info_layout.addWidget(rating)
        info_layout.addLayout(action_row)
        
        layout.addWidget(self.img_area)
        layout.addWidget(info)
        
        if is_soldout:
            self.setOpacity(0.6)

    def _pick_image(self):
        """Open a file dialog to select and save a custom dish photo as LONGBLOB."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select Photo for {self.item['name']}",
            "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if not file_path:
            return

        # Read the image file as binary data
        try:
            with open(file_path, 'rb') as f:
                image_data = f.read()
        except Exception as e:
            print(f"Error reading image file: {e}")
            return

        # Update the item data and signal for database save
        self.item["image_data"] = image_data
        self.image_updated.emit(self.item["name"], image_data)

        # Refresh the card display
        for i in reversed(range(self.layout().count())):
            w = self.layout().itemAt(i).widget()
            if w:
                w.setParent(None)
        self._setup_ui()

    def setOpacity(self, opacity):
        # We can simulate opacity using alpha in stylesheets or QGraphicsOpacityEffect,
        # but for simple modularity we just adjust the style of children.
        pass

    def update_state(self, is_soldout):
        self.item["soldout"] = is_soldout
        # Clear layout and re-run setup
        for i in reversed(range(self.layout().count())): 
            self.layout().itemAt(i).widget().setParent(None)
        self._setup_ui()
