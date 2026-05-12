"""
RiceMoto POS — Modular Professional Restaurant Management System.
Entry point and Main Controller.
"""
import sys
from builtins import super

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget,
    QHBoxLayout, QVBoxLayout, QMessageBox, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve

# Local Modules
from assets.ui.styles import GLOBAL_QSS, BG
from database.database_manager import DataController
from components.sidebar import Sidebar
from components.topbar import TopBar
from assets.ui.login_view import LoginView, RegisterView
from assets.ui.menu_view import MenuView
from assets.ui.analytics_view import AnalyticsView
from assets.ui.orders_view import OrdersView
from assets.ui.inventory_view import InventoryView
from assets.ui.settings_view import SettingsView


# Maps sidebar key → (view_stack_index, page_title)
NAV_MAP = {
    "menu":      (0, "Menu & Ordering"),
    "analytics": (1, "Analytics Dashboard"),
    "orders":    (2, "Orders & Kitchen Queue"),
    "inventory": (3, "Inventory & Products"),
    "settings":  (4, "Settings"),
}


class AnimatedStackedWidget(QStackedWidget):
    """QStackedWidget with fade-in animation on page switch."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._animation_duration = 180  # ms
        self._current_anim = None

    def switch_to(self, index: int):
        """Animate fade-out of current page then switch and fade-in new page."""
        if index == self.currentIndex():
            return

        new_widget = self.widget(index)
        if new_widget is None:
            return

        # Ensure a QGraphicsOpacityEffect is set on the incoming widget
        effect = new_widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(new_widget)
            new_widget.setGraphicsEffect(effect)

        effect.setOpacity(0.0)
        self.setCurrentIndex(index)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(self._animation_duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: new_widget.setGraphicsEffect(None))
        anim.start()
        # Keep reference so GC doesn't collect it
        self._current_anim = anim


class MainApp(QMainWindow):
    """Master window handling navigation and global state."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RiceMoto POS — Restaurant Professional")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 750)
        self.setStyleSheet(f"background: {BG};")

        # Data Controller
        self.dc = DataController()

        # ── Root screen stack (login / register / main) ────────
        self.central_stack = QStackedWidget()
        self.setCentralWidget(self.central_stack)

        # Login / Register
        self.login_view    = LoginView()
        self.register_view = RegisterView()

        # Main app shell
        self.main_app_widget = QWidget()
        self._setup_main_app_layout()

        self.central_stack.addWidget(self.login_view)       # index 0
        self.central_stack.addWidget(self.register_view)    # index 1
        self.central_stack.addWidget(self.main_app_widget)  # index 2

        # Navigation connections
        self.login_view.login_requested.connect(self._handle_login)
        self.login_view.register_clicked.connect(
            lambda: self.central_stack.setCurrentIndex(1)
        )
        self.register_view.back_clicked.connect(
            lambda: self.central_stack.setCurrentIndex(0)
        )
        self.register_view.register_requested.connect(self._handle_registration)

        import sys
        if "--apply-theme" in sys.argv:
            # Seamlessly skip login after a theme update and jump to Settings
            user_name = "Admin User (Manager)"
            role = "Manager"
            for arg in sys.argv:
                if arg.startswith("--user="):
                    user_name = arg.split("=", 1)[1]
                elif arg.startswith("--role="):
                    role = arg.split("=", 1)[1]
            
            self.topbar.set_user(user_name)
            self.sidebar.set_role(role)
            self.inventory_view.set_role(role)
            
            # Mock the user in DataController so log writes don't fail
            display_name = user_name.split(" (")[0] if " (" in user_name else user_name
            self.dc.current_user = {
                "display_name": display_name,
                "role": role,
                "first_name": display_name,
                "last_name": ""
            }
            
            self.sidebar.set_active_key("settings")
            self.view_stack.setCurrentIndex(4) # Settings is index 4
            self.topbar.set_page_title("Settings")
            self.central_stack.setCurrentIndex(2)
        else:
            self.central_stack.setCurrentIndex(0)

    # ── Main App Layout ───────────────────────────────────────

    def _setup_main_app_layout(self):
        """Builds the main dashboard: Sidebar + TopBar + page stack."""
        layout = QHBoxLayout(self.main_app_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.nav_changed.connect(self._handle_navigation)
        layout.addWidget(self.sidebar)

        # Right content area
        content_area = QWidget()
        cv = QVBoxLayout(content_area)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)

        # TopBar
        self.topbar = TopBar()
        cv.addWidget(self.topbar)

        # ── Page stack (one widget per nav section) ────────────
        self.view_stack = AnimatedStackedWidget()
        self.view_stack.setStyleSheet(f"background: {BG};")

        self.menu_view      = MenuView(self.dc)       # 0 — Plate / Menu
        self.analytics_view = AnalyticsView(self.dc)  # 1 — Analytics
        self.orders_view    = OrdersView(self.dc)     # 2 — Orders / Clipboard
        self.inventory_view = InventoryView(self.dc)  # 3 — Inventory / Box
        self.settings_view  = SettingsView(self.dc)   # 4 — Settings Gear

        for view in [
            self.menu_view, self.analytics_view, self.orders_view,
            self.inventory_view, self.settings_view
        ]:
            self.view_stack.addWidget(view)

        cv.addWidget(self.view_stack)
        layout.addWidget(content_area)

        # Start on the Menu page (matches sidebar default)
        self.view_stack.setCurrentIndex(0)

    # ── Navigation Handler ────────────────────────────────────

    def _handle_navigation(self, key: str):
        """Switch visible page based on sidebar selection."""
        if key == "logout":
            self.central_stack.setCurrentIndex(0)
            self.sidebar.set_active_key("menu")
            return

        entry = NAV_MAP.get(key)
        if entry:
            idx, title = entry
            self.view_stack.switch_to(idx)
            self.topbar.set_page_title(title)

    # ── Auth Handlers ─────────────────────────────────────────

    def _handle_login(self, username, password):
        user = self.dc.login(username, password)
        if user:
            role = str(user.get("role", "Staff")).title()
            # Update topbar with logged-in user's name and role
            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')} ({role})".strip()
            self.topbar.set_user(full_name)

            # Apply role permissions
            self.sidebar.set_role(role)
            self.inventory_view.set_role(role)

            # Reset sidebar active state to menu on each login
            self.sidebar.set_active_key("menu")
            self.view_stack.setCurrentIndex(0)
            self.topbar.set_page_title("Menu & Ordering")

            self.central_stack.setCurrentIndex(2)
        else:
            self._show_styled_message("Login Failed", "Invalid username or password.", QMessageBox.Icon.Critical)

    def _show_styled_message(self, title, text, icon=QMessageBox.Icon.Information):
        """Show a QMessageBox that properly inherits the global theme."""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(icon)
        # Force the global style onto the dialog
        msg.setStyleSheet(GLOBAL_QSS + f"\nQMessageBox {{ background-color: {BG}; }}")
        msg.exec()

    def _handle_registration(self, data):
        success, msg = self.dc.register(data)
        if success:
            self._show_styled_message("Registration Success", msg, QMessageBox.Icon.Information)
            self.central_stack.setCurrentIndex(0)
        else:
            self._show_styled_message("Registration Error", msg, QMessageBox.Icon.Warning)


def main():
    from PyQt6.QtCore import qInstallMessageHandler
    def handler(mode, context, message):
        if "QFont::setPointSize" in message or "QThreadStorage" in message:
            return
        print(message)
    qInstallMessageHandler(handler)

    app = QApplication(sys.argv)
    app.setApplicationName("RiceMoto POS")
    app.setStyleSheet(GLOBAL_QSS)

    window = MainApp()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
