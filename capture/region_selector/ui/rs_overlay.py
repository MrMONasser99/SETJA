from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QPen


class RegionSelector(QWidget):
    selected = Signal(dict)

    def __init__(self, min_size: int = 5):
        super().__init__()
        self.min_size = int(min_size)

        self.start = QPoint()
        self.selecting = False
        self.cut_rect = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.CrossCursor)

        self.hide()

    def show_selector(self):
        self.selecting = False
        self.cut_rect = None
        self.update()

        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        print("Selector shown (press ESC to cancel)")

    def cancel(self, reopen_hint: str = ""):
        self.selecting = False
        self.cut_rect = None
        self.update()
        self.hide()

        if reopen_hint:
            print(f"Selector hidden (app still running, press {reopen_hint} to re-open)")

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 80))

        if self.cut_rect:
            p.setCompositionMode(QPainter.CompositionMode_Clear)
            p.fillRect(self.cut_rect, Qt.transparent)

            p.setCompositionMode(QPainter.CompositionMode_SourceOver)
            p.setPen(QPen(QColor(255, 255, 255, 220), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRect(self.cut_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selecting = True
            self.start = event.position().toPoint()
            self.cut_rect = QRect(self.start, self.start)
            self.update()

    def mouseMoveEvent(self, event):
        if self.selecting:
            self.cut_rect = QRect(self.start, event.position().toPoint()).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.selecting:
            self.selecting = False
            rect = self.cut_rect

            if rect and rect.width() >= self.min_size and rect.height() >= self.min_size:
                self.selected.emit({
                    "x": rect.x(),
                    "y": rect.y(),
                    "width": rect.width(),
                    "height": rect.height(),
                })

            self.cancel()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.cancel()
