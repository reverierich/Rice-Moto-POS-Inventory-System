"""
TopBar component for RiceMoto POS.
Handles global search (UI), user profile, and notifications.
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QDateTime
from assets.ui.styles import SURFACE, TEXT, MUTED, BORDER, BG, TEAL_PALE, TEAL, TEAL_DARK, get_shadow

class TopBar(QWidget):
    """Modern TopBar with live clock and profile info."""

    def __init__(self, user_name="Admin"):
        super().__init__()
        self.setFixedHeight(80)
        self.setStyleSheet(f"background: {SURFACE}; border-bottom: 1.5px solid {BORDER};")
        self._setup_ui(user_name)

    def _setup_ui(self, user_name):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(30, 0, 30, 0)
        layout.setSpacing(20)

        # Page Title
        title_col = QWidget()
        title_col.setStyleSheet("background: transparent;")
        tc = QHBoxLayout(title_col)
        tc.setContentsMargins(0, 0, 0, 0)
        tc.setSpacing(10)

        self.breadcrumb = QLabel("RiceMoto POS")
        self.breadcrumb.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {MUTED};")

        sep = QLabel("›")
        sep.setStyleSheet(f"font-size: 13px; color: {MUTED};")

        self.page_title_lbl = QLabel("Menu & Ordering")
        self.page_title_lbl.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {TEXT};")

        tc.addWidget(self.breadcrumb)
        tc.addWidget(sep)
        tc.addWidget(self.page_title_lbl)
        tc.addStretch()
        layout.addWidget(title_col, stretch=1)

        # Live Clock (Replacing Search Bar)
        self.clock_lbl = QLabel()
        self.clock_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clock_lbl.setStyleSheet(f"""
            font-size: 14px; 
            font-weight: 700; 
            color: {MUTED};
            background: {BG};
            border-radius: 20px;
            border: 1.5px solid {BORDER};
            padding: 8px 20px;
        """)
        layout.addWidget(self.clock_lbl)
        layout.addStretch()

        # Start timer for clock
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_clock)
        self.timer.start(1000)
        self._update_clock()

        # Notification & Profile info
        info_row = QHBoxLayout()
        info_row.setSpacing(15)
        
        notify_btn = QPushButton("🔔")
        notify_btn.setFixedSize(40, 40)
        notify_btn.setStyleSheet(f"""
            QPushButton {{
                background: {BG};
                border-radius: 20px;
                border: none;
                font-size: 16px;
            }}
            QPushButton:hover {{ background: {BORDER}; }}
        """)
        
        profile = QWidget()
        ph = QHBoxLayout(profile)
        ph.setContentsMargins(0, 0, 0, 0)
        ph.setSpacing(10)
        
        self.name_lbl = QLabel(user_name)
        self.name_lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {TEXT};")
        
        self.avatar_lbl = QLabel(user_name[0] if user_name else "U")
        self.avatar_lbl.setFixedSize(40, 40)
        self.avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_lbl.setStyleSheet(f"""
            background: {TEAL};
            color: white;
            border-radius: 20px;
            font-weight: 800;
        """)
        
        ph.addWidget(self.name_lbl)
        ph.addWidget(self.avatar_lbl)
        
        info_row.addWidget(notify_btn)
        info_row.addWidget(profile)
        layout.addLayout(info_row)

    def set_page_title(self, title: str):
        """Update the displayed page/section title."""
        self.page_title_lbl.setText(title)

    def set_user(self, name: str):
        """Update displayed user name and avatar letter."""
        self.name_lbl.setText(name)
        self.avatar_lbl.setText(name[0].upper() if name else "U")

    def _update_clock(self):
        current_time = QDateTime.currentDateTime().toString("hh:mm A  |  MMM dd, yyyy")
        self.clock_lbl.setText(f"🕒 {current_time}")
