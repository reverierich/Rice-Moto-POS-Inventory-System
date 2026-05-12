from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt
from assets.ui.styles import (
    TEXT, MUTED, BORDER, BG, SURFACE, TEAL, TEAL_DARK, get_shadow
)
import hashlib

class EditAccountDialog(QDialog):
    """Dialog to edit account information.
    Managers can edit all accounts; Staff can only edit their own.
    """
    def __init__(self, data_controller, parent=None):
        super().__init__(parent)
        self.dc = data_controller
        self.current_logged_in = self.dc.current_user
        self.is_manager = self.current_logged_in.get("role", "").lower() == "manager"
        
        self.users_list = []
        if self.is_manager:
            self.users_list = self.dc.get_all_users()
        else:
            self.users_list = [self.current_logged_in]

        self.setWindowTitle("Edit Account")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._setup_ui()
        self._populate_user_selector()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        card = QFrame()
        card.setFixedWidth(550)
        card.setStyleSheet(f"""
            QFrame {{
                background: {SURFACE};
                border-radius: 20px;
                border: 1px solid {BORDER};
            }}
        """)
        card.setGraphicsEffect(get_shadow(10))
        layout = QVBoxLayout(card)
        layout.setContentsMargins(25, 20, 25, 25)
        layout.setSpacing(15)

        # Header
        header = QLabel("👤 Edit Account Information")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(f"color: {TEXT}; font-size: 18px; font-weight: 800; border: none;")
        layout.addWidget(header)

        # User Selector (Only for Manager)
        self.user_select_lbl = QLabel("Select Account to Edit")
        self.user_select_lbl.setStyleSheet(f"color: {MUTED}; font-size: 11px; font-weight: 700; border: none;")
        self.user_combo = QComboBox()
        self.user_combo.setStyleSheet(self._input_style())
        self.user_combo.currentIndexChanged.connect(self._on_user_selected)
        
        if not self.is_manager:
            self.user_select_lbl.hide()
            self.user_combo.hide()
        
        layout.addWidget(self.user_select_lbl)
        layout.addWidget(self.user_combo)

        # Username
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setStyleSheet(self._input_style())
        layout.addWidget(QLabel("Username (Login ID)"))
        layout.addWidget(self.username_input)

        # Display Name
        self.display_input = QLineEdit()
        self.display_input.setPlaceholderText("Display Name")
        self.display_input.setStyleSheet(self._input_style())
        layout.addWidget(QLabel("Full Name / Display Name"))
        layout.addWidget(self.display_input)

        # Role
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Manager", "Staff"])
        self.role_combo.setStyleSheet(self._input_style())
        layout.addWidget(QLabel("Account Role"))
        layout.addWidget(self.role_combo)
        
        if not self.is_manager:
            self.role_combo.setEnabled(False)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #0F766E; font-size: 12px; font-weight: 700; border: none;")
        layout.addWidget(self.status_label)

        # New Password
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("Enter new password")
        self.pass_input.setStyleSheet(self._input_style())
        layout.addWidget(QLabel("Change Password (optional)"))
        layout.addWidget(self.pass_input)

        # Confirm Password
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setPlaceholderText("Confirm new password")
        self.confirm_input.setStyleSheet(self._input_style())
        layout.addWidget(self.confirm_input)
        
        self.pass_err = QLabel("")
        self.pass_err.setStyleSheet("color: #DC2626; font-size: 11px; font-weight: 600; border: none;")
        self.pass_err.setFixedHeight(15)
        layout.addWidget(self.pass_err)

        # Buttons
        btns = QHBoxLayout()
        btns.setSpacing(12)
        
        cancel = QPushButton("Cancel")
        cancel.setFixedHeight(40)
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        cancel.setStyleSheet(self._button_style())
        
        self.deactivate_btn = QPushButton("Deactivate Account")
        self.deactivate_btn.setFixedHeight(40)
        self.deactivate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.deactivate_btn.clicked.connect(self._deactivate_account)
        self.deactivate_btn.setStyleSheet(self._danger_button_style())

        self.reactivate_btn = QPushButton("Reactivate Account")
        self.reactivate_btn.setFixedHeight(40)
        self.reactivate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reactivate_btn.clicked.connect(self._reactivate_account)
        self.reactivate_btn.setStyleSheet(self._success_button_style())
        self.reactivate_btn.hide()

        save = QPushButton("Save Changes")
        save.setFixedHeight(40)
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self._save)
        save.setStyleSheet(self._save_button_style())
        
        btns.addWidget(cancel)
        btns.addWidget(self.deactivate_btn)
        btns.addWidget(self.reactivate_btn)
        btns.addWidget(save)
        layout.addLayout(btns)

        root.addWidget(card)

    def _input_style(self):
        return f"""
            QLineEdit, QComboBox {{
                background: {BG};
                border: 1.5px solid {BORDER};
                border-radius: 8px;
                padding: 8px 12px;
                color: {TEXT};
                font-size: 13px;
                font-weight: 600;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 2px solid {TEAL};
                background: {SURFACE};
            }}
        """

    def _button_style(self):
        return f"""
            QPushButton {{
                background: transparent;
                color: {TEXT};
                border: 1.5px solid {BORDER};
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {BG}; }}
        """

    def _save_button_style(self):
        return f"""
            QPushButton {{
                background: {TEAL_DARK};
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {TEAL}; }}
        """

    def _danger_button_style(self):
        return f"""
            QPushButton {{
                background: #DC2626;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: #B91C1C; }}
        """

    def _success_button_style(self):
        return f"""
            QPushButton {{
                background: {TEAL};
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {TEAL_DARK}; }}
        """

    def _populate_user_selector(self):
        self.user_combo.clear()
        for u in self.users_list:
            self.user_combo.addItem(f"{u.get('display_name')} ({u.get('username')})", u)
        
        # Default to current user if found in list
        for i in range(self.user_combo.count()):
            u_data = self.user_combo.itemData(i)
            if u_data.get("id") == self.current_logged_in.get("id"):
                self.user_combo.setCurrentIndex(i)
                break

    def _on_user_selected(self, index):
        user = self.user_combo.itemData(index)
        if not user: return
        
        self.username_input.setText(user.get("username", ""))
        self.display_input.setText(user.get("display_name", ""))
        
        role = user.get("role", "staff").title()
        role_idx = self.role_combo.findText(role)
        if role_idx != -1:
            self.role_combo.setCurrentIndex(role_idx)
            
        self.pass_input.clear()
        self.confirm_input.clear()
        self.pass_err.setText("")

        is_active = bool(user.get("is_active", 1))
        self.status_label.setText(f"Account Status: {'Active' if is_active else 'Inactive'}")
        self.status_label.setStyleSheet(
            f"color: {TEAL if is_active else '#DC2626'}; font-size: 12px; font-weight: 700; border: none;"
        )
        
        if is_active:
            self.deactivate_btn.show()
            self.reactivate_btn.hide()
        else:
            self.deactivate_btn.hide()
            self.reactivate_btn.show()

    def _deactivate_account(self):
        user = self.user_combo.currentData()
        if not user:
            return

        if user.get("id") == self.current_logged_in.get("id"):
            QMessageBox.warning(self, "Action Not Allowed", "You cannot deactivate your own account while signed in.")
            return

        confirm = QMessageBox.question(
            self,
            "Deactivate Account",
            f"Are you sure you want to deactivate the account '{user.get('username')}'? This will keep their transaction history intact.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        success = self.dc.set_user_active_state(user.get("id"), False)
        if success:
            user["is_active"] = False
            self._on_user_selected(self.user_combo.currentIndex())
            QMessageBox.information(self, "Success", f"Account '{user.get('username')}' has been deactivated.")
        else:
            QMessageBox.warning(self, "Error", "Failed to deactivate the account.")

    def _reactivate_account(self):
        user = self.user_combo.currentData()
        if not user:
            return

        confirm = QMessageBox.question(
            self,
            "Reactivate Account",
            f"Are you sure you want to reactivate the account '{user.get('username')}'? This account will be able to sign in again.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        success = self.dc.set_user_active_state(user.get("id"), True)
        if success:
            user["is_active"] = True
            self._on_user_selected(self.user_combo.currentIndex())
            QMessageBox.information(self, "Success", f"Account '{user.get('username')}' has been reactivated.")
        else:
            QMessageBox.warning(self, "Error", "Failed to reactivate the account.")

    def _save(self):
        user = self.user_combo.currentData()
        if not user: return
        
        new_username = self.username_input.text().strip()
        display = self.display_input.text().strip()
        role = self.role_combo.currentText().lower()
        pwd = self.pass_input.text()
        confirm = self.confirm_input.text()
        
        if not new_username or not display:
            QMessageBox.warning(self, "Validation Error", "Username and Display Name cannot be empty.")
            return

        pwd_hash = None
        if pwd or confirm:
            if pwd != confirm:
                self.pass_err.setText("Passwords do not match.")
                return
            if len(pwd) < 4:
                self.pass_err.setText("Password too short (min 4 characters).")
                return
            pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()

        try:
            success = self.dc.update_user(user.get("id"), display, role, pwd_hash, new_username)
            if success:
                QMessageBox.information(self, "Success", f"Account for '{new_username}' updated successfully.")
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "Failed to update account. The username might already be taken.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"An unexpected error occurred: {e}")

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QColor
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 0))
        super().paintEvent(event)
