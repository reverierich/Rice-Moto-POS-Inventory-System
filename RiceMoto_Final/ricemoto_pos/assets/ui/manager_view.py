"""
Manager View (Dashboard) for RiceMoto POS.
Includes sales analytics, top items, and staff status.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QScrollArea, QFrame, QGridLayout, QTableWidget, 
    QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import pyqtgraph as pg
from assets.ui.styles import (
    TEAL, TEAL_DARK, TEAL_PALE, TEAL_LIGHT, BORDER,
    BG, SURFACE, TEXT, MUTED, ACCENT, GREEN, BLUE, ORANGE, RED, get_shadow
)

class StatCard(QFrame):
    """Modern Statistic Card."""
    def __init__(self, label, value, subtext, color=TEAL):
        super().__init__()
        self.setFixedHeight(120)
        self.setGraphicsEffect(get_shadow(12))
        self.setStyleSheet(f"""
            QFrame {{
                background: {SURFACE};
                border-radius: 20px;
                border: 1.5px solid {BORDER};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        
        accent_bar = QFrame()
        accent_bar.setFixedHeight(3)
        accent_bar.setStyleSheet(f"background: {color}; border-radius: 2px; border: none;")
        
        lbl = QLabel(label.upper())
        lbl.setStyleSheet(f"font-size: 10px; font-weight: 800; color: {MUTED}; letter-spacing: 1px; background: transparent; border: none;")
        
        val = QLabel(value)
        val.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {TEXT}; background: transparent; border: none;")
        
        sub = QLabel(subtext)
        sub.setStyleSheet(f"font-size: 11px; color: {GREEN if '↑' in subtext else MUTED}; font-weight: 600; background: transparent; border: none;")
        
        layout.addWidget(accent_bar)
        layout.addWidget(lbl)
        layout.addWidget(val)
        layout.addWidget(sub)


class ManagerView(QWidget):
    """Manager Dashboard with Analytics."""
    def __init__(self, dc):
        super().__init__()
        self.dc = dc
        self.setStyleSheet(f"background: {BG};")
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 25, 30, 25)
        main_layout.setSpacing(25)
        
        # Scroll Area for the whole dashboard
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(25)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Sales Analytics & Reports")
        title.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {TEXT};")
        header.addWidget(title)
        v.addLayout(header)
        
        # 1. Stats Row
        stats = self.dc.get_stats()
        stats_row = QHBoxLayout()
        stats_row.setSpacing(15)
        
        stats_row.addWidget(StatCard("Total Revenue", f"₱{stats['revenue']:,}", "↑ 12% vs last week", TEAL))
        stats_row.addWidget(StatCard("Total Orders", str(stats["orders"]), "↑ 8 today", ACCENT))
        stats_row.addWidget(StatCard("Avg Order", f"₱{stats['avg_order']}", "Steady", BLUE))
        stats_row.addWidget(StatCard("Staff Active", str(stats["active_staff"]), "All shifts covered", GREEN))
        
        v.addLayout(stats_row)
        
        # 2. Sales Trend Chart
        chart_card = QFrame()
        chart_card.setFixedHeight(300)
        chart_card.setGraphicsEffect(get_shadow(12))
        chart_card.setStyleSheet(f"background: {SURFACE}; border-radius: 24px; border: 1.5px solid {BORDER};")
        cv = QVBoxLayout(chart_card)
        cv.setContentsMargins(20, 20, 20, 20)
        
        cv.addWidget(QLabel("Sales Trend (This Week vs Last Week)"))
        
        # PyQtGraph Integration — use white bg to avoid transparent crash
        self.plot = pg.PlotWidget()
        self.plot.setBackground('w')  # white, matches SURFACE
        self.plot.getPlotItem().hideAxis('left')
        self.plot.getPlotItem().hideAxis('bottom')
        self.plot.getPlotItem().getViewBox().setBorder(None)
        self.plot.setStyleSheet("border: none; background: transparent;")
        
        this_week, last_week = self.dc.get_sales_data()
        
        # Plot last week (dashed/muted)
        self.plot.plot(last_week, pen=pg.mkPen(MUTED, width=1.5, style=Qt.PenStyle.DashLine))
        # Plot this week (bold teal)
        self.plot.plot(this_week, pen=pg.mkPen(TEAL, width=3), symbol='o', symbolSize=6, symbolBrush=TEAL)
        
        cv.addWidget(self.plot)
        v.addWidget(chart_card)
        
        # 3. Bottom Grid: Top Selling Items and Staff
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(25)
        
        # Top Selling Table
        table_card = QFrame()
        table_card.setGraphicsEffect(get_shadow(12))
        table_card.setStyleSheet(f"background: {SURFACE}; border-radius: 24px; border: 1.5px solid {BORDER};")
        tv = QVBoxLayout(table_card)
        tv.setContentsMargins(20, 20, 20, 20)
        tv.addWidget(QLabel("Top Selling Items"))
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Item", "Price", "Sold"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet(f"QTableWidget {{ border: none; }} QHeaderView::section {{ background: {TEAL_PALE}; color: {TEXT}; }}")
        
        menu = sorted(self.dc.get_menu(), key=lambda x: x["sold"], reverse=True)[:5]
        self.table.setRowCount(len(menu))
        for row, item in enumerate(menu):
            self.table.setItem(row, 0, QTableWidgetItem(f"{item['emoji']}  {item['name']}"))
            self.table.setItem(row, 1, QTableWidgetItem(f"₱{item['price']}"))
            self.table.setItem(row, 2, QTableWidgetItem(str(item['sold'])))
            
        tv.addWidget(self.table)
        bottom_row.addWidget(table_card, stretch=2)
        
        # Staff Quick View
        staff_card = QFrame()
        staff_card.setGraphicsEffect(get_shadow(12))
        staff_card.setStyleSheet(f"background: {SURFACE}; border-radius: 24px; border: 1.5px solid {BORDER};")
        sv = QVBoxLayout(staff_card)
        sv.setContentsMargins(20, 20, 20, 20)
        sv.addWidget(QLabel("Staff Status"))
        
        staff_list = QVBoxLayout()
        for staff in self.dc.get_staff():
            row = QHBoxLayout()
            avatar = QLabel(staff["initials"])
            avatar.setFixedSize(35, 35)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setStyleSheet(f"background: {staff['color']}; color: white; border-radius: 17px; font-weight: bold; font-size: 10px;")
            
            info = QVBoxLayout()
            name = QLabel(staff["name"])
            name.setStyleSheet("font-size: 12px; font-weight: 700;")
            role = QLabel(staff["role"])
            role.setStyleSheet(f"font-size: 10px; color: {MUTED};")
            info.addWidget(name)
            info.addWidget(role)
            
            row.addWidget(avatar)
            row.addLayout(info)
            row.addStretch()
            
            status = QLabel(staff["status"])
            status.setStyleSheet(f"font-size: 9px; font-weight: 800; padding: 2px 8px; border-radius: 10px; background: {TEAL_PALE}; color: {TEAL};")
            row.addWidget(status)
            
            staff_list.addLayout(row)
            
        sv.addLayout(staff_list)
        sv.addStretch()
        bottom_row.addWidget(staff_card, stretch=1)
        
        v.addLayout(bottom_row)
        
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def refresh(self):
        """Called when view is shown to update data."""
        # Update tables/charts if needed
        pass
