"""
Login and Registration views for RiceMoto POS.
Includes form validation and modern aesthetics.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QRadioButton, QButtonGroup,
    QScrollArea, QSpinBox, QDateEdit, QComboBox, QMessageBox,
    QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QCursor
from assets.ui.styles import (
    TEAL, TEAL_DARK, TEAL_PALE, BORDER, BG,
    SURFACE, TEXT, MUTED, RED, get_shadow
)

INPUT_QSS = f"""
    QLineEdit {{
        background: {SURFACE};
        border: 1.5px solid {BORDER};
        border-radius: 10px;
        padding: 8px 14px;
        font-size: 13px;
        color: {TEXT};
        selection-background-color: {TEAL};
    }}
    QLineEdit:focus {{
        border-color: {TEAL};
        background: {BG};
    }}
    QLineEdit:hover {{
        border-color: {TEAL};
    }}
"""


class LoginView(QWidget):
    """Modern Login facade with role selection."""
    login_requested = pyqtSignal(str, str)
    register_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background: {BG};")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        # Main Card
        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        card.setGraphicsEffect(get_shadow(32, TEAL, 40))
        card.setStyleSheet(f"""
            QFrame {{
                background: {SURFACE};
                border-radius: 24px;
                border: 1.5px solid {BORDER};
            }}
        """)

        row = QHBoxLayout(card)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        # Left Panel (Branding)
        left = QFrame()
        left.setFixedWidth(560)
        left.setStyleSheet(f"""
            QFrame {{
                background: #000000;
                border-radius: 22px 0 0 22px;
                border: none;
            }}
        """)
        lv = QVBoxLayout(left)
        lv.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lv.setSpacing(15)

        import os
        from PyQt6.QtGui import QPixmap
        
        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        logo_path = os.path.join(os.path.dirname(__file__), '..', 'logo.png')
        svg_path = os.path.join(os.path.dirname(__file__), '..', 'logo.svg')
        
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            logo.setPixmap(pixmap.scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            logo.setStyleSheet("background: transparent; border: none;")
        elif os.path.exists(svg_path):
            pixmap = QPixmap(svg_path)
            logo.setPixmap(pixmap.scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            logo.setStyleSheet("background: transparent; border: none;")
        else:
            logo.setText("🍽")
            logo.setStyleSheet("font-size: 56px; background: transparent; border: none;")
        brand = QLabel("RiceMoto")
        brand.setStyleSheet("font-size: 28px; font-weight: 800; color: white; background: transparent; border: none;")
        sub = QLabel("Professional POS System")
        sub.setStyleSheet("font-size: 13px; color: rgba(255,255,255,0.7); background: transparent; border: none;")

        lv.addWidget(logo)
        lv.addWidget(brand)
        lv.addWidget(sub)

        # Right Panel (Form)
        right = QWidget()
        right.setStyleSheet("background: transparent;")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(30, 20, 30, 20)
        rv.setSpacing(18)
        rv.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        content = QWidget()
        content.setMaximumWidth(720)
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        content.setStyleSheet("background: transparent;")
        cv = QVBoxLayout(content)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(18)
        cv.setAlignment(Qt.AlignmentFlag.AlignTop)

        rv.addStretch()
        welcome = QLabel("Welcome Back! ✨")
        welcome.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {TEXT}; background: transparent; border: none;")
        welcome_sub = QLabel("Sign in to continue")
        welcome_sub.setStyleSheet(f"font-size: 13px; color: {MUTED}; background: transparent; border: none;")

        # Username input
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username")
        self.user_input.setFixedHeight(45)
        self.user_input.setStyleSheet(INPUT_QSS)
        # Press Enter → move to password
        self.user_input.returnPressed.connect(self._focus_password)

        # Password row: input + show/hide button
        pass_row = QFrame()
        pass_row.setStyleSheet(f"""
            QFrame {{
                background: {SURFACE};
                border: 1.5px solid {BORDER};
                border-radius: 10px;
            }}
            QFrame:focus-within {{
                border-color: {TEAL};
                background: {BG};
            }}
        """)
        pass_row.setFixedHeight(45)
        pass_h = QHBoxLayout(pass_row)
        pass_h.setContentsMargins(0, 0, 6, 0)
        pass_h.setSpacing(0)

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                border: none;
                border-radius: 10px;
                padding: 8px 14px;
                font-size: 13px;
                color: {TEXT};
            }}
        """)
        self.pass_input.returnPressed.connect(self._do_login)

        self.show_pass_btn = QPushButton("👁")
        self.show_pass_btn.setFixedSize(34, 34)
        self.show_pass_btn.setCheckable(True)
        self.show_pass_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.show_pass_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                color: {MUTED};
                padding: 0;
            }}
            QPushButton:hover {{
                background: {BORDER};
                color: {TEAL};
            }}
            QPushButton:checked {{
                color: {TEAL};
            }}
        """)
        self.show_pass_btn.toggled.connect(self._toggle_password_visibility)

        pass_h.addWidget(self.pass_input)
        pass_h.addWidget(self.show_pass_btn)

        self.login_btn = QPushButton("Sign In")
        self.login_btn.setFixedHeight(50)
        self.login_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.login_btn.setStyleSheet(f"""
            QPushButton {{
                background: {TEAL_DARK}; color: white;
                border-radius: 12px; font-size: 15px; font-weight: 700;
                border: none;
            }}
            QPushButton:hover {{ background: {TEAL}; }}
            QPushButton:pressed {{ background: #004A42; }}
        """)
        self.login_btn.clicked.connect(self._do_login)

        reg_row = QHBoxLayout()
        reg_lbl = QLabel("New here?")
        reg_lbl.setStyleSheet(f"font-size: 12px; color: {MUTED}; background: transparent; border: none;")
        reg_btn = QPushButton("Create Account")
        reg_btn.setFlat(True)
        reg_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        reg_btn.setStyleSheet(f"color: {TEAL}; font-weight: 700; font-size: 12px; border: none; background: transparent;")
        reg_btn.clicked.connect(self.register_clicked.emit)
        reg_row.addWidget(reg_lbl)
        reg_row.addWidget(reg_btn)
        reg_row.addStretch()

        cv.addWidget(welcome)
        cv.addWidget(welcome_sub)
        cv.addSpacing(10)
        cv.addWidget(self.user_input)
        cv.addWidget(pass_row)
        cv.addWidget(self.login_btn)
        cv.addLayout(reg_row)
        cv.addStretch()

        rv.addWidget(content)
        rv.addStretch()

        row.addWidget(left)
        row.addWidget(right)
        row.setStretch(0, 0)
        row.setStretch(1, 1)
        layout.addWidget(card, 1)

    def _focus_password(self):
        """Move focus to password field when Enter pressed on username."""
        self.pass_input.setFocus()

    def _toggle_password_visibility(self, checked):
        """Toggle password echo mode with clean, professional symbols."""
        if checked:
            self.pass_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_pass_btn.setText("⦵") # Clean slashed circle for 'Hide'
        else:
            self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_pass_btn.setText("👁")

    def _do_login(self):
        self.login_requested.emit(
            self.user_input.text(), self.pass_input.text()
        )


class RegisterView(QWidget):
    """Complete Registration view with validation."""
    register_requested = pyqtSignal(dict)
    back_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background: {BG};")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        card.setGraphicsEffect(get_shadow(24))
        card.setStyleSheet(f"background: {SURFACE}; border-radius: 24px; border: 1.5px solid {BORDER};")

        v = QVBoxLayout(card)
        v.setContentsMargins(40, 40, 40, 40)
        v.setSpacing(14)

        title = QLabel("Create Account")
        title.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {TEXT}; background: transparent; border: none;")
        v.addWidget(title)

        # Scroll area for the form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        form = QWidget()
        form.setStyleSheet("background: transparent;")
        fv = QVBoxLayout(form)
        fv.setSpacing(12)

        field_input_qss = INPUT_QSS + """
            QLineEdit { height: 40px; }
        """

        def add_field(label, placeholder, is_pass=False):
            l = QLabel(label)
            l.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {TEXT}; background: transparent; border: none;")
            i = QLineEdit()
            i.setPlaceholderText(placeholder)
            i.setFixedHeight(40)
            i.setStyleSheet(INPUT_QSS)
            if is_pass:
                i.setEchoMode(QLineEdit.EchoMode.Password)
            fv.addWidget(l)
            fv.addWidget(i)
            return i

        self.email = add_field("Email", "email@gmail.com")
        self.user = add_field("Username", "Choose a username")
        self.password = add_field("Password", "At least 6 characters", True)

        name_row = QHBoxLayout()
        self.first = QLineEdit()
        self.first.setPlaceholderText("First Name")
        self.first.setFixedHeight(40)
        self.first.setStyleSheet(INPUT_QSS)
        self.last = QLineEdit()
        self.last.setPlaceholderText("Last Name")
        self.last.setFixedHeight(40)
        self.last.setStyleSheet(INPUT_QSS)
        name_row.addWidget(self.first)
        name_row.addWidget(self.last)
        name_lbl = QLabel("Full Name")
        name_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {TEXT}; background: transparent; border: none;")
        fv.addWidget(name_lbl)
        fv.addLayout(name_row)

        # Advanced Fields
        age_lbl = QLabel("Age")
        age_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {TEXT}; background: transparent; border: none;")
        self.age = QSpinBox()
        self.age.setRange(16, 99)
        self.age.setFixedHeight(40)
        fv.addWidget(age_lbl)
        fv.addWidget(self.age)

        gender_lbl = QLabel("Gender")
        gender_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {TEXT}; background: transparent; border: none;")
        self.gender = QComboBox()
        self.gender.addItems(["Male", "Female", "Prefer not to say"])
        self.gender.setFixedHeight(40)
        fv.addWidget(gender_lbl)
        fv.addWidget(self.gender)

        scroll.setWidget(form)
        v.addWidget(scroll)

        btn = QPushButton("Create Account")
        btn.setFixedHeight(50)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {TEAL_DARK}; color: white;
                border-radius: 12px; font-size: 15px; font-weight: 700;
                border: none;
            }}
            QPushButton:hover {{ background: {TEAL}; }}
            QPushButton:pressed {{ background: #004A42; }}
        """)
        btn.clicked.connect(self._validate_and_submit)
        v.addWidget(btn)

        back = QPushButton("← Back to Login")
        back.setFlat(True)
        back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        back.setStyleSheet(f"color: {MUTED}; font-size: 12px; border: none; background: transparent;")
        back.clicked.connect(self.back_clicked.emit)
        v.addWidget(back)

        layout.addWidget(card, 1)

    def _validate_and_submit(self):
        data = {
            "email": self.email.text().strip(),
            "username": self.user.text().strip(),
            "password": self.password.text().strip(),
            "first_name": self.first.text().strip(),
            "last_name": self.last.text().strip(),
            "age": self.age.value(),
            "gender": self.gender.currentText()
        }

        if not all([data["email"], data["username"], data["password"], data["first_name"]]):
            QMessageBox.warning(self, "Validation Error", "Please fill in all required fields.")
            return

        if len(data["password"]) < 6:
            QMessageBox.warning(self, "Validation Error", "Password must be at least 6 characters.")
            return

        self.register_requested.emit(data)
