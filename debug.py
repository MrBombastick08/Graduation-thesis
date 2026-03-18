"""
python test_dice.py
Нажми кнопку "Светлая тема" и посмотри — кубик меняет фон?
"""
import sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt
from PyQt6.QtGui import *

app = QApplication(sys.argv)
app.setStyle("Fusion")

DARK_SURF = "#3a3a3a"
LIGHT_SURF = "#ffffff"

class DiceWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(160, 160)
        self._value = "7"
        self._color = QColor("#5b7fc7")
        self._bg1 = QColor("#484848")
        self._bg2 = QColor("#333333")
        self._surface = QColor(DARK_SURF)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    def set_theme(self, is_dark):
        if is_dark:
            self._surface = QColor(DARK_SURF)
            self._bg1 = QColor("#484848")
            self._bg2 = QColor("#333333")
        else:
            self._surface = QColor(LIGHT_SURF)
            self._bg1 = QColor("#f0f0f0")
            self._bg2 = QColor("#e0e0e0")
        self.update()
        print(f"surface set to: {self._surface.name()}", flush=True)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        print(f"paintEvent: surface={self._surface.name()}", flush=True)
        p.fillRect(self.rect(), self._surface)
        cx = cy = 80; h = 58; r = h * 0.28
        grad = QLinearGradient(cx-h, cy-h, cx+h, cy+h)
        grad.setColorAt(0, self._bg1); grad.setColorAt(1, self._bg2)
        p.setBrush(QBrush(grad)); p.setPen(QPen(self._color, 2.5))
        p.drawRoundedRect(cx-h, cy-h, h*2, h*2, r, r)
        p.setFont(QFont("Segoe UI", 44, QFont.Weight.Bold))
        p.setPen(self._color)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._value)
        p.end()

w = QWidget()
w.setStyleSheet("QWidget { background: #f0f0f0; } QPushButton { background: #5b7fc7; color: white; border-radius: 6px; padding: 8px 16px; }")
vl = QVBoxLayout(w)

dice = DiceWidget()
vl.addWidget(dice, alignment=Qt.AlignmentFlag.AlignCenter)

is_dark = [True]
btn = QPushButton("Переключить тему (сейчас: тёмная)")
def toggle():
    is_dark[0] = not is_dark[0]
    dice.set_theme(is_dark[0])
    lbl.setText(f"surface: {dice._surface.name()}")
    btn.setText(f"Переключить тему (сейчас: {'тёмная' if is_dark[0] else 'светлая'})")
    # Меняем фон окна тоже
    bg = "#2b2b2b" if is_dark[0] else "#f0f0f0"
    w.setStyleSheet(f"QWidget {{ background: {bg}; }} QPushButton {{ background: #5b7fc7; color: white; border-radius: 6px; padding: 8px 16px; }}")

btn.clicked.connect(toggle)
vl.addWidget(btn)

lbl = QLabel(f"surface: {dice._surface.name()}")
lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
vl.addWidget(lbl)

w.resize(400, 300)
w.show()
sys.exit(app.exec())