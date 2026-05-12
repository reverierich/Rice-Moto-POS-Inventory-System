"""
Cashier View for RiceMoto POS.
Features categories, threaded search, and a menu grid.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QScrollArea, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot, QTimer
from assets.ui.styles import BG, TEXT, MUTED, BORDER, TEAL_PALE, TEAL
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
        # Even with mock data, we simulate some work
        results = self.dc.filter_menu(self.query)
        self.finished.emit(results)


class CashierView(QWidget):
    """Main Ordering Interface."""
    add_to_cart = pyqtSignal(dict)

    def __init__(self, dc):
        super().__init__()
        self.dc = dc
        self.current_cat = "All"
        self._search_thread = None
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._on_search_debounced)
        
        self._setup_ui()
        self._render_menu(self.dc.get_menu())
        
        # Connect signals
        self.dc.sold_out_changed.connect(self._on_sold_out_global)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Left Side (Menu Area)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(30, 25, 20, 25)
        lv.setSpacing(20)
        
        # Top Bar: Search
        search_bar = QFrame()
        search_bar.setFixedHeight(50)
        search_bar.setStyleSheet(f"background: white; border-radius: 25px; border: 1.5px solid {BORDER};")
        sb_layout = QHBoxLayout(search_bar)
        sb_layout.setContentsMargins(20, 0, 20, 0)
        
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("font-size: 16px; background: transparent; border: none;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search restaurant, Food, Cuisine or a Dish")
        self.search_input.setStyleSheet("border: none; font-size: 14px; background: transparent;")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        
        sb_layout.addWidget(search_icon)
        sb_layout.addWidget(self.search_input)
        lv.addWidget(search_bar)
        
        # Categories
        cat_header = QHBoxLayout()
        cat_header.addWidget(QLabel("Categories"))
        cat_header.addStretch()
        view_all = QLabel("View all >")
        view_all.setStyleSheet(f"color: {TEXT}; font-weight: 700; font-size: 11px;")
        cat_header.addWidget(view_all)
        lv.addLayout(cat_header)
        
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
            self.cat_layout.insertWidget(self.cat_layout.count()-1, cw)
            self.cat_widgets[name] = cw
        
        lv.addWidget(self.cat_scroll)
        
        # Popular Dishes (Menu Grid)
        grid_header = QHBoxLayout()
        grid_header.addWidget(QLabel("Popular Dishes"))
        grid_header.addStretch()
        view_more = QLabel("View More >")
        view_more.setStyleSheet(f"color: {TEXT}; font-weight: 700; font-size: 11px;")
        grid_header.addWidget(view_more)
        lv.addLayout(grid_header)
        
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
        
        # Right Side (Order Panel)
        self.order_panel = OrderPanel()
        self.order_panel.order_confirmed.connect(self._on_order_confirmed)
        layout.addWidget(self.order_panel)

    def _render_menu(self, items):
        # Clear existing grid
        while self.grid.count():
            child = self.grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if not items:
            placeholder = QLabel("No dishes found matching your search.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet(f"color: {MUTED}; font-size: 14px; margin-top: 50px;")
            self.grid.addWidget(placeholder, 0, 0)
            return

        cols = 3 # Can be dynamic based on width
        for i, item in enumerate(items):
            card = MenuCard(item)
            card.add_to_cart.connect(self.order_panel.add_item)
            self.grid.addWidget(card, i // cols, i % cols)

    def _on_cat_clicked(self, name):
        self.current_cat = name
        for n, widget in self.cat_widgets.items():
            widget.set_active(n == name)
        
        self._render_menu(self.dc.get_menu(name))

    def _on_search_text_changed(self, text):
        # Debounce the search
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
        # Find and update the specific card in the grid if it exists
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
