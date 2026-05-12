"""
Inventory View for RiceMoto POS.
Two tabs: Menu Products + Raw Supplies (connected to MySQL).
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QPushButton, QLineEdit,
    QDialog, QFormLayout, QDialogButtonBox, QMessageBox,
    QDoubleSpinBox, QSpinBox, QComboBox, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from assets.ui.styles import (
    TEXT, MUTED, BORDER, BG, SURFACE, TEAL, TEAL_DARK,
    TEAL_PALE, TEAL_LIGHT, ORANGE, RED, GREEN, BLUE, get_shadow
)


class ItemDialog(QDialog):
    def __init__(self, parent=None, item_data=None):
        super().__init__(parent)
        self.setWindowTitle("Add Item" if not item_data else "Edit Item")
        self.setFixedSize(380, 350)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {SURFACE}; border-radius: 15px; }}
            QLabel {{ color: {TEXT}; font-weight: bold; font-size: 13px; }}
            QLineEdit, QComboBox, QDoubleSpinBox {{
                background: white; border: 1.5px solid {BORDER};
                border-radius: 8px; padding: 6px; color: black;
            }}
            QPushButton {{
                min-width: 80px; padding: 8px 16px; border-radius: 8px;
                font-weight: bold; font-size: 12px;
            }}
        """)
        layout = QFormLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        self.name_input = QLineEdit()
        self.emoji_input = QLineEdit()
        self.emoji_input.setMaxLength(2)
        self.cat_input = QComboBox()
        self.cat_input.addItems(["Beverages", "Silog Meals", "Rice Bowls", "Snacks"])
        self.price_input = QDoubleSpinBox()
        self.price_input.setMaximum(9999.99)
        self.price_input.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons) # Cleaner look

        if item_data:
            self.name_input.setText(item_data.get("name", ""))
            self.emoji_input.setText(item_data.get("emoji", ""))
            self.cat_input.setCurrentText(item_data.get("category", "Beverages"))
            self.price_input.setValue(item_data.get("price", 0.0))

        layout.addRow("Name:", self.name_input)
        layout.addRow("Emoji:", self.emoji_input)
        layout.addRow("Category:", self.cat_input)
        layout.addRow("Price (₱):", self.price_input)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        # Style the buttons explicitly
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Save Item")
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setStyleSheet(f"background: {TEAL_DARK}; color: white;")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setStyleSheet(f"background: #E2E8F0; color: {TEXT};")
        
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "emoji": self.emoji_input.text().strip() or "🍱",
            "category": self.cat_input.currentText(),
            "price": self.price_input.value(),
            "soldout": False, "sold": 0, "rating": 5.0
        }


class SupplyDialog(QDialog):
    """Dialog to add/edit a raw supply item."""
    def __init__(self, parent=None, data=None, categories=None):
        super().__init__(parent)
        self.setWindowTitle("Add Supply" if not data else "Edit Supply")
        self.setFixedSize(400, 380)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {SURFACE}; border-radius: 15px; }}
            QLabel {{ color: {TEXT}; font-weight: bold; font-size: 13px; }}
            QLineEdit, QComboBox, QDoubleSpinBox {{
                background: white; border: 1.5px solid {BORDER};
                border-radius: 8px; padding: 6px; color: black;
            }}
            QPushButton {{
                min-width: 80px; padding: 8px 16px; border-radius: 8px;
                font-weight: bold; font-size: 12px;
            }}
        """)
        layout = QFormLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(12)

        self.name_input = QLineEdit()
        self.cat_input = QComboBox()
        self.cat_input.setEditable(True)
        cats = categories or ["Silog Meals","Rice Bowls","Snacks","Beverages","Fresh Fruits","Buko Pandan","Cookies N Cream","Kape ng Ina Mo"]
        self.cat_input.addItems(cats)
        self.unit_input = QComboBox()
        self.unit_input.setEditable(True)
        self.unit_input.addItems(["pcs","kg","liters","packs","cans","bottles","gallons"])
        self.qty_input = QDoubleSpinBox()
        self.qty_input.setMaximum(99999)
        self.qty_input.setDecimals(1)
        self.qty_input.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.min_input = QDoubleSpinBox()
        self.min_input.setMaximum(99999)
        self.min_input.setDecimals(1)
        self.min_input.setValue(5)
        self.min_input.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)

        if data:
            self.name_input.setText(str(data.get("name","")))
            self.cat_input.setCurrentText(str(data.get("category","")))
            self.unit_input.setCurrentText(str(data.get("unit","pcs")))
            self.qty_input.setValue(float(data.get("quantity",0)))
            self.min_input.setValue(float(data.get("min_stock",5)))

        layout.addRow("Name:", self.name_input)
        layout.addRow("Category:", self.cat_input)
        layout.addRow("Unit:", self.unit_input)
        layout.addRow("Quantity:", self.qty_input)
        layout.addRow("Min Stock:", self.min_input)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Save Supply")
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setStyleSheet(f"background: {TEAL_DARK}; color: white;")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setStyleSheet(f"background: #E2E8F0; color: {TEXT};")

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "category": self.cat_input.currentText().strip(),
            "unit": self.unit_input.currentText().strip() or "pcs",
            "quantity": self.qty_input.value(),
            "min_stock": self.min_input.value(),
            "notes": None
        }


class InventoryView(QWidget):
    """Product / Stock Inventory management page with tabs."""

    def __init__(self, dc):
        super().__init__()
        self.dc = dc
        self.setStyleSheet(f"background: {BG};")
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 25, 30, 25)
        main_layout.setSpacing(20)

        # Header
        header = QHBoxLayout()
        title = QLabel("Inventory & Products")
        title.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {TEXT};")
        header.addWidget(title)
        header.addStretch()
        main_layout.addLayout(header)

        # Summary Cards
        summary_row = QHBoxLayout()
        summary_row.setSpacing(15)
        self._total_card = self._make_summary_card("Total Items", "0", TEAL)
        self._avail_card = self._make_summary_card("Available", "0", GREEN)
        self._soldout_card = self._make_summary_card("Sold Out", "0", RED)
        self._low_stock_card = self._make_summary_card("Low Stock Supplies", "0", ORANGE)
        for c in [self._total_card, self._avail_card, self._soldout_card, self._low_stock_card]:
            summary_row.addWidget(c)
        main_layout.addLayout(summary_row)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: transparent; }}
            QTabBar::tab {{
                background: {SURFACE}; color: {MUTED}; border: 1.5px solid {BORDER};
                border-bottom: none; border-radius: 12px 12px 0 0;
                padding: 10px 24px; font-weight: 700; font-size: 12px; margin-right: 4px;
            }}
            QTabBar::tab:selected {{ background: {TEAL_DARK}; color: white; border-color: {TEAL_DARK}; }}
        """)

        # Tab 1 — Menu Products
        self._build_menu_tab()
        # Tab 2 — Raw Supplies
        self._build_supplies_tab()

        main_layout.addWidget(self.tabs)

        self.dc.sold_out_changed.connect(lambda *_: self._load_menu_data())
        self.dc.stock_updated.connect(lambda *_: self._load_menu_data())
        self.dc.order_status_changed.connect(lambda *_: self._load_menu_data())
        self._load_menu_data()
        self._load_supplies_data()

    # ── Tab 1: Menu Products ────────────────────────────────────
    def _build_menu_tab(self):
        tab = QWidget()
        vl = QVBoxLayout(tab)
        vl.setContentsMargins(0, 15, 0, 0)
        vl.setSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        self.add_btn = QPushButton("➕ Add Item")
        self.add_btn.setStyleSheet(f"QPushButton {{ background: {ORANGE}; color: white; border-radius: 12px; font-size: 12px; font-weight: 700; padding: 10px 15px; }}")
        self.edit_btn = QPushButton("✏️ Edit")
        self.edit_btn.setStyleSheet(f"QPushButton {{ background: {BLUE}; color: white; border-radius: 12px; font-size: 12px; font-weight: 700; padding: 10px 15px; }}")
        self.del_btn = QPushButton("🗑️ Delete")
        self.del_btn.setStyleSheet(f"QPushButton {{ background: {RED}; color: white; border-radius: 12px; font-size: 12px; font-weight: 700; padding: 10px 15px; }}")
        self.add_btn.clicked.connect(self._on_add_item)
        self.edit_btn.clicked.connect(self._on_edit_item)
        self.del_btn.clicked.connect(self._on_delete_item)
        self._menu_search = QLineEdit()
        self._menu_search.setPlaceholderText("Search menu items…")
        self._menu_search.setFixedHeight(38)
        self._menu_search.setStyleSheet(f"border: 1.5px solid {BORDER}; border-radius: 12px; padding: 0 14px; font-size: 13px; background: {SURFACE};")
        self._menu_search.textChanged.connect(self._filter_menu_table)
        toolbar.addWidget(self._menu_search)
        toolbar.addStretch()
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.edit_btn)
        toolbar.addWidget(self.del_btn)
        vl.addLayout(toolbar)

        # Table
        self.menu_table = self._make_table(["Item", "Category", "Price", "Status"])
        self.menu_table.itemDoubleClicked.connect(self._on_item_double_clicked)
        vl.addWidget(self.menu_table)
        self.tabs.addTab(tab, "🍽️  Menu Products")

    # ── Tab 2: Raw Supplies ─────────────────────────────────────
    def _build_supplies_tab(self):
        tab = QWidget()
        vl = QVBoxLayout(tab)
        vl.setContentsMargins(0, 15, 0, 0)
        vl.setSpacing(12)

        toolbar = QHBoxLayout()
        self.supply_cat_filter = QComboBox()
        self.supply_cat_filter.addItem("All Categories")
        self.supply_cat_filter.setFixedHeight(38)
        self.supply_cat_filter.setStyleSheet(f"border: 1.5px solid {BORDER}; border-radius: 12px; padding: 0 14px; font-size: 13px; background: {SURFACE};")
        self.supply_cat_filter.currentTextChanged.connect(lambda: self._load_supplies_data())

        self._supply_search = QLineEdit()
        self._supply_search.setPlaceholderText("Search supplies…")
        self._supply_search.setFixedHeight(38)
        self._supply_search.setStyleSheet(f"border: 1.5px solid {BORDER}; border-radius: 12px; padding: 0 14px; font-size: 13px; background: {SURFACE};")
        self._supply_search.textChanged.connect(self._filter_supply_table)

        self.supply_add_btn = QPushButton("➕ Add Supply")
        self.supply_add_btn.setStyleSheet(f"QPushButton {{ background: {ORANGE}; color: white; border-radius: 12px; font-size: 12px; font-weight: 700; padding: 10px 15px; }}")
        self.supply_edit_btn = QPushButton("✏️ Edit")
        self.supply_edit_btn.setStyleSheet(f"QPushButton {{ background: {BLUE}; color: white; border-radius: 12px; font-size: 12px; font-weight: 700; padding: 10px 15px; }}")
        self.supply_del_btn = QPushButton("🗑️ Delete")
        self.supply_del_btn.setStyleSheet(f"QPushButton {{ background: {RED}; color: white; border-radius: 12px; font-size: 12px; font-weight: 700; padding: 10px 15px; }}")
        self.supply_add_btn.clicked.connect(self._on_add_supply)
        self.supply_edit_btn.clicked.connect(self._on_edit_supply)
        self.supply_del_btn.clicked.connect(self._on_delete_supply)

        toolbar.addWidget(self.supply_cat_filter)
        toolbar.addWidget(self._supply_search)
        toolbar.addStretch()
        toolbar.addWidget(self.supply_add_btn)
        toolbar.addWidget(self.supply_edit_btn)
        toolbar.addWidget(self.supply_del_btn)
        vl.addLayout(toolbar)

        self.supply_table = self._make_table(["ID", "Name", "Category", "Unit", "Quantity", "Min Stock", "Status"])
        self.supply_table.setColumnHidden(0, True)  # Hide ID column
        vl.addWidget(self.supply_table)
        self.tabs.addTab(tab, "📦  Raw Supplies")

    # ── Shared Table Builder ────────────────────────────────────
    def _make_table(self, headers):
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.verticalHeader().setVisible(False)
        t.setShowGrid(False)
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setStyleSheet(f"""
            QTableWidget {{ border: none; background: {SURFACE}; border-radius: 16px; }}
            QHeaderView::section {{ background: {SURFACE}; color: {TEXT}; font-weight: 700; font-size: 11px; padding: 10px 14px; border: none; }}
            QTableWidget::item {{ padding: 12px 14px; border: none; background: transparent; }}
            QTableWidget::item:alternate {{ background: {BG}; }}
            QTableWidget::item:selected {{ background: {TEAL_LIGHT}; color: {TEXT}; }}
        """)
        return t

    def _make_summary_card(self, label, value, color):
        card = QFrame()
        card.setFixedHeight(90)
        card.setGraphicsEffect(get_shadow(10))
        card.setStyleSheet(f"background: {SURFACE}; border-radius: 18px; border: none;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 12, 18, 12)
        bar = QFrame()
        bar.setFixedHeight(3)
        bar.setStyleSheet(f"background: {color}; border-radius: 2px; border: none;")
        lbl = QLabel(label.upper())
        lbl.setStyleSheet(f"font-size: 9px; font-weight: 800; color: {MUTED}; letter-spacing: 1px;")
        val = QLabel(value)
        val.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {TEXT};")
        val.setObjectName("val")
        layout.addWidget(bar)
        layout.addWidget(lbl)
        layout.addWidget(val)
        return card

    # ── Role Permissions ────────────────────────────────────────
    def set_role(self, role):
        is_mgr = role == "Manager"
        for btn in [self.add_btn, self.edit_btn, self.del_btn,
                     self.supply_add_btn, self.supply_edit_btn, self.supply_del_btn]:
            btn.setVisible(is_mgr)

    # ── Menu Products CRUD ──────────────────────────────────────
    def _get_selected_menu_name(self):
        row = self.menu_table.currentRow()
        if row < 0: return None
        item = self.menu_table.item(row, 0)
        return item.text().split("  ")[-1].strip() if item else None

    def _on_add_item(self):
        dlg = ItemDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if data["name"]:
                self.dc.add_menu_item(data)
                self._load_menu_data()

    def _on_edit_item(self):
        name = self._get_selected_menu_name()
        if not name:
            QMessageBox.warning(self, "Selection Required", "Please select an item to edit.")
            return
        item_data = next((m for m in self.dc.get_menu() if m["name"] == name), None)
        if not item_data: return
        dlg = ItemDialog(self, item_data)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_data = dlg.get_data()
            new_data["soldout"] = item_data.get("soldout", False)
            new_data["sold"] = item_data.get("sold", 0)
            new_data["rating"] = item_data.get("rating", 5.0)
            if new_data["name"]:
                self.dc.edit_menu_item(name, new_data)
                self._load_menu_data()

    def _on_delete_item(self):
        name = self._get_selected_menu_name()
        if not name:
            QMessageBox.warning(self, "Selection Required", "Please select an item to delete.")
            return
        ans = QMessageBox.question(self, "Confirm Delete", f"Delete '{name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ans == QMessageBox.StandardButton.Yes:
            self.dc.delete_menu_item(name)
            self._load_menu_data()

    def _on_item_double_clicked(self, item):
        row = item.row()
        name_item = self.menu_table.item(row, 0)
        if not name_item: return
        name = name_item.text().split("  ")[-1].strip()
        for m in self.dc.get_menu():
            if m["name"] == name:
                self.dc.set_sold_out(name, not m.get("soldout", False))
                self._load_menu_data()
                break

    # ── Supply CRUD ─────────────────────────────────────────────
    def _get_selected_supply_id(self):
        row = self.supply_table.currentRow()
        if row < 0: return None
        item = self.supply_table.item(row, 0)
        return int(item.text()) if item else None

    def _on_add_supply(self):
        cats = self.dc.get_supply_categories()
        dlg = SupplyDialog(self, categories=cats)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if data["name"]:
                self.dc.add_supply(data)
                self._load_supplies_data()

    def _on_edit_supply(self):
        sid = self._get_selected_supply_id()
        if sid is None:
            QMessageBox.warning(self, "Selection Required", "Please select a supply to edit.")
            return
        row = self.supply_table.currentRow()
        data = {
            "name": self.supply_table.item(row, 1).text(),
            "category": self.supply_table.item(row, 2).text(),
            "unit": self.supply_table.item(row, 3).text(),
            "quantity": float(self.supply_table.item(row, 4).text()),
            "min_stock": float(self.supply_table.item(row, 5).text()),
        }
        cats = self.dc.get_supply_categories()
        dlg = SupplyDialog(self, data=data, categories=cats)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_data = dlg.get_data()
            if new_data["name"]:
                self.dc.update_supply(sid, new_data)
                self._load_supplies_data()

    def _on_delete_supply(self):
        sid = self._get_selected_supply_id()
        if sid is None:
            QMessageBox.warning(self, "Selection Required", "Please select a supply to delete.")
            return
        row = self.supply_table.currentRow()
        name = self.supply_table.item(row, 1).text()
        ans = QMessageBox.question(self, "Confirm Delete", f"Delete supply '{name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ans == QMessageBox.StandardButton.Yes:
            self.dc.delete_supply(sid)
            self._load_supplies_data()

    # ── Data Loading ────────────────────────────────────────────
    def _load_menu_data(self):
        menu = self.dc.get_menu()
        total = len(menu)
        soldout = sum(1 for i in menu if i.get("soldout"))
        avail = total - soldout
        for card, text in [(self._total_card, str(total)), (self._avail_card, str(avail)), (self._soldout_card, str(soldout))]:
            val_lbl = card.findChild(QLabel, "val")
            if val_lbl: val_lbl.setText(text)

        self.menu_table.setRowCount(len(menu))
        for row, item in enumerate(menu):
            is_out = item.get("soldout", False)
            self.menu_table.setItem(row, 0, QTableWidgetItem(f"{item['emoji']}  {item['name']}"))
            cat_col = QTableWidgetItem(item.get("category", "—"))
            cat_col.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.menu_table.setItem(row, 1, cat_col)
            price_col = QTableWidgetItem(f"₱{item['price']:.2f}")
            price_col.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.menu_table.setItem(row, 2, price_col)
            status_item = QTableWidgetItem("Sold Out" if is_out else "Available")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setForeground(QColor(RED if is_out else GREEN))
            self.menu_table.setItem(row, 3, status_item)

    def _load_supplies_data(self):
        cat_filter = self.supply_cat_filter.currentText()
        cat = None if cat_filter == "All Categories" else cat_filter
        supplies = self.dc.get_supplies(cat)

        # Update category filter dropdown (preserve selection)
        cats = self.dc.get_supply_categories()
        self.supply_cat_filter.blockSignals(True)
        self.supply_cat_filter.clear()
        self.supply_cat_filter.addItem("All Categories")
        self.supply_cat_filter.addItems(cats)
        if cat_filter in cats:
            self.supply_cat_filter.setCurrentText(cat_filter)
        self.supply_cat_filter.blockSignals(False)

        # Low stock count
        all_supplies = self.dc.get_supplies()
        low = sum(1 for s in all_supplies if float(s.get("quantity", 0)) <= float(s.get("min_stock", 5)))
        val_lbl = self._low_stock_card.findChild(QLabel, "val")
        if val_lbl: val_lbl.setText(str(low))

        self.supply_table.setRowCount(len(supplies))
        for row, s in enumerate(supplies):
            qty = float(s.get("quantity", 0))
            min_s = float(s.get("min_stock", 5))
            is_low = qty <= min_s

            id_col = QTableWidgetItem(str(s["id"]))
            self.supply_table.setItem(row, 0, id_col)
            self.supply_table.setItem(row, 1, QTableWidgetItem(str(s["name"])))
            cat_col = QTableWidgetItem(str(s["category"]))
            cat_col.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.supply_table.setItem(row, 2, cat_col)
            unit_col = QTableWidgetItem(str(s["unit"]))
            unit_col.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.supply_table.setItem(row, 3, unit_col)
            qty_col = QTableWidgetItem(f"{qty:g}")
            qty_col.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if is_low: qty_col.setForeground(QColor(RED))
            self.supply_table.setItem(row, 4, qty_col)
            min_col = QTableWidgetItem(f"{min_s:g}")
            min_col.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.supply_table.setItem(row, 5, min_col)
            status_col = QTableWidgetItem("⚠️ Low" if is_low else "✅ OK")
            status_col.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_col.setForeground(QColor(RED if is_low else GREEN))
            self.supply_table.setItem(row, 6, status_col)

    # ── Search Filters ──────────────────────────────────────────
    def _filter_menu_table(self, text):
        text = text.lower()
        for row in range(self.menu_table.rowCount()):
            n = self.menu_table.item(row, 0)
            c = self.menu_table.item(row, 1)
            match = (n and text in n.text().lower()) or (c and text in c.text().lower())
            self.menu_table.setRowHidden(row, not match)

    def _filter_supply_table(self, text):
        text = text.lower()
        for row in range(self.supply_table.rowCount()):
            n = self.supply_table.item(row, 1)
            c = self.supply_table.item(row, 2)
            match = (n and text in n.text().lower()) or (c and text in c.text().lower())
            self.supply_table.setRowHidden(row, not match)
