import os
import sys
import ctypes
import numpy as np
from PIL import ImageGrab
import keyboard
from pathlib import Path
import tempfile

# Add the project root to the path to allow imports from other directories
grandparent_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(grandparent_dir))

from PySide6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen

# --- Windows-specific API setup for acrylic/blur effect ---
if sys.platform == 'win32':
    from ctypes import wintypes
    dwmapi = ctypes.WinDLL('dwmapi')
    user32 = ctypes.WinDLL('user32')

    # Constants for window attributes
    DWMWA_SYSTEMBACKDROP_TYPE = 38
    DWM_SYSTEMBACKDROP_TYPE_ACRYLIC = 2 # 2 for Acrylic, 3 for Mica
    DWMWA_WINDOW_CORNER_PREFERENCE = 33
    DWMWCP_ROUND = 2 # Enum for corner preference

    WDA_EXCLUDEFROMCAPTURE = 0x00000011 # Exclude window from capture

    # Structures for composition attribute
    class ACCENTPOLICY(ctypes.Structure):
        _fields_ = [
            ('AccentState', ctypes.c_uint),
            ('AccentFlags', ctypes.c_uint),
            ('GradientColor', ctypes.c_uint),
            ('AnimationId', ctypes.c_uint)
        ]

    class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
        _fields_ = [
            ('Attribute', ctypes.c_int),
            ('Data', ctypes.POINTER(ctypes.c_byte)),
            ('SizeOfData', ctypes.c_size_t)
        ]

    # Function pointers
    SetWindowCompositionAttribute = user32.SetWindowCompositionAttribute
    SetWindowCompositionAttribute.argtypes = [wintypes.HWND, ctypes.POINTER(WINDOWCOMPOSITIONATTRIBDATA)]
    SetWindowCompositionAttribute.restype = wintypes.BOOL

    SetWindowDisplayAffinity = user32.SetWindowDisplayAffinity
    SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
    SetWindowDisplayAffinity.restype = wintypes.BOOL


class InstantOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # --- State Initialization ---
        self.last_text = ""
        self.last_mtime = 0
        self.current_text_color = "#FFD75A" # Default color

        # --- Dragging and Interaction ---
        self.dragging = False
        self.offset = QPoint()
        self.draggable = False # Start in click-through mode
        self.is_hidden = False

        # --- Setup ---
        self._setup_window()
        self._create_widgets()
        self._apply_acrylic_effect()

        # --- Timers ---
        self.file_update_timer = QTimer(self)
        self.file_update_timer.timeout.connect(self.check_for_text_update)
        self.file_update_timer.start(100)

        self._hide_timer = QTimer(self)
        self._hide_timer.timeout.connect(self._hide_window)
        self._hide_timer.setSingleShot(True)

        self._color_update_timer = QTimer(self)
        self._color_update_timer.timeout.connect(self._update_text_color)
        self._color_update_timer.start(250)

        # --- Keyboard Hook ---
        keyboard.on_press_key("-", lambda _: self.toggle_draggable())

        # --- Positioning ---
        self.base_position = QPoint(960, 800)
        self.move(self.base_position)
        self.set_click_through(True)


    def toggle_draggable(self):
        self.draggable = not self.draggable
        self.set_click_through(not self.draggable)
        print(f"Draggable mode: {'On' if self.draggable else 'Off (Click-through)'}")
        if self.draggable:
            self.activateWindow()
            self.raise_()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setMinimumSize(1, 1)

        if sys.platform == 'win32':
            hwnd = self.winId()
            SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)

    def _apply_acrylic_effect(self):
        if sys.platform == 'win32':
            hwnd = self.winId()
            
            corner_preference = ctypes.c_int(DWMWCP_ROUND)
            dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, 
                ctypes.byref(corner_preference), ctypes.sizeof(corner_preference)
            )

            accent = ACCENTPOLICY()
            accent.AccentState = 3  # ACCENT_ENABLE_BLURBEHIND
            accent.AccentFlags = 0
            accent.GradientColor = 0
            accent.AnimationId = 0

            data = WINDOWCOMPOSITIONATTRIBDATA()
            data.Attribute = 19  # WCA_ACCENT_POLICY
            data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.POINTER(ctypes.c_byte))
            data.SizeOfData = ctypes.sizeof(accent)

            SetWindowCompositionAttribute(hwnd, ctypes.byref(data))

    def _create_widgets(self):
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setMargin(10)

        font = QFont("Arial", 24, QFont.Bold)
        self.label.setFont(font)

        self.label.setStyleSheet(f"""
            QLabel {{
                color: {self.current_text_color};
                background-color: transparent;
                padding: 5px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.addWidget(self.label)
        self.setLayout(layout)

    def _get_background_luminance(self):
        try:
            rect = self.geometry()
            capture_rect = (rect.x() + 5, rect.y() + 5, rect.right() - 5, rect.bottom() - 5)
            
            if capture_rect[2] <= capture_rect[0] or capture_rect[3] <= capture_rect[1]:
                return 128

            screenshot = ImageGrab.grab(bbox=capture_rect, all_screens=True)
            img = np.array(screenshot)
            
            img_sample = img[::5, ::5]
            if img_sample.size == 0:
                return 128

            avg_color = np.mean(img_sample, axis=(0, 1))
            luminance = 0.2126 * avg_color[0] + 0.7152 * avg_color[1] + 0.0722 * avg_color[2]
            return luminance
        except Exception:
            return 128

    def _update_text_color(self):
        if not self.isVisible():
            return

        luminance = self._get_background_luminance()
        
        if luminance > 120:
            new_color = "#A9831A" # Darker gold
            shadow_color = "#FFFFFF"
        else:
            new_color = "#FFD75A" # Brighter gold
            shadow_color = "#000000"

        if new_color != self.current_text_color:
            self.current_text_color = new_color
            
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(8)
            shadow.setColor(QColor(shadow_color))
            shadow.setOffset(1.5, 1.5)
            self.label.setGraphicsEffect(shadow)

            self.label.setStyleSheet(f"""
                QLabel {{
                    color: {self.current_text_color};
                    background-color: transparent;
                    padding: 5px;
                }}
            """)

    def _hide_window(self):
        if not self.is_hidden:
            self.hide()

    def update_text(self, text):
        if self.is_hidden or not text or text.isspace():
            if not self.isHidden():
                self._hide_timer.start(100)
            return

        self.label.setText(text)

        font_metrics = self.label.fontMetrics()
        lines = text.split('\n')
        if not lines or (len(lines) == 1 and not lines[0]):
             max_width = 0
        else:
            max_width = max(font_metrics.horizontalAdvance(line) for line in lines)
        
        line_count = len(lines)
        new_height = font_metrics.height() * line_count + self.label.margin() * 2 + 30

        new_width = max_width + self.label.margin() * 2 + 30
        
        new_x = self.base_position.x() - new_width // 2
        new_y = self.base_position.y() - new_height // 2

        self.setGeometry(new_x, new_y, new_width, new_height)

        if not self.isVisible():
            self.show()

        self._update_text_color()
        self._hide_timer.start(7000)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 12, 12)
        painter.setClipPath(path)
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.drawPath(path)

    def set_click_through(self, enable):
        if sys.platform == 'win32':
            hwnd = self.winId()
            current_style = user32.GetWindowLongW(hwnd, -20)
            if enable:
                new_style = current_style | 0x20 | 0x80000
            else:
                new_style = current_style & ~0x20
            user32.SetWindowLongW(hwnd, -20, new_style)

    def mousePressEvent(self, event):
        if self.draggable and event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.LeftButton:
            new_pos = event.globalPosition().toPoint() - self.offset
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if self.draggable and event.button() == Qt.LeftButton:
            self.dragging = False
            new_center_x = self.pos().x() + self.width() // 2
            new_center_y = self.pos().y() + self.height() // 2
            self.base_position = QPoint(new_center_x, new_center_y)
            print(f"New base position saved: {self.base_position}")
            event.accept()

    def check_for_text_update(self):
        try:
            ar_out_path = os.path.join(tempfile.gettempdir(), "setja_ar.txt")
            if not os.path.exists(ar_out_path):
                return

            mtime = os.path.getmtime(ar_out_path)
            if mtime == self.last_mtime:
                return
            self.last_mtime = mtime

            with open(ar_out_path, "r", encoding="utf-8") as f:
                new_text = f.read().strip()

            if new_text != self.last_text:
                self.last_text = new_text
                self.update_text(new_text)

        except Exception as e:
            print(f"Error reading translation file: {e}")


def main():
    app = QApplication(sys.argv)

    if sys.platform == 'win32':
        ctypes.windll.shcore.SetProcessDpiAwareness(1)

    overlay = InstantOverlay()
    overlay.update_text("...")
    
    QTimer.singleShot(2000, lambda: overlay.update_text("") if overlay.last_text == "..." else None)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
