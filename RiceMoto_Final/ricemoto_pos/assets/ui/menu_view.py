"""
Menu View for RiceMoto POS.
Shows food/menu cards with category filters and the order panel.
This is the Plate/Menu section — the main cashier ordering interface.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QScrollArea, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot, QTimer
from assets.ui.styles import BG, SURFACE, TEXT, MUTED, BORDER, TEAL_PALE, TEAL
from components.menu_cards import CategoryIcon, MenuCard
from components.order_panel import OrderPanel


class SearchWorker(QThread):
    """Threaded worker for filtering large datasets."""
    finished = pyqtSignal(list)

    def __init__(self, dc, query):
        super().__init__()
        self.dc = dc
        self.query = query

    def run(self):
        results = self.dc.filter_menu(self.query)
        self.finished.emit(results)


class MenuView(QWidget):
    """Main Ordering / Menu Interface (Plate section)."""
    add_to_cart = pyqtSignal(dict)

    def __init__(self, dc):
        super().__init__()
        self.dc = dc
        self.current_cat = "All"
        self._search_thread = None
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._on_search_debounced)

        self._show_all_dishes = False

        self._setup_ui()
        self._render_menu(self.dc.get_menu())

        # Connect signals
        self.dc.sold_out_changed.connect(self._on_sold_out_global)
        self.dc.menu_filtered.connect(self._render_menu)
        self.dc.stock_updated.connect(lambda name, qty: self._render_menu(self.dc.get_menu(self.current_cat)))

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Left Side (Menu Area) ──────────────────────────────────
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(30, 25, 20, 25)
        lv.setSpacing(20)

        # Search bar
        search_bar = QFrame()
        search_bar.setFixedHeight(50)
        search_bar.setStyleSheet(
            f"background: {SURFACE}; border-radius: 25px; border: 1.5px solid {BORDER};"
        )
        sb_layout = QHBoxLayout(search_bar)
        sb_layout.setContentsMargins(20, 0, 20, 0)

        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("font-size: 18px; background: transparent; border: none;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search restaurant, Food, Cuisine or a Dish"
        )
        self.search_input.setStyleSheet(
            "border: none; font-size: 14px; background: transparent;"
        )
        self.search_input.textChanged.connect(self._on_search_text_changed)

        sb_layout.addWidget(search_icon)
        sb_layout.addWidget(self.search_input)
        lv.addWidget(search_bar)

        # Categories header
        cat_header = QHBoxLayout()
        cat_title = QLabel("Categories")
        cat_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {TEXT};")
        cat_header.addWidget(cat_title)
        cat_header.addStretch()
        lv.addLayout(cat_header)

        # Category scroll
        self.cat_scroll = QScrollArea()
        self.cat_scroll.setWidgetResizable(True)
        self.cat_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.cat_scroll.setFixedHeight(100)
        self.cat_scroll.setStyleSheet("background: transparent;")

        cat_container = QWidget()
        self.cat_layout = QHBoxLayout(cat_container)
        self.cat_layout.setContentsMargins(0, 0, 0, 0)
        self.cat_layout.setSpacing(15)
        self.cat_layout.addStretch()
        self.cat_scroll.setWidget(cat_container)

        categories = [
            ("🍽", "All"), ("🥤", "Beverages"), ("🍳", "Silog Meals"), 
            ("🍚", "Rice Bowls"), ("🍟", "Snacks")
        ]
        self.cat_widgets = {}
        for emoji, name in categories:
            cw = CategoryIcon(emoji, name, name == "All")
            cw.clicked.connect(self._on_cat_clicked)
            self.cat_layout.insertWidget(self.cat_layout.count() - 1, cw)
            self.cat_widgets[name] = cw

        lv.addWidget(self.cat_scroll)

        # Menu grid header
        grid_header = QHBoxLayout()
        self.grid_title = QLabel("Popular Dishes")
        self.grid_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {TEXT};")
        grid_header.addWidget(self.grid_title)
        grid_header.addStretch()
        self.view_more = QLabel("View More >")
        self.view_more.setStyleSheet(f"color: {TEXT}; font-weight: 700; font-size: 11px;")
        self.view_more.setCursor(Qt.CursorShape.PointingHandCursor)
        self.view_more.mousePressEvent = self._toggle_view_more
        grid_header.addWidget(self.view_more)
        lv.addLayout(grid_header)

        # Menu scroll + grid
        self.menu_scroll = QScrollArea()
        self.menu_scroll.setWidgetResizable(True)
        self.menu_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.menu_scroll.setStyleSheet("background: transparent;")

        self.menu_container = QWidget()
        self.grid = QGridLayout(self.menu_container)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(20)
        self.menu_scroll.setWidget(self.menu_container)
        lv.addWidget(self.menu_scroll)

        layout.addWidget(left, stretch=1)

        # ── Right Side (Order Panel) ──────────────────────────────
        self.order_panel = OrderPanel()
        self.order_panel.order_confirmed.connect(self._on_order_confirmed)
        layout.addWidget(self.order_panel)

    # ── Helpers ──────────────────────────────────────────────────

    def _render_menu(self, items):
        """Clear and re-populate the menu grid."""
        while self.grid.count():
            child = self.grid.takeAt(0)
            w = child.widget()
            if w:
                w.hide()
                w.setParent(None)

        if not items:
            placeholder = QLabel("No dishes found matching your search.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet(
                f"color: {MUTED}; font-size: 14px; margin-top: 50px;"
            )
            self.grid.addWidget(placeholder, 0, 0)
            return

        # Handle 'View More' logic
        if self.current_cat == "All" and not self.search_input.text().strip():
            if not self._show_all_dishes:
                # Show top 6 popular dishes
                items = sorted(items, key=lambda x: x.get("sold", 0), reverse=True)[:6]
                self.grid_title.setText("Popular Dishes")
                self.view_more.setText("View More >")
                self.view_more.show()
            else:
                self.grid_title.setText("All Dishes")
                self.view_more.setText("View Less <")
                self.view_more.show()
        else:
            # Hide the toggle if searching or filtering
            if self.search_input.text().strip():
                self.grid_title.setText("Search Results")
            else:
                self.grid_title.setText(f"{self.current_cat} Dishes")
            self.view_more.hide()

        cols = 3
        for i, item in enumerate(items):
            card = MenuCard(item)
            card.add_to_cart.connect(self.order_panel.add_item)
            card.image_updated.connect(self.dc.update_menu_image)
            self.grid.addWidget(card, i // cols, i % cols)

    def _on_cat_clicked(self, name):
        self.current_cat = name
        self._show_all_dishes = False # Reset on category change
        for n, widget in self.cat_widgets.items():
            widget.set_active(n == name)
        self._render_menu(self.dc.get_menu(name))

    def _toggle_view_more(self, event):
        self._show_all_dishes = not self._show_all_dishes
        self._render_menu(self.dc.get_menu(self.current_cat))

    def _on_search_text_changed(self, text):
        self._debounce_timer.start(300)

    def _on_search_debounced(self):
        query = self.search_input.text()
        if self._search_thread and self._search_thread.isRunning():
            self._search_thread.terminate()
            self._search_thread.wait()
        self._search_thread = SearchWorker(self.dc, query)
        self._search_thread.finished.connect(self._render_menu)
        self._search_thread.start()

    def _on_sold_out_global(self, name, state):
        for i in range(self.grid.count()):
            widget = self.grid.itemAt(i).widget()
            if isinstance(widget, MenuCard) and widget.item["name"] == name:
                widget.update_state(state)

    def _on_order_confirmed(self, items, order_type, payment_method, customer_details=None, delivery_fee=0):
        order_code = self.dc.add_order(items, order_type, payment_method, customer_details, delivery_fee)
        if order_code:
            from components.receipt_dialog import ReceiptDialog
            cashier_name = self.dc.current_user.get("display_name", "Staff") if self.dc.current_user else "Manager"
            dialog = ReceiptDialog(order_code, order_type, items, cashier_name, payment_method, self, customer_details, dc=self.dc)
            dialog.exec()
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Order Error", "Failed to save the order to the database. Please check your connection.")
