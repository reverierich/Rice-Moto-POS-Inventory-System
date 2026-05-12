"""
Custom Sidebar component for RiceMoto POS.
Slim design (~80px) with centered items, colored active states,
left-border indicator, hover effects, and smooth transitions.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QVariantAnimation, QByteArray
from PyQt6.QtGui import QCursor, QColor
from assets.ui.styles import TEAL_DARK, ACCENT, WHITE, MUTED, TEXT, BG

# Per-key active accent colors — one per nav section
NAV_COLORS = {
    "menu":      "#FF6B35",   # Orange  — Plate / Menu
    "analytics": "#3B82F6",   # Blue    — Analytics
    "orders":    "#F97316",   # Amber   — Orders / Clipboard
    "inventory": "#8B5CF6",   # Purple  — Inventory / Box
    "settings":  "#94A3B8",   # Slate   — Settings Gear
    "logout":    "#EF4444",   # Red     — Logout
}

# Nav entries: (emoji, short label, unique key)
NAV_ENTRIES = [
    ("🍽", "Menu",      "menu"),
    ("📊", "Analytics", "analytics"),
    ("📋", "Orders",    "orders"),
    ("📦", "Inventory", "inventory"),
]

BOTTOM_ENTRIES = [
    ("⚙",  "Settings", "settings"),
    ("🚪", "Logout",   "logout"),
]


class SidebarItem(QWidget):
    """Single navigation button in the sidebar with smooth animations."""
    clicked = pyqtSignal(str)

    def __init__(self, icon_text: str, label: str, key: str, active: bool = False):
        super().__init__()
        self.key = key
        self._active = active
        self._color_str = NAV_COLORS.get(key, "#007B6E")
        self.setFixedSize(72, 68)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip(label)

        # Outer wrapper
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Inner container
        self._inner = QFrame()
        self._inner.setFixedSize(68, 66)

        inner_layout = QVBoxLayout(self._inner)
        inner_layout.setContentsMargins(0, 8, 0, 8)
        inner_layout.setSpacing(3)
        inner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_lbl = QLabel(icon_text)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setStyleSheet("font-size: 22px; background: transparent; border: none;")

        self.text_lbl = QLabel(label)
        self.text_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        inner_layout.addWidget(self.icon_lbl)
        inner_layout.addWidget(self.text_lbl)
        outer.addWidget(self._inner, alignment=Qt.AlignmentFlag.AlignCenter)

        # Setup smooth color transition animation
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(150)
        self._anim.valueChanged.connect(self._on_anim_step)
        
        # Initial style setup
        self._apply_style(animate=False)

    def _on_anim_step(self, color: QColor):
        """Update border color dynamically during transition to avoid background rectangles."""
        border_color = f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha() / 255.0})"
        # Maintain constant border width to prevent shifting content, just change color
        self._inner.setStyleSheet(f"QFrame {{ background: transparent; border-left: 4px solid {border_color}; border-radius: 0px; }}")

    def _apply_style(self, animate=True):
        """Apply active/inactive static text styles and trigger border animation."""
        if self._active:
            target_color = QColor(self._color_str)
            self.text_lbl.setStyleSheet(f"font-size: 10px; color: {self._color_str}; font-weight: 800; letter-spacing: 0.5px; background: transparent; border: none;")
            self.icon_lbl.setStyleSheet("font-size: 24px; background: transparent; border: none;")
        else:
            target_color = QColor(Qt.GlobalColor.transparent)
            self.text_lbl.setStyleSheet(f"font-size: 9px; color: {MUTED}; font-weight: 600; letter-spacing: 0.4px; background: transparent; border: none;")
            self.icon_lbl.setStyleSheet("font-size: 20px; background: transparent; border: none;")

        if animate:
            self._anim.stop()
            start_color = self._anim.currentValue() if self._anim.currentValue() else QColor(Qt.GlobalColor.transparent)
            if not isinstance(start_color, QColor):
                start_color = QColor(Qt.GlobalColor.transparent)
            self._anim.setStartValue(start_color)
            self._anim.setEndValue(target_color)
            self._anim.start()
        else:
            self._on_anim_step(target_color)

    def set_active(self, active: bool):
        if self._active == active:
            return
        self._active = active
        self._apply_style(animate=True)

    def mousePressEvent(self, event):
        self.clicked.emit(self.key)

    def enterEvent(self, event):
        if not self._active:
            self._anim.stop()
            start_color = self._anim.currentValue() if self._anim.currentValue() else QColor(Qt.GlobalColor.transparent)
            if not isinstance(start_color, QColor):
                start_color = QColor(Qt.GlobalColor.transparent)
            
            c = QColor(self._color_str)
            c.setAlpha(120) # Hover indicator
            self._anim.setStartValue(start_color)
            self._anim.setEndValue(c)
            self._anim.start()
            
            self.text_lbl.setStyleSheet(f"font-size: 9px; color: {TEXT}; font-weight: 600; letter-spacing: 0.4px; background: transparent; border: none;")
            self.icon_lbl.setStyleSheet("font-size: 22px; background: transparent; border: none;")

    def leaveEvent(self, event):
        if not self._active:
            self._apply_style(animate=True)


class Sidebar(QWidget):
    """Main sidebar navigation widget."""
    nav_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(84)
        
        # Detect light mode
        is_light_mode = BG != "#121212"
        sidebar_bg = BG if is_light_mode else TEAL_DARK
        self.setStyleSheet(f"QWidget {{ background: {sidebar_bg}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 20, 6, 20)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Logo
        import os
        from PyQt6.QtGui import QPixmap
        
        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFixedSize(52, 52)
        
        logo_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'logo.png')
        
        # Detect light mode (consistent with SettingsView logic)
        is_light_mode = BG != "#121212"
        svg_filename = 'logo_black.svg' if is_light_mode else 'logo.svg'
        svg_path = os.path.join(os.path.dirname(__file__), '..', 'assets', svg_filename)
        
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            logo.setPixmap(pixmap.scaled(52, 52, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            logo.setStyleSheet("background: transparent; border: none;")
        elif os.path.exists(svg_path):
            pixmap = QPixmap(svg_path)
            logo.setPixmap(pixmap.scaled(52, 52, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            logo.setStyleSheet("background: transparent; border: none;")
        else:
            logo.setText("🍽")
            logo.setStyleSheet(f"font-size: 26px; background: {ACCENT}; border-radius: 18px; border: none;")
            
        layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(10)

        # Divider
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setFixedWidth(44)
        div_color = "rgba(0,0,0,0.08)" if is_light_mode else "rgba(255,255,255,0.12)"
        divider.setStyleSheet(f"background: {div_color}; border: none;")
        layout.addWidget(divider, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(6)

        # Main Nav Items
        self._items: dict[str, SidebarItem] = {}

        for icon, label, key in NAV_ENTRIES:
            item = SidebarItem(icon, label, key, active=(key == "menu"))
            item.clicked.connect(self._on_nav_clicked)
            layout.addWidget(item, alignment=Qt.AlignmentFlag.AlignHCenter)
            self._items[key] = item

        layout.addStretch()

        # Divider
        div2 = QFrame()
        div2.setFixedHeight(1)
        div2.setFixedWidth(44)
        div2.setStyleSheet(f"background: {div_color}; border: none;")
        layout.addWidget(div2, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(4)

        # Bottom Items
        for icon, label, key in BOTTOM_ENTRIES:
            item = SidebarItem(icon, label, key)
            item.clicked.connect(self._on_nav_clicked)
            layout.addWidget(item, alignment=Qt.AlignmentFlag.AlignHCenter)
            self._items[key] = item

    def _on_nav_clicked(self, key: str):
        """Update active state for all items (except logout), then emit signal."""
        if key != "logout":
            for k, item in self._items.items():
                item.set_active(k == key)
        self.nav_changed.emit(key)

    def set_active_key(self, key: str):
        """Programmatically set the active nav item (e.g. on startup/login)."""
        for k, item in self._items.items():
            item.set_active(k == key)
        self.nav_changed.emit(key)

    def set_role(self, role: str):
        """Show/hide sidebar items based on user role."""
        manager_only = ["analytics", "settings"]
        for key, item in self._items.items():
            if key == "logout":
                item.setVisible(True)
                continue
                
            if role == "Manager":
                item.setVisible(True)
            else:
                item.setVisible(key not in manager_only)
