"""
Settings View for RiceMoto POS.
Contains app settings: Theme, Account, Language, Notifications, System Preferences.
Mapped to the Gear (⚙) sidebar icon.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QPushButton, QComboBox,
    QLineEdit, QCheckBox, QSlider, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
# Import the edit account dialog
from components.edit_account_dialog import EditAccountDialog
from PyQt6.QtCore import Qt
from assets.ui.styles import (
    TEXT, MUTED, BORDER, BG, SURFACE, TEAL, TEAL_DARK,
    TEAL_MID, TEAL_LIGHT, TEAL_PALE, ACCENT, get_shadow
)


class SettingsSection(QFrame):
    """A card-style settings section container."""
    def __init__(self, title, icon):
        super().__init__()
        self.setObjectName("SettingsSectionCard")
        self.setGraphicsEffect(get_shadow(10))
        self.setStyleSheet(
            f"#SettingsSectionCard {{ background: {SURFACE}; border-radius: 20px; border: 1.5px solid {BORDER}; }}"
        )
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 20, 24, 24)
        self._layout.setSpacing(16)

        # Section header
        hdr = QHBoxLayout()
        ico_lbl = QLabel(icon)
        ico_lbl.setStyleSheet("font-size: 20px;")
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"font-size: 15px; font-weight: 800; color: {TEXT};"
        )
        hdr.addWidget(ico_lbl)
        hdr.addWidget(title_lbl)
        hdr.addStretch()
        self._layout.addLayout(hdr)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {BORDER}; border: none;")
        self._layout.addWidget(sep)

    def add_row(self, label, widget, description=""):
        """Add a label + widget row to this section."""
        row = QHBoxLayout()
        left = QVBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {TEXT};")
        left.addWidget(lbl)
        if description:
            desc = QLabel(description)
            desc.setStyleSheet(f"font-size: 11px; color: {MUTED};")
            left.addWidget(desc)
        row.addLayout(left)
        row.addStretch()
        row.addWidget(widget)
        self._layout.addLayout(row)

    def add_widget(self, widget):
        self._layout.addWidget(widget)


def _styled_combo(options, fixed_width=200):
    cb = QComboBox()
    cb.addItems(options)
    cb.setFixedWidth(fixed_width)
    cb.setFixedHeight(38)
    cb.view().setAlternatingRowColors(True)
    return cb


def _toggle_btn(checked=False):
    """A simple toggle-style QPushButton."""
    btn = QPushButton("ON" if checked else "OFF")
    btn.setCheckable(True)
    btn.setChecked(checked)
    btn.setFixedSize(70, 32)

    def _update(state):
        btn.setText("ON" if state else "OFF")
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {TEAL if state else BORDER};
                color: {'white' if state else MUTED};
                border-radius: 16px;
                font-size: 11px; font-weight: 800;
                border: none;
            }}
        """)

    btn.toggled.connect(_update)
    _update(checked)
    return btn


class SettingsView(QWidget):
    """Full Settings page."""

    def __init__(self, dc):
        super().__init__()
        self.dc = dc
        self.current_theme = self._detect_current_theme()
        self.current_mode = self._detect_current_mode()
        self.setStyleSheet(f"background: {BG};")
        self._setup_ui()

    def _detect_current_theme(self):
        try:
            from assets.ui.styles import TEAL
            if TEAL == "#0284C7": return "Ocean Blue"
            elif TEAL == "#F43F5E": return "Coral"
            elif TEAL == "#6366F1": return "Midnight Dark"
            else: return "Teal (Default)"
        except:
            return "Teal (Default)"

    def _detect_current_mode(self):
        try:
            from assets.ui.styles import BG
            if BG == "#121212": return "Dark Mode"
            else: return "Light Mode"
        except:
            return "Light Mode"

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 25, 30, 25)
        main_layout.setSpacing(20)

        # Scroll wrapper
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(20)

        self.content_layout = v # Store for dynamic updates

        # ── Page header ───────────────────────────────────────────
        page_title = QLabel("Settings")
        page_title.setStyleSheet(
            f"font-size: 22px; font-weight: 800; color: {TEXT};"
        )
        v.addWidget(page_title)

        # ── Appearance & Theme ───────────────────────────────────
        theme_sec = SettingsSection("Appearance & Theme", "🎨")

        self.theme_combo = _styled_combo(["Teal (Default)", "Ocean Blue", "Coral", "Midnight Dark"])
        self.theme_combo.setCurrentText(self.current_theme)  # Display the current theme
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        theme_sec.add_row(
            "Color Theme",
            self.theme_combo,
            "Choose the primary accent color for the app"
        )

        self.mode_combo = _styled_combo(["Light Mode", "Dark Mode", "System Default"])
        self.mode_combo.setCurrentText(self.current_mode)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        theme_sec.add_row(
            "Interface Mode",
            self.mode_combo,
            "Switch between light and dark interface"
        )

        # Add Save Settings Button
        save_btn = QPushButton("💾 Save Settings")
        save_btn.setFixedHeight(46)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {TEAL_DARK}; color: white;
                border-radius: 14px; font-size: 14px; font-weight: 800;
                margin-top: 6px;
            }}
            QPushButton:hover {{ background: {TEAL}; }}
        """)
        save_btn.clicked.connect(self._on_save_settings)
        theme_sec.add_widget(save_btn)

        v.addWidget(theme_sec)

        # Container for dynamic account management section
        self.account_container = QVBoxLayout()
        self.account_container.setSpacing(20)
        v.addLayout(self.account_container)

        # ── System Error Logs ───────────────────────────────────
        logs_sec = SettingsSection("System Error Logs", "🚨")
        
        self.error_log_table = QTableWidget()
        self.error_log_table.setColumnCount(5)
        self.error_log_table.setHorizontalHeaderLabels(["Time", "Category", "User", "Action", "Message"])
        self.error_log_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.error_log_table.verticalHeader().setVisible(False)
        self.error_log_table.setShowGrid(False)
        self.error_log_table.setFrameShape(QFrame.Shape.NoFrame)
        self.error_log_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.error_log_table.setStyleSheet(
            f"""
            QTableView, QTableWidget {{
                background: transparent;
                border: none;
                gridline-color: transparent;
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
        self.error_log_table.setMinimumHeight(250)
        logs_sec.add_widget(self.error_log_table)
        
        v.addWidget(logs_sec)

        self._load_error_logs()
        v.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        
        # Initial refresh
        self._refresh_account_section()

    def showEvent(self, event):
        """Refresh the account section every time the settings page is shown."""
        super().showEvent(event)
        self._refresh_account_section()

    def _refresh_account_section(self):
        """Dynamically add or remove the Account section based on user role."""
        # Clear existing content in the account container
        while self.account_container.count():
            child = self.account_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Only show account management for manager
        if self.dc.current_user and self.dc.current_user.get('role', '').lower() == 'manager':
            account_sec = SettingsSection("Account", "👤")
            edit_btn = QPushButton("Edit Account")
            edit_btn.setFixedHeight(42)
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {TEAL_DARK}; color: white; border: none; border-radius: 8px; font-weight: 800;
                }}
                QPushButton:hover {{ background: {TEAL}; }}
            """)
            edit_btn.clicked.connect(self._open_edit_account)
            account_sec.add_widget(edit_btn)

            manage_status_btn = QPushButton("Manage Account Status")
            manage_status_btn.setFixedHeight(42)
            manage_status_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            manage_status_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {TEXT}; border: 1.5px solid {BORDER}; border-radius: 8px; font-weight: 800;
                }}
                QPushButton:hover {{ background: {BG}; }}
            """)
            manage_status_btn.clicked.connect(self._open_edit_account)
            account_sec.add_widget(manage_status_btn)
            self.account_container.addWidget(account_sec)

    def _open_edit_account(self):
        """Open the EditAccountDialog for manager users."""
        dlg = EditAccountDialog(self.dc, self)
        if dlg.exec():
            # after successful edit, reload user info if needed
            self.dc.refresh_current_user()
            # You may also want to refresh UI elsewhere
            self._show_styled_message("Info", "Account details updated.")

    def _on_theme_changed(self, text):
        try:
            import os, re
            styles_path = os.path.join(os.path.dirname(__file__), 'styles.py')

            with open(styles_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Apply Color Theme
            if text == "Ocean Blue":
                content = re.sub(r'TEAL = ".*?"', 'TEAL = "#0284C7"', content)
                content = re.sub(r'TEAL_DARK = ".*?"', 'TEAL_DARK = "#0369A1"', content)
                content = re.sub(r'TEAL_MID = ".*?"', 'TEAL_MID = "#0EA5E9"', content)
                content = re.sub(r'TEAL_LIGHT = ".*?"', 'TEAL_LIGHT = "#E0F2FE"', content)
                content = re.sub(r'TEAL_PALE = ".*?"', 'TEAL_PALE = "#F0F9FF"', content)
            elif text == "Coral":
                content = re.sub(r'TEAL = ".*?"', 'TEAL = "#F43F5E"', content)
                content = re.sub(r'TEAL_DARK = ".*?"', 'TEAL_DARK = "#BE123C"', content)
                content = re.sub(r'TEAL_MID = ".*?"', 'TEAL_MID = "#FB7185"', content)
                content = re.sub(r'TEAL_LIGHT = ".*?"', 'TEAL_LIGHT = "#FFE4E6"', content)
                content = re.sub(r'TEAL_PALE = ".*?"', 'TEAL_PALE = "#FFF1F2"', content)
            elif text == "Midnight Dark":
                content = re.sub(r'TEAL = ".*?"', 'TEAL = "#6366F1"', content)
                content = re.sub(r'TEAL_DARK = ".*?"', 'TEAL_DARK = "#4338CA"', content)
                content = re.sub(r'TEAL_MID = ".*?"', 'TEAL_MID = "#818CF8"', content)
                content = re.sub(r'TEAL_LIGHT = ".*?"', 'TEAL_LIGHT = "#E0E7FF"', content)
                content = re.sub(r'TEAL_PALE = ".*?"', 'TEAL_PALE = "#EEF2FF"', content)
            else: # Teal (Default)
                content = re.sub(r'TEAL = ".*?"', 'TEAL = "#007B6E"', content)
                content = re.sub(r'TEAL_DARK = ".*?"', 'TEAL_DARK = "#005A50"', content)
                content = re.sub(r'TEAL_MID = ".*?"', 'TEAL_MID = "#009688"', content)
                content = re.sub(r'TEAL_LIGHT = ".*?"', 'TEAL_LIGHT = "#E0F2EF"', content)
                content = re.sub(r'TEAL_PALE = ".*?"', 'TEAL_PALE = "#F0FAF8"', content)

            with open(styles_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.current_theme = text  # Update the current theme
            self._show_styled_message("Theme Applied", f"Color theme changed to {text}.")
        except Exception as e:
            self._show_styled_message("Error", f"Failed to apply theme: {str(e)}", QMessageBox.Icon.Warning)

    def _on_mode_changed(self, text):
        try:
            import os, re
            styles_path = os.path.join(os.path.dirname(__file__), 'styles.py')
            with open(styles_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if text == "Dark Mode":
                content = re.sub(r'BG = ".*?"', 'BG = "#121212"', content)
                content = re.sub(r'SURFACE = ".*?"', 'SURFACE = "#1E1E1E"', content)
                content = re.sub(r'TEXT = ".*?"', 'TEXT = "#E0E0E0"', content)
                content = re.sub(r'MUTED = ".*?"', 'MUTED = "#8A8A8A"', content)
                content = re.sub(r'BORDER = ".*?"', 'BORDER = "#333333"', content)
                content = re.sub(r'WHITE = ".*?"', 'WHITE = "#2D2D2D"', content)
            else:
                content = re.sub(r'BG = ".*?"', 'BG = "#F4F7F6"', content)
                content = re.sub(r'SURFACE = ".*?"', 'SURFACE = "#FFFFFF"', content)
                content = re.sub(r'TEXT = ".*?"', 'TEXT = "#1A2E2C"', content)
                content = re.sub(r'MUTED = ".*?"', 'MUTED = "#6B8682"', content)
                content = re.sub(r'BORDER = ".*?"', 'BORDER = "#D0E8E4"', content)
                content = re.sub(r'WHITE = ".*?"', 'WHITE = "#FFFFFF"', content)

            with open(styles_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.current_mode = text
            self._show_styled_message("Mode Applied", f"Interface mode changed to {text}.")
        except Exception as e:
            self._show_styled_message("Error", f"Failed to apply mode: {str(e)}", QMessageBox.Icon.Warning)

    def _on_save_settings(self):
        try:
            import sys
            import os
            from PyQt6.QtWidgets import QApplication

            main_window = None
            for widget in QApplication.topLevelWidgets():
                if widget.__class__.__name__ == "MainApp":
                    main_window = widget
                    break
            
            user_name = "Admin User (Manager)"
            role = "Manager"
            if main_window and hasattr(main_window, 'dc') and main_window.dc.current_user:
                u = main_window.dc.current_user
                user_name = f"{u.get('first_name', '')} {u.get('last_name', '')} ({str(u.get('role', 'Staff')).title()})".strip()
                role = str(u.get('role', 'Staff')).title()

            self._show_styled_message("Settings Saved", "Settings have been saved. The application will now restart to apply changes.")

            args = sys.argv[:]
            # Clean up existing flags
            args = [a for a in args if not a.startswith("--apply-theme") and not a.startswith("--user=") and not a.startswith("--role=")]
            
            args.append("--apply-theme")
            args.append(f"--user={user_name}")
            args.append(f"--role={role}")
            
            os.execl(sys.executable, sys.executable, *args)
        except Exception as e:
            self._show_styled_message("Error", f"Failed to save settings: {str(e)}", QMessageBox.Icon.Warning)
 
    def _show_styled_message(self, title, text, icon=QMessageBox.Icon.Information):
        """Show a QMessageBox that properly inherits the global theme."""
        from assets.ui.styles import GLOBAL_QSS, BG
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(icon)
        # Force the global style onto the dialog
        msg.setStyleSheet(GLOBAL_QSS + f"\nQMessageBox {{ background-color: {BG}; }}")
        msg.exec()

    def _load_error_logs(self):
        """Fetch and display recent error logs from the database."""
        error_logs = self.dc.get_error_logs(limit=10)
        self.error_log_table.setRowCount(len(error_logs))
        for row, log in enumerate(error_logs):
            self.error_log_table.setItem(row, 0, QTableWidgetItem(log["created_at"]))
            self.error_log_table.setItem(row, 1, QTableWidgetItem(log.get("category", "")))
            self.error_log_table.setItem(row, 2, QTableWidgetItem(log.get("user", "")))
            self.error_log_table.setItem(row, 3, QTableWidgetItem(log.get("action", "")))
            self.error_log_table.setItem(row, 4, QTableWidgetItem(log.get("message", "")))
