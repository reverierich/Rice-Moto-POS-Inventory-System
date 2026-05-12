"""
Analytics View (Dashboard) for RiceMoto POS.
Includes sales analytics, top items, and staff status.
Mapped to the Analytics (📊) sidebar icon.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QPushButton, QStyle
)
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont
import pyqtgraph as pg
from assets.ui.styles import (
    TEAL, TEAL_DARK, TEAL_PALE, TEAL_LIGHT, BORDER,
    BG, SURFACE, TEXT, MUTED, ACCENT, GREEN, BLUE, ORANGE, RED, get_shadow
)
from datetime import datetime, timedelta


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
        accent_bar.setStyleSheet(
            f"background: {color}; border-radius: 2px; border: none;"
        )

        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            f"font-size: 10px; font-weight: 800; color: {MUTED}; "
            f"letter-spacing: 1px; background: transparent; border: none;"
        )

        val = QLabel(value)
        val.setStyleSheet(
            f"font-size: 24px; font-weight: 800; color: {TEXT}; "
            f"background: transparent; border: none;"
        )
        self.value_label = val

        sub = QLabel(subtext)
        sub.setStyleSheet(
            f"font-size: 11px; color: {GREEN if '↑' in subtext else MUTED}; "
            f"font-weight: 600; background: transparent; border: none;"
        )
        self.sub_label = sub

        layout.addWidget(accent_bar)
        layout.addWidget(lbl)
        layout.addWidget(val)
        layout.addWidget(sub)


class DonutWidget(QWidget):
    """A custom-painted donut/pie chart widget."""
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data  # list of (label, value, color)
        self.setMinimumSize(160, 160)
        self.setMaximumSize(160, 160)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        total = sum(v for _, v, _ in self.data)
        if total == 0:
            return

        rect = self.rect().adjusted(10, 10, -10, -10)
        start_angle = 90 * 16  # Start from top

        for label, value, color in self.data:
            span = int((value / total) * 360 * 16)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(color)))
            painter.drawPie(rect, start_angle, -span)
            start_angle -= span

        # Draw center hole (donut effect)
        inner = rect.adjusted(30, 30, -30, -30)
        painter.setBrush(QBrush(QColor(SURFACE)))
        painter.drawEllipse(inner)

        # Draw total in center
        painter.setPen(QPen(QColor(TEXT)))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.drawText(inner, Qt.AlignmentFlag.AlignCenter, f"{total:.0f}\norders")


class AnalyticsView(QWidget):
    """Manager Dashboard with Analytics & Sales Reports."""
    def __init__(self, dc):
        super().__init__()
        self.dc = dc
        self.setStyleSheet(f"background: {BG};")
        self._current_range = "7d"
        self._tooltip_label = None
        self._today_line = None
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 25, 30, 25)
        main_layout.setSpacing(25)

        # Scroll wrapper
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(25)

        # ── Header ──────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("Sales Analytics & Reports")
        title.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {TEXT};")
        header.addWidget(title)
        v.addLayout(header)

        # ── Stats Row ────────────────────────────────────────────
        stats = self.dc.get_stats()
        stats_row = QHBoxLayout()
        stats_row.setSpacing(15)

        self.total_revenue_card = StatCard("Total Revenue", f"₱{stats['revenue']:,}", "Performance summary", TEAL)
        self.total_orders_card = StatCard("Total Orders", str(stats["orders"]), f"↑ {stats.get('orders_today', 8)} today", ACCENT)
        self.avg_order_card = StatCard("Avg Order", f"₱{stats['avg_order']}", "Steady", BLUE)
        self.active_staff_card = StatCard("Staff Active", str(stats["active_staff"]), "All shifts covered", GREEN)

        stats_row.addWidget(self.total_revenue_card)
        stats_row.addWidget(self.total_orders_card)
        stats_row.addWidget(self.avg_order_card)
        stats_row.addWidget(self.active_staff_card)
        v.addLayout(stats_row)

        # ── Sales Trend Chart ─────────────────────────────────────
        chart_card = QFrame()
        chart_card.setFixedHeight(340)
        chart_card.setGraphicsEffect(get_shadow(12))
        chart_card.setStyleSheet(
            f"background: {SURFACE}; border-radius: 24px; border: 1px solid rgba(16, 65, 73, 0.08);"
        )
        cv = QVBoxLayout(chart_card)
        cv.setContentsMargins(24, 20, 24, 20)
        cv.setSpacing(10)

        # Chart header row: title + filter buttons
        chart_header = QHBoxLayout()
        self.chart_title = QLabel("Sales Trend (This Week vs Last Week)")
        self.chart_title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {TEXT}; background: transparent; border: none;")
        chart_header.addWidget(self.chart_title)
        chart_header.addStretch()

        # Time range filter buttons
        self._range_buttons = {}
        for label, key in [("7 Days", "7d"), ("30 Days", "30d"), ("12 Months", "12m")]:
            btn = QPushButton(label)
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self._switch_range(k))
            self._range_buttons[key] = btn
            chart_header.addWidget(btn)

        cv.addLayout(chart_header)
        self._update_range_btn_styles()

        # Plot widget
        self.plot = pg.PlotWidget()
        self.plot.setBackground(SURFACE)
        self.plot.setStyleSheet("border: none; background: transparent;")

        plot_item = self.plot.getPlotItem()
        plot_item.showGrid(x=False, y=True, alpha=0.1)
        plot_item.getViewBox().setBorder(None)
        plot_item.setContentsMargins(10, 10, 10, 10)
        plot_item.setMenuEnabled(False)
        plot_item.hideButtons()
        self.plot.setMouseEnabled(x=False, y=False)

        # Tooltip label (floating)
        self._tooltip_label = QLabel(self.plot)
        self._tooltip_label.setStyleSheet(
            f"background: {TEAL_DARK}; color: white; padding: 5px 10px; "
            f"border-radius: 6px; font-size: 11px; font-weight: bold;"
        )
        self._tooltip_label.hide()

        # Connect hover events for tooltip
        self.plot.scene().sigMouseMoved.connect(self._on_mouse_moved)

        cv.addWidget(self.plot)
        v.addWidget(chart_card)

        # Draw the initial chart
        self._draw_chart()

        self.dc.order_status_changed.connect(lambda *_: self.refresh())
        self.dc.sold_out_changed.connect(lambda *_: self.refresh())
        self.dc.menu_filtered.connect(lambda _: self.refresh())

        # ── Bottom Row: Top Items + Payment Breakdown + Staff ─────────────────────────
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(25)

        # Top Selling Table
        table_card = QFrame()
        table_card.setGraphicsEffect(get_shadow(12))
        table_card.setStyleSheet(
            f"background: {SURFACE}; border-radius: 24px; border: 1px solid rgba(16, 65, 73, 0.08);"
        )
        tv = QVBoxLayout(table_card)
        tv.setContentsMargins(20, 20, 20, 20)
        tv.addWidget(QLabel("Top Selling Items"))

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ITEM", "PRICE", "SOLD"])
        self.table.horizontalHeaderItem(0).setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table.horizontalHeaderItem(1).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.horizontalHeaderItem(2).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setFrameShape(QFrame.Shape.NoFrame)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet(
            f"""
            QTableView, QTableWidget {{
                background: transparent;
                border: none;
                gridline-color: transparent;
            }}
            QHeaderView {{
                background: transparent;
                border: none;
            }}

            QTableView::item, QTableWidget::item {{
                padding: 10px 14px;
                border: none;
                background: transparent;
            }}
            QTableView::item:selected, QTableWidget::item:selected {{
                background: rgba(14, 165, 233, 0.14);
            }}
            QHeaderView::section {{
                background: transparent;
                color: {TEXT};
                border: none;
                padding: 12px 10px;
            }}
            QHeaderView::section:checked {{
                background: transparent;
            }}
            QTableCornerButton::section {{
                background: transparent;
                border: none;
            }}
            """
        )

        tv.addWidget(self.table)
        bottom_row.addWidget(table_card, stretch=2)

        # Recent Transactions (Audit)
        audit_card = QFrame()
        audit_card.setGraphicsEffect(get_shadow(12))
        audit_card.setStyleSheet(
            f"background: {SURFACE}; border-radius: 24px; border: none;"
        )
        av = QVBoxLayout(audit_card)
        av.setContentsMargins(20, 20, 20, 20)
        audit_title = QLabel("Recent Transactions")
        audit_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {TEXT}; background: transparent; border: none;")
        av.addWidget(audit_title)


        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background: transparent; border: none;")
        
        audit_container_widget = QWidget()
        audit_container_widget.setStyleSheet("background: transparent;")
        self.audit_container = QVBoxLayout(audit_container_widget)
        self.audit_container.setContentsMargins(0, 0, 0, 0)
        self.audit_container.setSpacing(10)
        
        scroll_area.setWidget(audit_container_widget)
        av.addWidget(scroll_area)
        bottom_row.addWidget(audit_card, stretch=2)

        # Payment Method Breakdown (Donut Chart)
        payment_card = QFrame()
        payment_card.setGraphicsEffect(get_shadow(12))
        payment_card.setStyleSheet(
            f"background: {SURFACE}; border-radius: 24px; border: none;"
        )
        pv = QVBoxLayout(payment_card)
        pv.setContentsMargins(20, 20, 20, 20)
        pay_title = QLabel("Payment Breakdown")
        pay_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {TEXT}; background: transparent; border: none;")
        pv.addWidget(pay_title)

        breakdown = self.dc.get_payment_breakdown()
        cash_count = breakdown.get("Cash", {}).get("count", 0)
        gcash_count = breakdown.get("GCash", {}).get("count", 0)
        cash_rev = breakdown.get("Cash", {}).get("revenue", 0)
        gcash_rev = breakdown.get("GCash", {}).get("revenue", 0)

        donut_data = [
            ("Cash", cash_count, "#22C55E"),
            ("GCash", gcash_count, "#0052FE"),
        ]
        self.donut = DonutWidget(donut_data)
        pv.addWidget(self.donut, alignment=Qt.AlignmentFlag.AlignCenter)

        # Legend rows
        for label, count, color, rev in [
            ("Cash", cash_count, "#22C55E", cash_rev),
            ("GCash", gcash_count, "#0052FE", gcash_rev)
        ]:
            legend_row = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 14px; background: transparent; border: none;")
            name_lbl = QLabel(f"{label}")
            name_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {TEXT}; background: transparent; border: none;")
            val_lbl = QLabel(f"{count} orders  •  ₱{rev:,.0f}")
            val_lbl.setStyleSheet(f"font-size: 10px; color: {MUTED}; background: transparent; border: none;")
            legend_row.addWidget(dot)
            legend_row.addWidget(name_lbl)
            legend_row.addStretch()
            legend_row.addWidget(val_lbl)
            pv.addLayout(legend_row)

        pv.addStretch()
        bottom_row.addWidget(payment_card, stretch=1)

        v.addLayout(bottom_row)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        self.refresh()

    # ── Chart Drawing ──────────────────────────────────────────
    def _draw_chart(self):
        """Draw (or redraw) the sales trend chart based on current range."""
        self.plot.clear()
        plot_item = self.plot.getPlotItem()

        # Remove old legend if any
        if plot_item.legend:
            plot_item.legend.scene().removeItem(plot_item.legend)
            plot_item.legend = None

        left_axis = plot_item.getAxis("left")
        left_axis.setPen(MUTED)
        left_axis.setTextPen(TEXT)
        bottom_axis = plot_item.getAxis("bottom")
        bottom_axis.setPen(MUTED)
        bottom_axis.setTextPen(TEXT)

        today_idx = None

        if self._current_range == "7d":
            self.chart_title.setText("Weekly Sales Trend")
            this_week, _ = self.dc.get_sales_data()
            self._chart_data = this_week
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

            # Highlight today
            today_idx = datetime.now().weekday()  # 0=Mon
            tick_list = []
            for i, d in enumerate(days):
                tick_list.append((i, d))
            ticks = [tick_list]
            bottom_axis.setTicks(ticks)

            # Add legend
            legend = plot_item.addLegend(offset=(20, 20))
            legend.setLabelTextColor(TEXT)
            legend.setBrush(QColor(SURFACE))

            max_val = max(this_week) if this_week and any(this_week) else 1000
            self.plot.setYRange(0, max_val * 1.35)
            self.plot.setXRange(-0.3, 6.3)

            # This week line (Primary Series)
            fill_color = QColor(TEAL)
            fill_color.setAlpha(40)
            
            # Use anti-aliasing for a smoother look
            self.plot.setAntialiasing(True)
            
            self.plot.plot(
                this_week,
                pen=pg.mkPen(color=QColor(TEAL), width=3, cosmetic=True),
                symbol="o", 
                symbolSize=10,
                symbolBrush=QColor(TEAL),
                symbolPen=pg.mkPen(color="white", width=2),
                fillLevel=0, 
                fillBrush=fill_color,
                name="This Week",
                antialias=True
            )

        elif self._current_range == "30d":
            self.chart_title.setText("Sales Trend (Last 30 Days)")
            data = self.dc.get_monthly_sales()
            self._chart_data = data
            
            # Show actual day labels for every 5 days
            now = datetime.now()
            tick_list = []
            for i in range(0, len(data), 5):
                day_date = now - timedelta(days=(len(data) - 1 - i))
                tick_list.append((i, day_date.strftime("%b %d")))
            ticks = [tick_list]
            bottom_axis.setTicks(ticks)

            max_val = max(data) if data else 50000
            self.plot.setYRange(0, max_val * 1.25)
            self.plot.setXRange(-0.5, len(data) - 0.5)

            fill_color = QColor(TEAL)
            fill_color.setAlpha(35)
            self.plot.plot(
                data,
                pen=pg.mkPen(TEAL, width=3),
                fillLevel=0, fillBrush=fill_color
            )
            today_idx = len(data) - 1

        elif self._current_range == "12m":
            self.chart_title.setText("Sales Trend (Last 12 Months)")
            data = self.dc.get_yearly_sales()
            self._chart_data = data
            
            # Calculate correct month labels
            now = datetime.now()
            curr_month = now.month # 1-12
            months_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            
            tick_list = []
            for i in range(len(data)):
                # Data is for the last 12 months, so index 11 is 'now'
                # index 0 is (curr_month - 11)
                m_idx = (curr_month - 11 + i - 1) % 12
                tick_list.append((i, months_names[m_idx]))
            
            ticks = [tick_list]
            bottom_axis.setTicks(ticks)

            max_val = max(data) if data else 1500000
            self.plot.setYRange(0, max_val * 1.25)
            self.plot.setXRange(-0.3, len(data) - 0.7)

            # Bar-style rendering for months
            bar_color = QColor(TEAL)
            bar_color.setAlpha(180)
            bargraph = pg.BarGraphItem(
                x=list(range(len(data))), height=data, width=0.5,
                brush=bar_color, pen=pg.mkPen(TEAL, width=1)
            )
            self.plot.addItem(bargraph)
            today_idx = 11 # Always the last bar

        # Draw "Today" vertical indicator line
        if today_idx is not None:
            today_line = pg.InfiniteLine(
                pos=today_idx, angle=90,
                pen=pg.mkPen(color=QColor(ACCENT), width=2, style=Qt.PenStyle.DotLine)
            )
            self.plot.addItem(today_line)

            # "Today" label at top
            today_text = pg.TextItem("Today", color=ACCENT, anchor=(0.5, 1))
            today_text.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            y_max = self.plot.viewRange()[1][1] if self.plot.viewRange() else 50000
            today_text.setPos(today_idx, max_val * 1.15 if 'max_val' in dir() else y_max)
            self.plot.addItem(today_text)

    def _switch_range(self, key):
        self._current_range = key
        self._update_range_btn_styles()
        self._draw_chart()

    def _update_range_btn_styles(self):
        for key, btn in self._range_buttons.items():
            if key == self._current_range:
                btn.setStyleSheet(
                    f"background: {TEAL}; color: white; border: none; border-radius: 6px; "
                    f"font-size: 11px; font-weight: bold; padding: 4px 12px;"
                )
            else:
                btn.setStyleSheet(
                    f"background: transparent; color: {MUTED}; border: 1px solid {BORDER}; border-radius: 6px; "
                    f"font-size: 11px; font-weight: bold; padding: 4px 12px;"
                )

    def _on_mouse_moved(self, pos):
        """Show tooltip when hovering over the chart."""
        if not hasattr(self, '_chart_data') or not self._chart_data:
            return

        mouse_point = self.plot.getPlotItem().vb.mapSceneToView(pos)
        x = int(round(mouse_point.x()))

        if 0 <= x < len(self._chart_data):
            value = self._chart_data[x]

            if self._current_range == "7d":
                days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                label_text = f"{days[x]}: ₱{value:,.0f}"
            elif self._current_range == "30d":
                label_text = f"Day {x+1}: ₱{value:,.0f}"
            else:
                months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                label_text = f"{months[x % 12]}: ₱{value:,.0f}"

            self._tooltip_label.setText(label_text)
            self._tooltip_label.adjustSize()

            # Position tooltip near mouse
            local_pos = self.plot.mapFromScene(pos)
            tip_x = max(0, min(local_pos.x() - self._tooltip_label.width() // 2,
                               self.plot.width() - self._tooltip_label.width()))
            tip_y = max(0, local_pos.y() - 35)
            self._tooltip_label.move(int(tip_x), int(tip_y))
            self._tooltip_label.show()
        else:
            self._tooltip_label.hide()

    def refresh(self):
        """Update analytics cards and top selling item table from the current database state."""
        stats = self.dc.get_stats()
        self.total_revenue_card.value_label.setText(f"₱{stats['revenue']:,}")
        self.total_orders_card.value_label.setText(str(stats["orders"]))
        self.avg_order_card.value_label.setText(f"₱{stats['avg_order']}")
        self.active_staff_card.value_label.setText(str(stats["active_staff"]))

        menu = sorted(self.dc.get_menu(), key=lambda x: x["sold"], reverse=True)[:5]
        self.table.setRowCount(len(menu))
        for row, item in enumerate(menu):
            name_item = QTableWidgetItem(f"{item['emoji']}  {item['name']}")
            
            price_item = QTableWidgetItem(f"₱{item['price']}")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            sold_item = QTableWidgetItem(str(item["sold"]))
            sold_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, price_item)
            self.table.setItem(row, 2, sold_item)
        
        self._update_audit_trail()
        self._draw_chart()

    def _update_audit_trail(self):
        """Fetch and display the latest activities in the audit log."""
        if not hasattr(self, 'audit_container'):
            return

        # Clear existing
        while self.audit_container.count():
            item = self.audit_container.takeAt(0)
            if item.layout():
                def clear_layout(layout):
                    while layout.count():
                        i = layout.takeAt(0)
                        if i.widget(): i.widget().deleteLater()
                        elif i.layout(): clear_layout(i.layout())
                clear_layout(item.layout())
            elif item.widget():
                item.widget().deleteLater()

        # Rebuild
        audit_data = self.dc.get_audit()
        if not audit_data:
            empty_lbl = QLabel("No recent activity found.")
            empty_lbl.setStyleSheet(f"color: {MUTED}; font-size: 12px; font-style: italic; padding: 20px;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.audit_container.addWidget(empty_lbl)
            return

        for audit in audit_data:
            row = QHBoxLayout()
            
            # Context-aware icons
            icon_char = "🛒" # Default for orders
            action_text = audit.get("action", "")
            if "Stock" in action_text: icon_char = "📝"
            elif "Login" in action_text: icon_char = "👤"
            elif "Void" in action_text or "Cancel" in action_text: icon_char = "⚠️"
            
            icon = QLabel(icon_char)
            icon.setStyleSheet(f"font-size: 16px; background: transparent; border: none;")
            
            info = QVBoxLayout()
            act_lbl = QLabel(f"{action_text} - {audit.get('time', 'Now')}")
            act_lbl.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {TEXT}; background: transparent; border: none;")
            det_lbl = QLabel(f"{audit.get('staff', 'System')}: {audit.get('detail', '')}")
            det_lbl.setStyleSheet(f"font-size: 10px; color: {MUTED}; background: transparent; border: none;")
            info.addWidget(act_lbl)
            info.addWidget(det_lbl)
            
            row.addWidget(icon)
            row.addLayout(info)
            row.addStretch()
            
            status_text = audit.get("status", "completed").title()
            status = QLabel(status_text)
            status_color = RED if status_text.lower() == "cancelled" else GREEN
            status.setStyleSheet(
                f"font-size: 9px; font-weight: 800; padding: 4px 10px; "
                f"border-radius: 999px; background: rgba(14, 165, 233, 0.08); color: {status_color}; border: 1px solid rgba(14, 165, 233, 0.16);"
            )
            row.addWidget(status)
            self.audit_container.addLayout(row)
            
        self.audit_container.addStretch()
