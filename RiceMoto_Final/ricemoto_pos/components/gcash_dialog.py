"""
GCash Payment Dialog for RiceMoto POS.
Displays auto-generated QR code with unique reference number for payment verification.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame, QGraphicsDropShadowEffect, QWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QColor
import random
import time

# ── Color constants ──
GCASH_BLUE = "#0052FE"
GCASH_BLUE_LIGHT = "#007BFF"
GCASH_BG = "#F8FAFC"
GCASH_BORDER = "#E2E8F0"
GCASH_MUTED = "#94A3B8"
GCASH_TEXT = "#1E293B"

# ── Reusable style snippets ──
_INPUT_BASE = f"""
    QLineEdit {{
        background: {GCASH_BG};
        border: 2px solid {GCASH_BORDER};
        border-radius: 12px;
        padding: 0 15px;
        font-size: 15px;
        font-weight: bold;
        color: {GCASH_TEXT};
        font-family: 'Consolas', 'Courier New', monospace;
        letter-spacing: 1px;
    }}
    QLineEdit:focus {{
        border: 2px solid {GCASH_BLUE};
        background: white;
    }}
"""
_INPUT_OK = """
    QLineEdit {
        background: #F0FDF4; border: 2px solid #22C55E; border-radius: 12px;
        padding: 0 15px; font-size: 15px; font-weight: bold; color: #16A34A;
        font-family: 'Consolas','Courier New',monospace; letter-spacing: 1px;
    }
"""
_INPUT_ERR = """
    QLineEdit {
        background: #FEF2F2; border: 2px solid #EF4444; border-radius: 12px;
        padding: 0 15px; font-size: 15px; font-weight: bold; color: #DC2626;
        font-family: 'Consolas','Courier New',monospace; letter-spacing: 1px;
    }
"""

class GCashDialog(QDialog):
    def __init__(self, amount_due, parent=None):
        super().__init__(parent)
        self.amount_due = amount_due
        self.reference_number = ""
        self._expected_ref = self._generate_unique_ref()

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frame)

        self._setup_ui()
        self._center()

    def _center(self):
        """Center the dialog perfectly on its parent window."""
        p = self.parentWidget()
        if p:
            win = p.window()
            rect = win.geometry()
            self.move(rect.center() - self.rect().center())
        else:
            from PyQt6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen().availableGeometry()
            self.move(screen.center() - self.rect().center())

    @staticmethod
    def _generate_unique_ref():
        ts = str(int(time.time() * 1000))[-7:]
        rand = "".join(str(random.randint(0, 9)) for _ in range(6))
        return ts + rand

    @staticmethod
    def _generate_qr_pixmap(data, size=190):
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            from io import BytesIO
            buf = BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            qi = QImage()
            qi.loadFromData(buf.read())
            return QPixmap.fromImage(qi).scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        except:
            px = QPixmap(size, size)
            px.fill(QColor("white"))
            return px

    def _setup_ui(self):
        # Root layout with padding to accommodate the shadow
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card = QFrame()
        self.card.setFixedWidth(420)
        self.card.setObjectName("GCashCard")
        self.card.setStyleSheet("QFrame#GCashCard{background:white;border-radius:24px;}")

        # Applying shadow to the card, which now has room in the root's margins
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        cl = QVBoxLayout(self.card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(88)
        header.setStyleSheet(f"QFrame {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {GCASH_BLUE}, stop:1 {GCASH_BLUE_LIGHT}); border-top-left-radius:24px; border-top-right-radius:24px; border:none; }}")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(25, 0, 25, 0)

        logo = QLabel("G")
        logo.setFixedSize(38, 38)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("background:white; color:#0052FE; border-radius:19px; font-size:20px; font-weight:900; border:none;")
        hl.addWidget(logo)
        hl.addSpacing(10)

        tv = QVBoxLayout()
        tv.setSpacing(1)
        n = QLabel("GCash")
        n.setStyleSheet("color:white; font-size:21px; font-weight:900; letter-spacing:1px; background:transparent; border:none;")
        s = QLabel("Payment Request")
        s.setStyleSheet("color:rgba(255,255,255,0.75); font-size:11px; font-weight:600; background:transparent; border:none;")
        tv.addWidget(n)
        tv.addWidget(s)
        hl.addLayout(tv)
        hl.addStretch()

        dot = QLabel("● Secure")
        dot.setStyleSheet("color:#50FF50; font-size:11px; font-weight:700; background:transparent; border:none;")
        hl.addWidget(dot)
        cl.addWidget(header)

        # Body
        body = QFrame()
        body.setStyleSheet("QFrame{background:white; border:none;}")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(30, 22, 30, 22)
        bl.setSpacing(0)

        # Amount
        al = QLabel("Amount to Pay", alignment=Qt.AlignmentFlag.AlignCenter)
        al.setStyleSheet("color:#6B7280; font-size:13px; font-weight:600; background:transparent; border:none;")
        bl.addWidget(al)
        bl.addSpacing(2)

        av = QLabel(self.amount_due, alignment=Qt.AlignmentFlag.AlignCenter)
        av.setStyleSheet(f"color:{GCASH_BLUE}; font-size:34px; font-weight:900; font-family:'Segoe UI',Arial; background:transparent; border:none;")
        bl.addWidget(av)
        bl.addSpacing(18)

        bl.addLayout(self._divider("Scan QR to Pay"))
        bl.addSpacing(16)

        # QR container
        qrc = QFrame()
        qrc.setObjectName("QRC")
        qrc.setStyleSheet(f"QFrame#QRC{{background:{GCASH_BG}; border:2px solid {GCASH_BORDER}; border-radius:16px;}}")
        ql = QVBoxLayout(qrc)
        ql.setContentsMargins(20, 18, 20, 14)
        ql.setSpacing(10)
        ql.setAlignment(Qt.AlignmentFlag.AlignCenter)

        qr_img = QLabel()
        qr_img.setPixmap(self._generate_qr_pixmap(self._expected_ref, 190))
        qr_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_img.setStyleSheet("background:transparent; border:none;")
        ql.addWidget(qr_img)

        rb = QFrame()
        rb.setObjectName("RB")
        rb.setStyleSheet("QFrame#RB{background:#EEF2FF; border:1.5px solid #C7D2FE; border-radius:10px;}")
        rbl = QVBoxLayout(rb)
        rbl.setContentsMargins(14, 6, 14, 6)
        rbl.setSpacing(1)
        rbl.addWidget(QLabel("Reference No.", alignment=Qt.AlignmentFlag.AlignCenter, styleSheet="color:#6366F1; font-size:10px; font-weight:700; letter-spacing:1px; background:transparent; border:none;"))
        rbl.addWidget(QLabel(self._expected_ref, alignment=Qt.AlignmentFlag.AlignCenter, styleSheet="color:#1E1B4B; font-size:17px; font-weight:900; font-family:'Consolas','Courier New',monospace; letter-spacing:2px; background:transparent; border:none;"))
        ql.addWidget(rb)
        bl.addWidget(qrc)
        bl.addSpacing(18)

        bl.addLayout(self._divider("Verify Payment"))
        bl.addSpacing(12)

        # Input row
        irow = QHBoxLayout()
        irow.setSpacing(10)
        self.ref_input = QLineEdit()
        self.ref_input.setPlaceholderText("Enter full ref or last 5 digits…")
        self.ref_input.setMaxLength(20)
        self.ref_input.setFixedHeight(46)
        self.ref_input.setStyleSheet(_INPUT_BASE)
        self.ref_input.textChanged.connect(self._validate_input)
        irow.addWidget(self.ref_input)

        self.scan_btn = QPushButton("📷 Scan")
        self.scan_btn.setFixedSize(88, 46)
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.setStyleSheet(f"QPushButton{{background:#F1F5F9; color:#475569; border:2px solid {GCASH_BORDER}; border-radius:12px; font-size:13px; font-weight:700;}} QPushButton:hover{{background:#E2E8F0;}}")
        self.scan_btn.clicked.connect(self._toggle_scanner)
        irow.addWidget(self.scan_btn)
        bl.addLayout(irow)

        self.val_msg = QLabel("", alignment=Qt.AlignmentFlag.AlignCenter)
        self.val_msg.setFixedHeight(20)
        bl.addWidget(self.val_msg)

        # Camera Container
        self.cam_container = QFrame()
        self.cam_container.setFixedHeight(0)
        cvl = QVBoxLayout(self.cam_container)
        cvl.setContentsMargins(0, 0, 0, 0)
        self.cam_label = QLabel()
        self.cam_label.setStyleSheet("background:#1E293B; border-radius:12px; border:none;")
        self.cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cvl.addWidget(self.cam_label)
        bl.addWidget(self.cam_container)

        bl.addSpacing(5)

        btns = QHBoxLayout()
        btns.setSpacing(12)
        cancel = QPushButton("Cancel")
        cancel.setFixedHeight(46)
        cancel.setStyleSheet(f"QPushButton{{background:{GCASH_BG}; color:#64748B; border:2px solid {GCASH_BORDER}; border-radius:14px; font-weight:700; font-size:14px;}} QPushButton:hover{{background:#F1F5F9;}}")
        cancel.clicked.connect(self.reject)
        
        self.confirm_btn = QPushButton("✓  Verify && Confirm")
        self.confirm_btn.setFixedHeight(46)
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.setStyleSheet(f"QPushButton{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {GCASH_BLUE}, stop:1 {GCASH_BLUE_LIGHT}); color:white; border:none; border-radius:14px; font-weight:800; font-size:14px;}} QPushButton:disabled{{background:#CBD5E1; color:#94A3B8;}}")
        self.confirm_btn.clicked.connect(self._on_confirm)
        btns.addWidget(cancel)
        btns.addWidget(self.confirm_btn)
        bl.addLayout(btns)

        cl.addWidget(body)
        root.addWidget(self.card)

    def _divider(self, text):
        row = QHBoxLayout()
        l = QFrame(); l.setFixedHeight(1); l.setStyleSheet("background:#E5E7EB; border:none;")
        r = QFrame(); r.setFixedHeight(1); r.setStyleSheet("background:#E5E7EB; border:none;")
        lbl = QLabel(f"  {text}  ")
        lbl.setStyleSheet("color:#9CA3AF; font-size:10px; font-weight:700; letter-spacing:1px; background:white; border:none;")
        row.addWidget(l); row.addWidget(lbl); row.addWidget(r)
        return row

    def _validate_input(self, text):
        text = text.strip()
        if not text:
            self.val_msg.setText("")
            self.confirm_btn.setEnabled(False)
            self.ref_input.setStyleSheet(_INPUT_BASE)
        elif text == self._expected_ref or (len(text) == 5 and text == self._expected_ref[-5:]):
            self.val_msg.setText("✓ Reference number verified!")
            self.val_msg.setStyleSheet("color:#16A34A; font-size:12px; font-weight:700; background:transparent; border:none;")
            self.confirm_btn.setEnabled(True)
            self.ref_input.setStyleSheet(_INPUT_OK)
        else:
            self.confirm_btn.setEnabled(False)
            if len(text) >= 5:
                self.val_msg.setText("✗ Invalid reference number")
                self.val_msg.setStyleSheet("color:#DC2626; font-size:12px; font-weight:700; background:transparent; border:none;")
                self.ref_input.setStyleSheet(_INPUT_ERR)
            else:
                self.val_msg.setText("")
                self.ref_input.setStyleSheet(_INPUT_BASE)

    def _on_confirm(self):
        self.reference_number = self._expected_ref
        self.accept()

    def _toggle_scanner(self):
        if self.cap is None:
            try:
                import cv2
                self.cap = cv2.VideoCapture(0)
                if not self.cap.isOpened(): raise Exception("Camera busy")
                self.cam_container.setFixedHeight(200)
                self.timer.start(30)
                self.scan_btn.setText("■ Stop")
                # When showing camera, adjust dialog size safely
                QTimer.singleShot(50, self.adjustSize)
                QTimer.singleShot(60, self._center)
            except Exception as e:
                self.val_msg.setText(f"Camera error: {str(e)}")
        else:
            self._stop_scanner()

    def _stop_scanner(self):
        self.timer.stop()
        if self.cap: self.cap.release(); self.cap = None
        self.cam_container.setFixedHeight(0)
        self.scan_btn.setText("📷 Scan")
        QTimer.singleShot(50, self.adjustSize)
        QTimer.singleShot(60, self._center)

    def _update_frame(self):
        if not self.cap: return
        import cv2
        ret, frame = self.cap.read()
        if not ret: return
        try:
            from pyzbar.pyzbar import decode
            for bc in decode(frame):
                self.ref_input.setText(bc.data.decode("utf-8"))
                self._stop_scanner()
                return
        except: pass
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qi = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self.cam_label.setPixmap(QPixmap.fromImage(qi).scaled(300, 200, Qt.AspectRatioMode.KeepAspectRatioByExpanding))

    def showEvent(self, event):
        super().showEvent(event)
        # Recalculate center after window is shown
        QTimer.singleShot(0, self._center)


    # ── Interactive Draggable Logic ──
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Capture initial click position relative to the window's top-left
            self._drag_start = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            # Update window position as mouse moves
            self.move(event.globalPosition().toPoint() - self._drag_start)
            event.accept()

    # ── Modern Hover Animation ──
    def enterEvent(self, event):
        # We avoid moving the card 'pos' in a layout as it causes 'ghosting' on translucent windows.
        # Instead, we can subtly update the shadow or just keep it static for stability.
        super().enterEvent(event)

    def leaveEvent(self, event):
        super().leaveEvent(event)

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        super().paintEvent(event)

    def reject(self): self._stop_scanner(); super().reject()
    def accept(self): self._stop_scanner(); super().accept()
    def closeEvent(self, e): self._stop_scanner(); super().closeEvent(e)
