import json, os, random, sys, math, io

import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QTabWidget,
    QFileDialog, QMessageBox, QScrollArea, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QGridLayout, QSizePolicy, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, QDate, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QPixmap, QLinearGradient, QFont, QPalette

DATA_FILE  = "app_internal_data.json"
IMAGES_DIR = "images"
MAX_REWARD = 200

if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

DARK = {
    "bg":       "#2b2b2b", "surface":  "#3a3a3a", "surface2": "#424242",
    "border":   "#545454", "accent":   "#5b7fc7", "positive": "#4caf7d",
    "negative": "#c75b5b", "text":     "#e8e8e8", "text_dim": "#999999",
    "row_alt":  "#333333", "select":   "#3d4f6e",
    "dice_bg1": "#484848", "dice_bg2": "#333333",
}
LIGHT = {
    "bg":       "#f0f0f0", "surface":  "#ffffff", "surface2": "#ebebeb",
    "border":   "#cccccc", "accent":   "#4a6abf", "positive": "#3a9e6a",
    "negative": "#c03030", "text":     "#1a1a1a", "text_dim": "#666666",
    "row_alt":  "#f7f7f7", "select":   "#c5d3ee",
    "dice_bg1": "#f5f5f5", "dice_bg2": "#e8e8e8",
}
PIE_COLORS = [
    "#5b7fc7","#e08040","#4caf7d","#9b59b6","#e74c3c",
    "#1abc9c","#f39c12","#2980b9","#8e44ad","#27ae60",
    "#c0392b","#16a085"
]
CATS_EXP = ["Продукты","Транспорт","Жилье","Здоровье","Развлечения","Досуг","Перевод","Наличка","Прочее"]
CATS_INC = ["Зарплата","Перевод","Наличка"]


class DiceWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(160, 160)
        self._value = "?"; self._color = QColor("#5b7fc7")
        self._scale = 1.0; self._bg1 = QColor("#484848"); self._bg2 = QColor("#333333")
        self._shadow_color = QColor(0, 0, 0, 50)
        self._surface = QColor("#3a3a3a")
        # WA_OpaquePaintEvent — Qt не затирает фон перед paintEvent
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    def update_theme(self, t):
        self._bg1 = QColor(t["dice_bg1"])
        self._bg2 = QColor(t["dice_bg2"])
        self._shadow_color = QColor(0,0,0,40) if t.get("bg","#2") < "#8" else QColor(150,150,150,50)
        self._surface = QColor(t["surface"])
        self.update()

    def set_face(self, value, color, scale=1.0):
        self._value = str(value); self._color = QColor(color); self._scale = scale
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Рисуем фон явно из сохранённого цвета темы
        bg = getattr(self, "_surface", QColor("#3a3a3a"))
        p.fillRect(self.rect(), bg)
        cx = cy = 80; h = int(58 * self._scale); r = h * 0.28
        # Тень — цвет зависит от темы
        shadow = getattr(self, "_shadow_color", QColor(0,0,0,50))
        p.setBrush(QBrush(shadow)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(cx-h+7, cy-h+7, h*2, h*2, r, r)
        grad = QLinearGradient(cx-h, cy-h, cx+h, cy+h)
        grad.setColorAt(0, self._bg1); grad.setColorAt(1, self._bg2)
        p.setBrush(QBrush(grad)); p.setPen(QPen(self._color, 2.5))
        p.drawRoundedRect(cx-h, cy-h, h*2, h*2, r, r)
        p.setFont(QFont("Segoe UI", max(10, int(44*self._scale)), QFont.Weight.Bold))
        p.setPen(self._color)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._value)
        p.end()


class ExclTag(QFrame):
    removed = pyqtSignal(int)
    def __init__(self, n, theme):
        super().__init__(); self.n = n
        self.setObjectName("excl_tag")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 5, 0); lay.setSpacing(4)
        self.setFixedHeight(28)

        lbl = QLabel(str(n))
        lbl.setStyleSheet(
            f"color:{theme['text']};font-size:13px;"
            f"font-weight:600;background:transparent;border:none;"
        )

        btn = QPushButton("×")
        btn.setFixedSize(16, 16)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;"
            f"color:{theme['text_dim']};font-size:16px;padding:0;margin:0;}}"
            f"QPushButton:hover{{color:{theme['negative']};}}"
        )
        btn.clicked.connect(lambda: self.removed.emit(self.n))

        lay.addWidget(lbl); lay.addWidget(btn)
        self.setStyleSheet(
            f"QFrame#excl_tag{{background:{theme['surface2']};border-radius:14px;"
            f"border:1px solid {theme['border']};}}"
            f"QFrame#excl_tag:hover{{border-color:{theme['accent']};}}"
        )


class PieWidget(QWidget):
    def __init__(self, entry_type="Расход"):
        super().__init__()
        self.entry_type = entry_type
        self._data  = []
        self._theme = DARK
        self._title = "Расходы по категориям" if entry_type=="Расход" else "Доходы по категориям"
        self._empty = "Нет данных о расходах" if entry_type=="Расход" else "Нет данных о доходах"
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(180)
        # Виджет сам рисует весь фон — Qt не должен его затирать
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    def plot(self, df, theme):
        self._theme = theme; self._data = []
        pal = PIE_COLORS
        if not df.empty and "Type" in df.columns and "Amount" in df.columns:
            exp = df[df["Type"].astype(str).str.strip()==self.entry_type].copy()
            exp["Amount"] = pd.to_numeric(exp["Amount"],errors="coerce").fillna(0)
            grp = exp.groupby("Category")["Amount"].sum()
            grp = grp[grp>0].sort_values(ascending=False)
            for i,(cat,val) in enumerate(grp.items()):
                self._data.append((cat, float(val), pal[i%len(pal)]))
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self._theme; W = self.width(); H = self.height()
        p.fillRect(0,0,W,H, QColor(t["surface"]))

        p.setFont(QFont("Segoe UI",10,QFont.Weight.Bold))
        p.setPen(QColor(t["text"]))
        p.drawText(0,4,W,22, Qt.AlignmentFlag.AlignHCenter, self._title)

        if not self._data:
            p.setFont(QFont("Segoe UI",10)); p.setPen(QColor(t["text_dim"]))
            p.drawText(0,H//2-10,W,20, Qt.AlignmentFlag.AlignHCenter, self._empty)
            p.end(); return

        from PyQt6.QtCore import QRectF
        leg_rows = math.ceil(len(self._data)/3)
        leg_h    = leg_rows*22+8
        pie_top  = 30; pie_bot = H-leg_h-8
        pie_h    = pie_bot-pie_top
        diam     = max(40, min(W-20, pie_h)-4)
        cx=W//2; cy=pie_top+pie_h//2; r=diam//2
        total = sum(v for _,v,_ in self._data)

        angle = 90.0
        for label,val,hex_c in self._data:
            sweep = (val/total)*360.0
            p.setBrush(QBrush(QColor(hex_c)))
            p.setPen(QPen(QColor(t["surface"]),2))
            p.drawPie(QRectF(cx-r,cy-r,diam,diam), int(angle*16), int(-sweep*16))
            if sweep>15:
                mid = math.radians(angle-sweep/2)
                tx = cx+(r*0.62)*math.cos(mid); ty = cy-(r*0.62)*math.sin(mid)
                p.setFont(QFont("Segoe UI",7,QFont.Weight.Bold))
                p.setPen(QColor("white"))
                p.drawText(int(tx)-20,int(ty)-8,40,16, Qt.AlignmentFlag.AlignHCenter, f"{val/total*100:.1f}%")
            angle -= sweep

        n = len(self._data); cols = min(n,3); cell_w = W//cols
        p.setFont(QFont("Segoe UI",8))
        for i,(label,val,hex_c) in enumerate(self._data):
            ci=i%cols; ri=i//cols
            lx=ci*cell_w+6; ly=pie_bot+6+ri*22
            p.setBrush(QBrush(QColor(hex_c))); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(lx,ly+3,12,12,3,3)
            p.setPen(QColor(t["text"]))
            fm=p.fontMetrics()
            txt=fm.elidedText(label,Qt.TextElideMode.ElideRight,cell_w-22)
            p.drawText(lx+16,ly,cell_w-20,18,Qt.AlignmentFlag.AlignVCenter,txt)
        p.end()


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Управление финансами и Тугрики")
        # Иконка приложения — ищем рядом с main.py
        import os as _os
        _icon_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "logo.ico")
        _png_path  = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "Logo.png")
        from PyQt6.QtGui import QIcon
        if _os.path.exists(_icon_path):
            self.setWindowIcon(QIcon(_icon_path))
        elif _os.path.exists(_png_path):
            self.setWindowIcon(QIcon(_png_path))
        self.resize(1350,860)
        self.is_dark=True; self.theme=DARK
        self.csv_path=None
        self.df=pd.DataFrame(columns=["Date","Type","Category","Amount","Comment"])
        self.state=load_data()
        self.excl=[]
        self.image_cache={}
        self._rf_model = None   # обученная модель RF
        self._rf_le = None      # LabelEncoder для категорий
        self._rf_features = None  # список признаков
        self._dice_timer=QTimer(); self._dice_timer.timeout.connect(self._dice_tick)
        self._dice_frames=0; self._dice_delay=30; self._dice_avail=[]
        self._bounce_step=0; self._bounce_val=0
        self.SHOP=[{"name":"Вечер кино","price":50},{"name":"Вкусный ужин","price":150},
                   {"name":"Выходной от дел","price":500},{"name":"Подарок себе","price":1000}]
        self._build(); self._apply_theme()

    # ── данные ──────────────────────────────────────────────────────────────
    def _save(self):
        with open(DATA_FILE,"w",encoding="utf-8") as f:
            json.dump(self.state,f,ensure_ascii=False,indent=2)

    def _update_tug(self):
        self.tug_lbl.setText(f"Тугрики: {self.state['tugriki']} 💰")
        self._refresh_history()

    # ── тема ────────────────────────────────────────────────────────────────
    def _apply_theme(self):
        t=self.theme
        # ВАЖНО: стиль задаём только на главном окне, не на QApplication
        # QMessageBox и другие системные диалоги НЕ наследуют этот стиль
        stylesheet = f"""
            QMainWindow,QWidget#central{{background:{t['bg']};}}
            QTabWidget::pane{{background:{t['surface']};border:none;margin-top:0;}}
            QTabBar{{background:transparent;border:none;}}
            QTabBar::tab{{background:{t['surface2']};color:{t['text_dim']};
                padding:8px 22px;font-size:13px;font-weight:600;border:1px solid {t['border']};
                border-bottom:none;margin-right:3px;
                border-top-left-radius:8px;border-top-right-radius:8px;}}
            QTabBar::tab:selected{{background:{t['accent']};color:white;border-color:{t['accent']};}}
            QTabBar::tab:hover:!selected{{background:{t['border']};color:{t['text']};}}
            QPushButton{{background:{t['accent']};color:white;border:none;border-radius:7px;
                padding:7px 16px;font-size:13px;font-weight:600;}}
            QPushButton:hover{{background:{t['accent']}dd;}}
            QPushButton:disabled{{background:{t['border']};color:{t['text_dim']};}}
            QPushButton#outline{{background:transparent;border:1.5px solid {t['accent']};color:{t['accent']};padding:5px 12px;}}
            QPushButton#outline:hover{{background:{t['surface2']};}}
            QPushButton#cal_arrow{{background:{t['surface2']};color:{t['text']};border:1.5px solid {t['border']};border-radius:6px;font-size:10px;padding:0;}}
            QPushButton#cal_arrow:hover{{background:{t['border']};}}
            QPushButton#red{{background:#c75b5b;color:white;}}
            QPushButton#red:hover{{background:#e05555;}}
            QLineEdit,QComboBox{{background:{t['surface2']};border:1px solid {t['border']};
                border-radius:6px;padding:5px 10px;color:{t['text']};font-size:13px;}}
            QLineEdit:focus,QComboBox:focus{{border-color:{t['accent']};}}
            QComboBox::drop-down{{border:none;width:20px;}}
            QComboBox QAbstractItemView{{background:{t['surface']};color:{t['text']};
                selection-background-color:{t['select']};border:1px solid {t['border']};}}
            QTableWidget{{background:{t['surface']};alternate-background-color:{t['row_alt']};
                color:{t['text']};gridline-color:{t['border']};border:none;font-size:13px;
                selection-background-color:{t['select']};selection-color:{t['text']};}}
            QHeaderView::section{{background:{t['surface2']};color:{t['text']};padding:7px 10px;
                font-weight:700;font-size:12px;border:none;
                border-bottom:1px solid {t['border']};border-right:1px solid {t['border']};}}
            QTableWidget::item{{padding:4px 8px;color:{t['text']};}}
            QScrollBar:vertical{{background:transparent;width:6px;border-radius:3px;}}
            QScrollBar::handle:vertical{{background:{t['border']};border-radius:3px;min-height:20px;}}
            QScrollBar::handle:vertical:hover{{background:{t['accent']};}}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}
            QScrollBar:horizontal{{background:transparent;height:6px;border-radius:3px;}}
            QScrollBar::handle:horizontal{{background:{t['border']};border-radius:3px;}}
            QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal{{width:0;}}
            QLabel{{color:{t['text']};background:transparent;}}
            QFrame#card{{background:{t['surface']};border-radius:8px;border:1px solid {t['border']};}}
            QFrame#topbar{{background:{t['surface']};border-radius:8px;border:1px solid {t['border']};}}
            QFrame#task_a{{background:{t['surface']};border-radius:7px;border:1px solid {t['border']};}}
            QFrame#task_d{{background:{t['row_alt']};border-radius:7px;border:1px solid {t['border']};}}
            QFrame#col_f{{background:{t['surface']};border-radius:8px;border:1px solid {t['border']};}}
            QScrollArea{{background:transparent;border:none;}}
        """
        self.setStyleSheet(stylesheet)
        self._apply_theme_widgets()

    def _msg(self, parent, kind, title, text):
        """Показывает QMessageBox в текущей теме приложения"""
        t = self.theme
        is_dark = self.is_dark
        bg      = t["surface"]
        bg2     = t["surface2"]
        text_c  = t["text"]
        border  = t["border"]
        accent  = t["accent"]
        msg_style = f"""
            QMessageBox {{
                background-color: {bg};
                color: {text_c};
            }}
            QMessageBox QLabel {{
                color: {text_c};
                background: transparent;
            }}
            QPushButton {{
                background: {accent};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 18px;
                font-size: 13px;
                font-weight: 600;
                min-width: 60px;
            }}
            QPushButton:hover {{
                background: {accent}dd;
            }}
        """
        box = QMessageBox(parent)
        box.setStyleSheet(msg_style)
        box.setWindowTitle(title)
        box.setText(text)
        if kind == "info":    box.setIcon(QMessageBox.Icon.Information)
        elif kind == "warn":  box.setIcon(QMessageBox.Icon.Warning)
        elif kind == "error": box.setIcon(QMessageBox.Icon.Critical)
        elif kind == "question":
            box.setIcon(QMessageBox.Icon.Question)
            box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            box.setDefaultButton(QMessageBox.StandardButton.No)
            box.button(QMessageBox.StandardButton.Yes).setText("Да")
            box.button(QMessageBox.StandardButton.No).setText("Нет")
        box.exec()
        return box.result()

    def _apply_theme_widgets(self):
        """Обновляет виджеты после применения stylesheet"""
        t = self.theme
        if hasattr(self,"tug_lbl"):
            self.tug_lbl.setStyleSheet(
                f"QPushButton{{color:{t['positive']};font-size:16px;font-weight:700;"
                f"background:transparent;border:none;padding:0;}}"
                f"QPushButton:hover{{text-decoration:underline;}}"
            )
        if hasattr(self,"dice"):
            self.dice.update_theme(t)
        if hasattr(self,"inv_scroll"):
            self._inv_scroll_update_bg()
            self._refresh_inv()
        if hasattr(self,"pie_exp"):
            self.pie_exp.plot(self.df, t)
            self.pie_inc.plot(self.df, t)

        if hasattr(self,"theme_btn"):
            self.theme_btn.setText("☀️ Светлая" if self.is_dark else "🌙 Тёмная")

    def _toggle_theme(self):
        self.is_dark = not self.is_dark
        self.theme = DARK if self.is_dark else LIGHT
        self._apply_theme()

    # ── UI ──────────────────────────────────────────────────────────────────
    def _build(self):
        c=QWidget(); c.setObjectName("central"); self.setCentralWidget(c)
        root=QVBoxLayout(c); root.setContentsMargins(12,10,12,10); root.setSpacing(8)

        tb=QFrame(); tb.setObjectName("topbar"); tb.setFixedHeight(52)
        tl=QHBoxLayout(tb); tl.setContentsMargins(14,0,14,0); tl.setSpacing(8)
        self.lbl_file=QLabel("Файл не выбран")
        self.lbl_file.setStyleSheet("color:#999;font-style:italic;background:transparent;")
        tl.addWidget(self.lbl_file); tl.addSpacing(6)
        b=QPushButton("Открыть CSV"); b.clicked.connect(self._open_csv); tl.addWidget(b)
        b2=QPushButton("Создать CSV"); b2.setObjectName("outline")
        b2.clicked.connect(self._create_csv); tl.addWidget(b2)
        tl.addStretch()
        self.theme_btn=QPushButton("☀️ Светлая"); self.theme_btn.setObjectName("outline")
        self.theme_btn.setFixedWidth(120); self.theme_btn.clicked.connect(self._toggle_theme)
        tl.addWidget(self.theme_btn); tl.addSpacing(14)

        # Тугрики — кнопка, при клике открывает историю
        self.tug_lbl=QPushButton(f"Тугрики: {self.state['tugriki']} 💰")
        self.tug_lbl.setStyleSheet(
            f"QPushButton{{color:{self.theme['positive']};font-size:16px;font-weight:700;"
            f"background:transparent;border:none;padding:0;}}"
            f"QPushButton:hover{{text-decoration:underline;}}"
        )
        self.tug_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tug_lbl.clicked.connect(self._show_history_popup)
        tl.addWidget(self.tug_lbl); root.addWidget(tb)

        self.tabs=QTabWidget(); self.tabs.setDocumentMode(False)
        root.addWidget(self.tabs)
        self._build_finance(); self._build_tasks()
        self._build_shop();    self._build_dice()

    # ── ФИНАНСЫ ─────────────────────────────────────────────────────────────
    def _build_finance(self):
        tab=QWidget(); self.tabs.addTab(tab,"Финансы")
        main_lay=QVBoxLayout(tab); main_lay.setContentsMargins(10,10,10,10); main_lay.setSpacing(8)

        # ── Тулбар: кнопки + фильтр + статистика ─────────────────────────
        bar=QFrame(); bar.setObjectName("card"); bar.setFixedHeight(46)
        bl=QHBoxLayout(bar); bl.setContentsMargins(8,4,8,4); bl.setSpacing(8)
        eb=QPushButton("Редактировать строку"); eb.setFixedHeight(30)
        eb.clicked.connect(self._edit_row); bl.addWidget(eb)
        db=QPushButton("Удалить строку"); db.setObjectName("red")
        db.setFixedHeight(30); db.clicked.connect(self._del_row); bl.addWidget(db)
        sep_v=QFrame(); sep_v.setFrameShape(QFrame.Shape.VLine)
        sep_v.setStyleSheet(f"background:{self.theme['border']};max-width:1px;border:none;")
        bl.addWidget(sep_v)
        bl.addWidget(QLabel("Период:"))
        self.sum_quick=QComboBox()
        self.sum_quick.addItems(["За всё время",
            "1 квартал","2 квартал","3 квартал","4 квартал",
            "1 полугодие","2 полугодие","За год"])
        self.sum_quick.setFixedWidth(140)
        self.sum_quick.currentTextChanged.connect(self._on_quick_period)
        bl.addWidget(self.sum_quick)
        from datetime import date as _date
        self.sum_year=QComboBox()
        cur_y=_date.today().year
        self.sum_year.addItems([str(y) for y in range(cur_y,cur_y-10,-1)])
        self.sum_year.setFixedWidth(70); self.sum_year.setVisible(False)
        bl.addWidget(self.sum_year)
        bl.addWidget(QLabel("С:"))
        self.sum_from=QLineEdit(_date.today().replace(day=1).isoformat())
        self.sum_from.setFixedWidth(90); bl.addWidget(self.sum_from)
        cb1=QPushButton("▼"); cb1.setObjectName("cal_arrow"); cb1.setFixedSize(24,24)
        cb1.clicked.connect(lambda: self._pick_date(self.sum_from)); bl.addWidget(cb1)
        bl.addWidget(QLabel("По:"))
        self.sum_to=QLineEdit(_date.today().isoformat())
        self.sum_to.setFixedWidth(90); bl.addWidget(self.sum_to)
        cb2=QPushButton("▼"); cb2.setObjectName("cal_arrow"); cb2.setFixedSize(24,24)
        cb2.clicked.connect(lambda: self._pick_date(self.sum_to)); bl.addWidget(cb2)
        go_btn=QPushButton("Показать"); go_btn.setFixedHeight(28); go_btn.setFixedWidth(90)
        go_btn.clicked.connect(self._refresh_summary); bl.addWidget(go_btn)
        bl.addStretch()
        # Статблоки доходы/расходы/баланс
        def _make_stat(layout, label, color):
            vl=QVBoxLayout(); vl.setSpacing(0); vl.setContentsMargins(6,0,6,0)
            lbl=QLabel(label); lbl.setStyleSheet(f"color:{self.theme['text_dim']};font-size:10px;")
            val=QLabel("—"); val.setStyleSheet(f"font-size:14px;font-weight:800;color:{color};")
            vl.addWidget(lbl); vl.addWidget(val); layout.addLayout(vl)
            return val
        self.sv_income  = _make_stat(bl,"Доходы",  self.theme["positive"])
        self.sv_expense = _make_stat(bl,"Расходы", self.theme["negative"])
        self.sv_balance = _make_stat(bl,"Баланс",  self.theme["accent"])

        # Разделитель + кнопка прогноза
        sep2=QFrame(); sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet(f"background:{self.theme['border']};max-width:1px;border:none;")
        bl.addWidget(sep2)
        forecast_btn=QPushButton("Прогноз на след. месяц")
        forecast_btn.setObjectName("outline")
        forecast_btn.clicked.connect(self._show_forecast)
        bl.addWidget(forecast_btn)

        sep3=QFrame(); sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setStyleSheet(f"background:{self.theme['border']};max-width:1px;border:none;")
        bl.addWidget(sep3)
        ml_btn=QPushButton("Обучить модель (RF)")
        ml_btn.setObjectName("outline")
        ml_btn.clicked.connect(self._train_and_show_ml)
        bl.addWidget(ml_btn)
        main_lay.addWidget(bar)

        # ── Splitter: форма | таблица | графики ───────────────────────────
        splitter=QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)
        splitter.setStyleSheet("""
            QSplitter::handle{background:#545454;border-radius:3px;}
            QSplitter::handle:hover{background:#5b7fc7;}
        """)

        # Форма добавления
        form=QFrame(); form.setObjectName("card")
        fl=QVBoxLayout(form); fl.setContentsMargins(14,14,14,14); fl.setSpacing(9)
        lh=QLabel("Добавить запись"); lh.setStyleSheet("font-size:14px;font-weight:700;")
        fl.addWidget(lh)
        self.f_type=QComboBox(); self.f_type.addItems(["Расход","Доход"])
        self.f_type.currentTextChanged.connect(self._update_cats); fl.addWidget(self.f_type)
        dr=QHBoxLayout(); dr.setSpacing(4); dr.addWidget(QLabel("Дата:"))
        self.f_date=QLineEdit(_date.today().isoformat())
        self.f_date.setPlaceholderText("гггг-мм-дд")
        self.f_date.setFixedWidth(110); dr.addWidget(self.f_date)
        cal_btn=QPushButton("▼"); cal_btn.setFixedSize(28,28)
        cal_btn.setObjectName("cal_arrow")
        cal_btn.clicked.connect(self._show_calendar); dr.addWidget(cal_btn)
        fl.addLayout(dr)
        self.f_cat=QComboBox(); self._update_cats(); fl.addWidget(self.f_cat)
        self.f_amt=QLineEdit(); self.f_amt.setPlaceholderText("Сумма"); fl.addWidget(self.f_amt)
        self.f_com=QLineEdit(); self.f_com.setPlaceholderText("Комментарий"); fl.addWidget(self.f_com)
        sb=QPushButton("Сохранить в CSV"); sb.clicked.connect(self._add_row); fl.addWidget(sb)
        self.edit_mode_lbl=QLabel("")
        self.edit_mode_lbl.setStyleSheet(f"color:{self.theme['positive']};font-size:11px;font-weight:600;")
        fl.addWidget(self.edit_mode_lbl)
        self._editing_row=None
        fl.addStretch()
        splitter.addWidget(form)

        # Таблица
        tf=QFrame(); tf.setObjectName("card")
        tfl=QVBoxLayout(tf); tfl.setContentsMargins(0,0,0,0)
        self.fin_tbl=QTableWidget()
        self.fin_tbl.setColumnCount(5)
        self.fin_tbl.setHorizontalHeaderLabels(["Дата","Тип","Категория","Сумма","Комментарий"])
        self.fin_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.fin_tbl.setAlternatingRowColors(True)
        self.fin_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.fin_tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.fin_tbl.verticalHeader().setVisible(False)
        tfl.addWidget(self.fin_tbl)
        splitter.addWidget(tf)

        # Графики
        charts=QWidget(); cl=QVBoxLayout(charts); cl.setContentsMargins(0,0,0,0); cl.setSpacing(8)
        cf1=QFrame(); cf1.setObjectName("card"); cfl1=QVBoxLayout(cf1); cfl1.setContentsMargins(6,6,6,6)
        save_exp=QPushButton("Сохранить PNG"); save_exp.setFixedHeight(26)
        save_exp.setStyleSheet("font-size:11px;padding:2px 8px;")
        save_exp.clicked.connect(lambda: self._save_chart_png(self.pie_exp,"расходы"))
        cfl1.addWidget(save_exp, alignment=Qt.AlignmentFlag.AlignRight)
        self.pie_exp=PieWidget("Расход"); cfl1.addWidget(self.pie_exp); cl.addWidget(cf1,stretch=1)
        cf2=QFrame(); cf2.setObjectName("card"); cfl2=QVBoxLayout(cf2); cfl2.setContentsMargins(6,6,6,6)
        save_inc=QPushButton("Сохранить PNG"); save_inc.setFixedHeight(26)
        save_inc.setStyleSheet("font-size:11px;padding:2px 8px;")
        save_inc.clicked.connect(lambda: self._save_chart_png(self.pie_inc,"доходы"))
        cfl2.addWidget(save_inc, alignment=Qt.AlignmentFlag.AlignRight)
        self.pie_inc=PieWidget("Доход"); cfl2.addWidget(self.pie_inc); cl.addWidget(cf2,stretch=1)
        splitter.addWidget(charts)

        # Начальные размеры: форма 240, таблица 700, графики 370
        splitter.setSizes([240, 700, 370])
        main_lay.addWidget(splitter)


    def _show_calendar(self):
        from PyQt6.QtWidgets import QCalendarWidget, QDialog, QVBoxLayout
        from PyQt6.QtCore import QDate
        dlg = QDialog(self)
        dlg.setWindowTitle("Выбор даты")
        t = self.theme
        dlg.setStyleSheet(f"""
            QDialog {{ background: {t['surface']}; color: {t['text']}; }}
            QCalendarWidget {{ background: {t['surface']}; color: {t['text']}; }}
            QCalendarWidget QAbstractItemView {{
                background: {t['surface2']}; color: {t['text']};
                selection-background-color: {t['accent']}; selection-color: white;
            }}
            QCalendarWidget QToolButton {{
                background: {t['surface2']}; color: {t['text']};
                border-radius: 4px; padding: 3px 8px;
            }}
            QCalendarWidget QToolButton:hover {{ background: {t['accent']}; color: white; }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{ background: {t['surface']}; }}
            QCalendarWidget QSpinBox {{ background: {t['surface2']}; color: {t['text']}; border: none; }}
        """)
        dlg.setFixedSize(300, 220)
        vl = QVBoxLayout(dlg); vl.setContentsMargins(4,4,4,4)
        cal = QCalendarWidget()
        cal.setGridVisible(True)
        # Установим текущую дату если поле заполнено
        try:
            d = QDate.fromString(self.f_date.text().strip(), "yyyy-MM-dd")
            if d.isValid(): cal.setSelectedDate(d)
        except: pass
        def pick(date):
            self.f_date.setText(date.toString("yyyy-MM-dd"))
            dlg.accept()
        cal.clicked.connect(pick)
        vl.addWidget(cal)
        dlg.exec()

    def _update_cats(self):
        self.f_cat.clear()
        self.f_cat.addItems(CATS_INC if self.f_type.currentText()=="Доход" else CATS_EXP)

    def _open_csv(self):
        p,_=QFileDialog.getOpenFileName(self,"Открыть CSV","","CSV (*.csv)")
        if p: self.csv_path=p; self.lbl_file.setText(os.path.basename(p)); self._reload()

    def _create_csv(self):
        p,_=QFileDialog.getSaveFileName(self,"Создать CSV","","CSV (*.csv)")
        if p:
            pd.DataFrame(columns=["Date","Type","Category","Amount","Comment"])\
              .to_csv(p,index=False,encoding="utf-8-sig")
            self.csv_path=p; self.lbl_file.setText(os.path.basename(p)); self._reload()

    def _reload(self):
        if not self.csv_path: return
        for enc in ["utf-8-sig","utf-8","cp1251","latin1"]:
            try:
                df=pd.read_csv(self.csv_path,encoding=enc,sep=None,engine="python",dtype=str)
                if len(df.columns)>=2: self.df=df; break
            except: continue
        cm={}
        for c in self.df.columns:
            lo=c.strip().lower()
            if lo in("date","дата"):cm[c]="Date"
            elif lo in("type","тип"):cm[c]="Type"
            elif lo in("category","категория"):cm[c]="Category"
            elif lo in("amount","сумма","sum"):cm[c]="Amount"
            elif lo in("comment","комментарий"):cm[c]="Comment"
        self.df.rename(columns=cm,inplace=True)
        for c in["Date","Type","Category","Amount","Comment"]:
            if c not in self.df.columns: self.df[c]=""
        self._editing_row=None
        if hasattr(self,"edit_mode_lbl"): self.edit_mode_lbl.setText("")
        self._refresh_tbl(); self._refresh_charts()

    def _refresh_tbl(self):
        t=self.theme; self.fin_tbl.setRowCount(0)
        for _,row in self.df.iterrows():
            r=self.fin_tbl.rowCount(); self.fin_tbl.insertRow(r)
            for ci,key in enumerate(["Date","Type","Category","Amount","Comment"]):
                val=str(row.get(key,"")) if pd.notna(row.get(key,"")) else ""
                item=QTableWidgetItem(val)
                if key=="Type":
                    item.setForeground(QColor(t["negative"]) if "расход" in val.lower()
                                       else QColor(t["positive"]) if "доход" in val.lower()
                                       else QColor(t["text"]))
                else: item.setForeground(QColor(t["text"]))
                self.fin_tbl.setItem(r,ci,item)

    def _save_chart_png(self, widget, name):
        from datetime import date as _d
        default = f"график_{name}_{_d.today().isoformat()}.png"
        path, _ = QFileDialog.getSaveFileName(
            self, f"Сохранить график — {name}", default, "PNG (*.png)"
        )
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        pix = QPixmap(widget.size())
        pix.fill(Qt.GlobalColor.transparent)
        widget.render(pix)
        if pix.save(path, "PNG"):
            self._msg(self, "info", "Сохранено", f"График сохранён:\n{path}")
        else:
            self._msg(self, "error", "Ошибка", "Не удалось сохранить файл.")

    def _refresh_charts(self):
        self.pie_exp.plot(self.df,self.theme)
        self.pie_inc.plot(self.df,self.theme)

    def _add_row(self):
        if not self.csv_path:
            self._msg(self,"warn","Внимание","Сначала выберите или создайте CSV файл!"); return
        try: amt=float(self.f_amt.text().replace(",","."))
        except: self._msg(self,"error","Ошибка","Сумма должна быть числом!"); return

        row_data = {
            "Date":     self.f_date.text().strip(),
            "Type":     self.f_type.currentText(),
            "Category": self.f_cat.currentText(),
            "Amount":   str(amt),   # строка — df читается как dtype=str
            "Comment":  self.f_com.text(),
        }

        if self._editing_row is not None:
            for key, val in row_data.items():
                self.df.at[self._editing_row, key] = str(val)
            self._editing_row = None
            self.edit_mode_lbl.setText("")
        else:
            # Добавляем новую строку
            self.df = pd.concat([self.df, pd.DataFrame([row_data])], ignore_index=True)

        self.df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
        self.f_amt.clear(); self.f_com.clear()
        self._refresh_tbl(); self._refresh_charts()

    def _edit_row(self):
        rows = self.fin_tbl.selectionModel().selectedRows()
        if not rows:
            self._msg(self,"info","","Сначала выберите строку."); return
        idx = rows[0].row()
        row = self.df.iloc[idx]

        # Заполняем форму данными строки
        typ = str(row.get("Type","Расход"))
        self.f_type.setCurrentText(typ if typ in ["Расход","Доход"] else "Расход")
        self._update_cats()
        cat = str(row.get("Category",""))
        if self.f_cat.findText(cat) >= 0:
            self.f_cat.setCurrentText(cat)
        self.f_date.setText(str(row.get("Date","")) if str(row.get("Date","")) != "nan" else "")
        amt = str(row.get("Amount",""))
        self.f_amt.setText("" if amt=="nan" else amt)
        com = str(row.get("Comment",""))
        self.f_com.setText("" if com=="nan" else com)

        self._editing_row = idx
        self.edit_mode_lbl.setText(f"✏️ Режим редактирования строки {idx+1}")
        self.fin_tbl.selectRow(idx)

    def _del_row(self):
        rows = self.fin_tbl.selectionModel().selectedRows()
        if not rows:
            self._msg(self, "info", "", "Выберите строку."); return
        idx = rows[0].row()
        box = QMessageBox(self)
        t = self.theme
        box.setStyleSheet(f"""
            QMessageBox {{ background: {t['surface']}; color: {t['text']}; }}
            QMessageBox QLabel {{ color: {t['text']}; background: transparent; }}
            QPushButton {{ background: {t['accent']}; color: white; border: none;
                border-radius: 6px; padding: 6px 18px; font-size: 13px; font-weight: 600; min-width: 60px; }}
            QPushButton:hover {{ background: {t['accent']}dd; }}
        """)
        box.setWindowTitle("Подтверждение")
        box.setText(f"Удалить строку {idx+1}?")
        box.setIcon(QMessageBox.Icon.Question)
        yes = box.addButton("Да",  QMessageBox.ButtonRole.YesRole)
        box.addButton("Нет", QMessageBox.ButtonRole.NoRole)
        box.exec()
        if box.clickedButton() == yes:
            self.df = self.df.drop(index=idx).reset_index(drop=True)
            if self.csv_path:
                self.df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
            self._editing_row = None
            self.edit_mode_lbl.setText("")
            self._refresh_tbl(); self._refresh_charts()

    # ── ЗАДАЧИ ──────────────────────────────────────────────────────────────
    def _build_tasks(self):
        tab=QWidget(); self.tabs.addTab(tab,"Задачи")
        vl=QVBoxLayout(tab); vl.setContentsMargins(12,12,12,12); vl.setSpacing(10)
        inp=QFrame(); inp.setObjectName("card")
        il=QHBoxLayout(inp); il.setContentsMargins(12,10,12,10); il.setSpacing(8)
        self.t_name=QLineEdit(); self.t_name.setPlaceholderText("Название задачи...")
        self.t_name.setMinimumWidth(340); il.addWidget(self.t_name)
        self.t_rew=QLineEdit(); self.t_rew.setPlaceholderText(f"Награда (макс.{MAX_REWARD})")
        self.t_rew.setFixedWidth(160); il.addWidget(self.t_rew)
        ab=QPushButton("Добавить"); ab.clicked.connect(self._add_task)
        self.t_name.returnPressed.connect(self._add_task); il.addWidget(ab); il.addStretch()
        vl.addWidget(inp)
        lim=QLabel(f"Максимальная награда: {MAX_REWARD} тугриков")
        lim.setStyleSheet("color:#999;font-size:11px;"); vl.addWidget(lim)
        cols=QHBoxLayout(); cols.setSpacing(12)
        self.a_col,self.a_lay=self._task_col("Активные задачи")
        self.d_col,self.d_lay=self._task_col("Выполненные")
        cols.addWidget(self.a_col); cols.addWidget(self.d_col); vl.addLayout(cols)
        self._refresh_tasks()

    def _task_col(self,title):
        outer=QFrame(); outer.setObjectName("col_f")
        ol=QVBoxLayout(outer); ol.setContentsMargins(0,0,0,0); ol.setSpacing(0)
        hdr=QLabel(title); hdr.setStyleSheet("font-size:13px;font-weight:700;padding:11px 14px;background:transparent;")
        ol.addWidget(hdr)
        sep=QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background:{self.theme['border']};max-height:1px;border:none;"); ol.addWidget(sep)
        scroll=QScrollArea(); scroll.setWidgetResizable(True)
        inner=QWidget(); inner.setStyleSheet("background:transparent;")
        lay=QVBoxLayout(inner); lay.setContentsMargins(8,8,8,8); lay.setSpacing(5); lay.addStretch()
        scroll.setWidget(inner); ol.addWidget(scroll)
        return outer,lay

    def _add_task(self):
        name=self.t_name.text().strip()
        try:
            rew=int(self.t_rew.text())
            if not name: raise ValueError
            if rew<=0 or rew>MAX_REWARD:
                self._msg(self,"warn","",f"Награда от 1 до {MAX_REWARD}."); return
        except ValueError:
            self._msg(self,"error","Ошибка","Заполните название и награду (целое число)."); return
        self.state["tasks"].append({"title":name,"reward":rew,"done":False})
        self._save(); self._refresh_tasks()
        self.t_name.clear(); self.t_rew.clear()

    def _refresh_tasks(self):
        for lay in[self.a_lay,self.d_lay]:
            while lay.count()>1:
                item=lay.takeAt(0)
                if item.widget(): item.widget().deleteLater()
        for i,t in enumerate(self.state["tasks"]):
            card=QFrame(); cl=QHBoxLayout(card); cl.setContentsMargins(10,6,10,6); cl.setSpacing(8)
            if not t.get("done"):
                card.setObjectName("task_a")
                lbl=QLabel(t["title"]); lbl.setStyleSheet("font-size:13px;")
                rew=QLabel(f"+{t['reward']} 💰")
                rew.setStyleSheet(f"color:{self.theme['positive']};font-weight:700;font-size:12px;")
                rew.setFixedWidth(60); rew.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
                btn=QPushButton("Выполнено")
                btn.setStyleSheet(
                    f"QPushButton{{background:{self.theme['positive']};color:white;border:none;"
                    f"border-radius:6px;font-size:12px;font-weight:600;padding:3px 8px;}}"
                    f"QPushButton:hover{{background:{self.theme['positive']}cc;}}")
                btn.setFixedWidth(105); btn.setFixedHeight(28)
                btn.clicked.connect(lambda _,idx=i: self._complete(idx))
                cl.addWidget(lbl,stretch=1); cl.addWidget(rew); cl.addWidget(btn)
                self.a_lay.insertWidget(self.a_lay.count()-1,card)
            else:
                card.setObjectName("task_d")
                lbl=QLabel(t["title"])
                lbl.setStyleSheet(f"font-size:13px;color:{self.theme['text_dim']};text-decoration:line-through;")
                rew=QLabel(f"+{t['reward']} 💰")
                rew.setStyleSheet(f"color:{self.theme['positive']};font-weight:700;font-size:12px;")
                rew.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
                cl.addWidget(lbl,stretch=1); cl.addWidget(rew)
                self.d_lay.insertWidget(self.d_lay.count()-1,card)

    def _complete(self,idx):
        reward = self.state["tasks"][idx]["reward"]
        self.state["tugriki"] += reward
        self.state["tasks"][idx]["done"] = True
        self._record_history(f'+{reward}', f'Задача: {self.state["tasks"][idx]["title"]}')
        self._save(); self._update_tug(); self._refresh_tasks()

    # ── МАГАЗИН ─────────────────────────────────────────────────────────────
    def _build_shop(self):
        tab=QWidget(); self.tabs.addTab(tab,"Магазин")
        vl=QVBoxLayout(tab); vl.setContentsMargins(12,12,12,12)
        it=QTabWidget(); vl.addWidget(it)
        sw=QWidget(); self._build_store(sw); it.addTab(sw,"Витрина")

        # Приобретённое — постоянная структура, обновляем только grid
        self.inv_w=QWidget()
        inv_layout=QVBoxLayout(self.inv_w); inv_layout.setContentsMargins(0,0,0,0)
        self.inv_scroll=QScrollArea(); self.inv_scroll.setWidgetResizable(True)
        self.inv_scroll.setWidgetResizable(True)
        self.inv_scroll.setFrameShape(self.inv_scroll.Shape.NoFrame)
        inv_layout.addWidget(self.inv_scroll)
        self._inv_scroll_update_bg()
        it.addTab(self.inv_w,"Приобретённое")
        self._refresh_inv()

        self._refresh_history()

    def _build_store(self,parent):
        scroll=QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        inner=QWidget(); inner.setStyleSheet("background:transparent;")
        grid=QGridLayout(inner); grid.setContentsMargins(24,24,24,24); grid.setSpacing(20)
        for i,item in enumerate(self.SHOP):
            card=QFrame(); card.setObjectName("card"); card.setFixedSize(222,258)
            vl2=QVBoxLayout(card); vl2.setContentsMargins(12,14,12,14)
            vl2.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_lbl=QLabel(); img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pix=self._get_pix(item["name"])
            img_lbl.setPixmap(pix.scaled(110,110,Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation))
            vl2.addWidget(img_lbl)
            nl=QLabel(item["name"]); nl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            nl.setStyleSheet("font-size:14px;font-weight:700;"); vl2.addWidget(nl)
            pl=QLabel(f"{item['price']} Тугриков"); pl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pl.setStyleSheet(f"color:{self.theme['positive']};font-size:12px;font-weight:600;")
            vl2.addWidget(pl)
            btn=QPushButton("Купить"); btn.setFixedWidth(140); btn.setFixedHeight(36)
            btn.setStyleSheet(
                f"QPushButton{{background:{self.theme['positive']};color:white;border:none;"
                f"border-radius:8px;font-size:13px;font-weight:700;padding:6px 14px;}}"
                f"QPushButton:hover{{background:{self.theme['positive']}dd;}}")
            btn.clicked.connect(lambda _,it=item: self._buy(it))
            vl2.addWidget(btn,alignment=Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(card,i//3,i%3)
        for c in range(3): grid.setColumnStretch(c,1)
        scroll.setWidget(inner)
        pl=QVBoxLayout(parent); pl.setContentsMargins(0,0,0,0); pl.addWidget(scroll)

    def _get_pix(self,name):
        if name in self.image_cache: return self.image_cache[name]
        path=os.path.join(IMAGES_DIR,f"{name}.png")
        if os.path.exists(path): pix=QPixmap(path)
        else:
            r,g,b=random.randint(60,120),random.randint(60,120),random.randint(80,160)
            pix=QPixmap(120,120); pix.fill(QColor(r,g,b))
            p=QPainter(pix); p.setPen(QColor("white"))
            p.setFont(QFont("Arial",38,QFont.Weight.Bold))
            p.drawText(pix.rect(),Qt.AlignmentFlag.AlignCenter,name[0].upper()); p.end()
        self.image_cache[name]=pix; return pix

    def _train_and_show_ml(self):
        """Обучает Random Forest на текущих данных и показывает результаты"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QProgressBar
        t = self.theme

        df = self.df.copy()
        if df.empty or len(df) < 20:
            self._msg(self,"warn","ML","Недостаточно данных (нужно минимум 20 записей)."); return
        if "Type" not in df.columns or "Amount" not in df.columns:
            self._msg(self,"warn","ML","Нет нужных столбцов (Type, Amount)."); return

        # ── Подготовка данных ────────────────────────────────────────────
        try:
            import numpy as np
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
            from sklearn.preprocessing import LabelEncoder, StandardScaler
            from sklearn.metrics import roc_auc_score, accuracy_score, f1_score, classification_report
        except ImportError:
            self._msg(self,"error","ML","Установите scikit-learn:\npip install scikit-learn numpy"); return

        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
        df["Date"]   = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date","Type"])

        # Признаки
        df["month"]          = df["Date"].dt.month
        df["day"]            = df["Date"].dt.day
        df["weekday"]        = df["Date"].dt.weekday
        df["is_weekend"]     = (df["weekday"] >= 5).astype(int)
        df["quarter"]        = df["Date"].dt.quarter
        df["year"]           = df["Date"].dt.year
        df["is_month_start"] = (df["day"] <= 5).astype(int)
        df["is_month_end"]   = (df["day"] >= 25).astype(int)
        df["log_amount"]     = np.log1p(df["Amount"])
        df["sqrt_amount"]    = np.sqrt(df["Amount"])

        le = LabelEncoder()
        df["category_enc"] = le.fit_transform(df["Category"].fillna("Unknown"))
        df["target"]       = (df["Type"].str.strip() == "Расход").astype(int)

        FEATURES = ["Amount","log_amount","sqrt_amount","month","day","weekday",
                    "is_weekend","quarter","year","is_month_start","is_month_end","category_enc"]
        FEAT_NAMES = ["Сумма","Log(Сумма)","√Сумма","Месяц","День","День недели",
                      "Выходной","Квартал","Год","Нач.мес.","Кон.мес.","Категория"]

        X = df[FEATURES].values
        y = df["target"].values

        if len(np.unique(y)) < 2:
            self._msg(self,"warn","ML","Нужны оба типа операций (Расход и Доход)."); return

        # Разбиение
        test_size = 0.2 if len(X) >= 50 else 0.3
        X_train,X_test,y_train,y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y)

        # ── Обучение RF ──────────────────────────────────────────────────
        rf = RandomForestClassifier(
            n_estimators=200, max_depth=12,
            min_samples_leaf=2, random_state=42, n_jobs=-1
        )
        rf.fit(X_train, y_train)
        proba  = rf.predict_proba(X_test)[:,1]
        y_pred = (proba >= 0.5).astype(int)

        roc_auc  = roc_auc_score(y_test, proba)
        accuracy = accuracy_score(y_test, y_pred)
        f1       = f1_score(y_test, y_pred)

        # Важность признаков
        importances = rf.feature_importances_
        imp_order   = np.argsort(importances)[::-1]

        # Сохраняем модель для использования в прогнозе
        self._rf_model    = rf
        self._rf_le       = le
        self._rf_features = FEATURES

        # ── Окно результатов ─────────────────────────────────────────────
        dlg = QDialog(self)
        dlg.setWindowTitle("Random Forest — результаты")
        dlg.resize(580, 620)
        dlg.setStyleSheet(f"""
            QDialog{{background:{t['bg']};}}
            QLabel{{color:{t['text']};background:transparent;}}
            QTableWidget{{background:{t['surface']};color:{t['text']};
                gridline-color:{t['border']};border:none;font-size:12px;
                alternate-background-color:{t['row_alt']};}}
            QHeaderView::section{{background:{t['surface2']};color:{t['text']};
                padding:5px 8px;font-weight:700;font-size:11px;border:none;
                border-bottom:1px solid {t['border']};}}
            QTableWidget::item{{padding:3px 8px;}}
            QFrame#card{{background:{t['surface']};border-radius:8px;border:1px solid {t['border']};}}
        """)
        vl = QVBoxLayout(dlg); vl.setContentsMargins(16,16,16,16); vl.setSpacing(12)

        # Заголовок
        h = QLabel("Random Forest — результаты обучения")
        h.setStyleSheet(f"font-size:15px;font-weight:800;color:{t['accent']};")
        vl.addWidget(h)

        sub = QLabel(f"Обучено на {len(X_train):,} записях · Тест: {len(X_test):,} записей")
        sub.setStyleSheet(f"font-size:11px;color:{t['text_dim']};")
        vl.addWidget(sub)

        # Метрики
        metrics_frame = QFrame(); metrics_frame.setObjectName("card")
        ml = QHBoxLayout(metrics_frame); ml.setContentsMargins(16,10,16,10); ml.setSpacing(0)

        def metric_block(label, value, color):
            mv = QVBoxLayout(); mv.setSpacing(2)
            lbl = QLabel(label); lbl.setStyleSheet(f"color:{t['text_dim']};font-size:10px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val = QLabel(value); val.setStyleSheet(f"font-size:20px;font-weight:900;color:{color};")
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            mv.addWidget(lbl); mv.addWidget(val); ml.addLayout(mv)

        metric_block("ROC-AUC",  f"{roc_auc:.4f}",  t["accent"])
        metric_block("Accuracy", f"{accuracy:.4f}", t["positive"])
        metric_block("F1-Score", f"{f1:.4f}",       t["positive"] if f1>0.8 else t["negative"])
        metric_block("Деревьев", "200",              t["text_dim"])
        vl.addWidget(metrics_frame)

        # Статус модели
        status_lbl = QLabel("✓ Модель сохранена — теперь нажмите «Прогноз на след. месяц»")
        status_lbl.setStyleSheet(f"font-size:12px;font-weight:600;color:{t['positive']};")
        vl.addWidget(status_lbl)

        # Важность признаков
        fi_lbl = QLabel("Важность признаков (Feature Importance):")
        fi_lbl.setStyleSheet(f"font-size:12px;font-weight:700;color:{t['text']};")
        vl.addWidget(fi_lbl)

        fi_tbl = QTableWidget()
        fi_tbl.setColumnCount(3)
        fi_tbl.setHorizontalHeaderLabels(["Признак","Важность","Визуально"])
        fi_tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        fi_tbl.setColumnWidth(0, 130)
        fi_tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        fi_tbl.setColumnWidth(1, 90)
        fi_tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        fi_tbl.setAlternatingRowColors(True)
        fi_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        fi_tbl.verticalHeader().setVisible(False)
        fi_tbl.setFixedHeight(min(len(FEATURES)*28+30, 260))

        max_imp = importances[imp_order[0]]
        for rank, idx in enumerate(imp_order):
            r = fi_tbl.rowCount(); fi_tbl.insertRow(r)
            name_item = QTableWidgetItem(FEAT_NAMES[idx])
            name_item.setForeground(QColor(t["text"]))
            imp_val = importances[idx]
            val_item = QTableWidgetItem(f"{imp_val:.4f}")
            val_item.setForeground(QColor(t["accent"]))
            val_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Прогресс-бар как текст
            bar_len = int(imp_val / max_imp * 20)
            bar_item = QTableWidgetItem("█" * bar_len)
            intensity = int(imp_val / max_imp * 200) + 55
            bar_item.setForeground(QColor(t["accent"]))
            fi_tbl.setItem(r, 0, name_item)
            fi_tbl.setItem(r, 1, val_item)
            fi_tbl.setItem(r, 2, bar_item)

        vl.addWidget(fi_tbl)
        dlg.exec()

    def _show_forecast(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QScrollArea
        from datetime import date as _d
        import calendar
        import numpy as np

        t = self.theme
        df = self.df.copy()

        if df.empty or "Amount" not in df.columns or "Date" not in df.columns:
            self._msg(self,"warn","Прогноз","Нет данных для построения прогноза."); return

        # Проверяем есть ли обученная модель
        if self._rf_model is None:
            self._msg(self,"warn","Прогноз",
                      "Сначала обучите модель — нажмите «Обучить модель (RF)».")
            return

        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
        df["_date"]  = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["_date"])
        df["_month"] = df["_date"].dt.to_period("M")

        exp = df[df["Type"].astype(str).str.strip()=="Расход"].copy()
        if exp.empty:
            self._msg(self,"warn","Прогноз","Нет данных о расходах."); return

        # Берём последние 6 месяцев для прогноза
        today      = _d.today()
        months_back = 6
        cutoff = pd.Period(today, "M") - months_back
        exp_recent = exp[exp["_month"] > cutoff]
        if exp_recent.empty:
            exp_recent = exp  # если мало данных — берём все

        # Среднее по категориям за период
        monthly_by_cat = (
            exp_recent.groupby(["_month","Category"])["Amount"]
            .sum()
            .groupby("Category")
            .mean()
            .sort_values(ascending=False)
        )
        total_forecast = monthly_by_cat.sum()

        # Следующий месяц
        if today.month == 12:
            next_m = _d(today.year+1, 1, 1)
        else:
            next_m = _d(today.year, today.month+1, 1)
        next_month_name = f"{calendar.month_name[next_m.month]} {next_m.year}"

        # ── RF: предсказание для каждой записи следующего месяца ────────
        rf_predictions = []
        try:
            df_pred = df.copy()
            df_pred["Amount"] = pd.to_numeric(df_pred["Amount"], errors="coerce").fillna(0)
            df_pred["Date"]   = pd.to_datetime(df_pred["Date"], errors="coerce")
            df_pred = df_pred.dropna(subset=["Date"])
            df_pred["month"]          = next_m.month
            df_pred["day"]            = 15  # середина месяца
            df_pred["weekday"]        = 2
            df_pred["is_weekend"]     = 0
            df_pred["quarter"]        = (next_m.month - 1) // 3 + 1
            df_pred["year"]           = next_m.year
            df_pred["is_month_start"] = 0
            df_pred["is_month_end"]   = 0
            df_pred["log_amount"]     = np.log1p(df_pred["Amount"])
            df_pred["sqrt_amount"]    = np.sqrt(df_pred["Amount"])
            df_pred["category_enc"]   = self._rf_le.transform(
                df_pred["Category"].fillna("Unknown").map(
                    lambda x: x if x in self._rf_le.classes_ else self._rf_le.classes_[0]
                )
            )
            X_pred = df_pred[self._rf_features].values
            proba_pred = self._rf_model.predict_proba(X_pred)[:,1]
            n_expense = int((proba_pred >= 0.5).sum())
            n_income  = len(proba_pred) - n_expense
            avg_conf  = float(proba_pred.mean()) * 100
            rf_predictions = (n_expense, n_income, avg_conf, proba_pred)
        except Exception as e:
            rf_predictions = None

        # Диалог
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Прогноз расходов — {next_month_name}")
        dlg.resize(580, 600)
        dlg.setStyleSheet(f"""
            QDialog{{background:{t['bg']};}}
            QLabel{{color:{t['text']};background:transparent;}}
            QTableWidget{{background:{t['surface']};alternate-background-color:{t['row_alt']};
                color:{t['text']};gridline-color:{t['border']};border:none;font-size:13px;}}
            QHeaderView::section{{background:{t['surface2']};color:{t['text']};padding:6px 10px;
                font-weight:700;font-size:12px;border:none;
                border-bottom:1px solid {t['border']};border-right:1px solid {t['border']};}}
            QTableWidget::item{{padding:4px 8px;}}
            QFrame#card{{background:{t['surface']};border-radius:8px;border:1px solid {t['border']};}}
        """)

        vl = QVBoxLayout(dlg); vl.setContentsMargins(18,18,18,18); vl.setSpacing(12)

        # Заголовок
        title = QLabel(f"Прогноз расходов на {next_month_name}")
        title.setStyleSheet(f"font-size:16px;font-weight:800;color:{t['accent']};")
        vl.addWidget(title)

        # RF предсказание блок
        if rf_predictions:
            n_exp, n_inc, avg_conf, probas = rf_predictions
            rf_frame = QFrame(); rf_frame.setObjectName("card")
            rfl = QVBoxLayout(rf_frame); rfl.setContentsMargins(14,10,14,10); rfl.setSpacing(4)

            rf_title = QLabel("Random Forest — классификация текущих данных")
            rf_title.setStyleSheet(f"font-size:11px;font-weight:700;color:{t['accent']};")
            rf_sub = QLabel(
                f"Из {n_exp+n_inc:,} записей модель определила: "
                f"{n_exp:,} расходов ({n_exp/(n_exp+n_inc)*100:.1f}%) и "
                f"{n_inc:,} доходов ({n_inc/(n_exp+n_inc)*100:.1f}%) "
                f"со средней уверенностью {avg_conf:.1f}%"
            )
            rf_sub.setStyleSheet(f"font-size:12px;color:{t['text']};")
            rf_sub.setWordWrap(True)
            rfl.addWidget(rf_title); rfl.addWidget(rf_sub)
            vl.addWidget(rf_frame)

        note = QLabel(f"Статистический прогноз: среднее за последние {months_back} месяцев")
        note.setStyleSheet(f"font-size:11px;color:{t['text_dim']};")
        vl.addWidget(note)

        # Итоговая сумма
        total_lbl = QLabel(f"Ожидаемые расходы: {total_forecast:,.0f} ₽")
        total_lbl.setStyleSheet(f"font-size:18px;font-weight:900;color:{t['negative']};")
        vl.addWidget(total_lbl)

        # Таблица по категориям
        tbl = QTableWidget()
        tbl.setColumnCount(3)
        tbl.setHorizontalHeaderLabels(["Категория","Прогноз (₽)","Доля"])
        h = tbl.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed); tbl.setColumnWidth(1,130)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed); tbl.setColumnWidth(2,100)
        tbl.setAlternatingRowColors(True)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tbl.verticalHeader().setVisible(False)

        COLORS = PIE_COLORS

        for i, (cat, amt) in enumerate(monthly_by_cat.items()):
            r = tbl.rowCount(); tbl.insertRow(r)
            pct = amt / total_forecast * 100 if total_forecast > 0 else 0

            # Цветной квадрат + название категории
            it_cat = QTableWidgetItem(f"  {cat}")
            it_cat.setForeground(QColor(t["text"]))
            from PyQt6.QtGui import QFont as _QF
            it_cat.setFont(_QF("Segoe UI", 11))

            it_amt = QTableWidgetItem(f"{amt:,.0f} ₽")
            it_amt.setForeground(QColor(COLORS[i % len(COLORS)]))
            it_amt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_amt.setFont(_QF("Segoe UI", 10, 75))

            it_pct = QTableWidgetItem(f"{pct:.1f}%")
            it_pct.setForeground(QColor(t["text_dim"]))
            it_pct.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            tbl.setItem(r,0,it_cat); tbl.setItem(r,1,it_amt); tbl.setItem(r,2,it_pct)

        vl.addWidget(tbl)

        # Визуальный бар с подписями категорий
        bar_lbl = QLabel("Распределение по категориям:")
        bar_lbl.setStyleSheet(f"font-size:11px;color:{t['text_dim']};margin-top:4px;")
        vl.addWidget(bar_lbl)

        class BarWidget(QWidget):
            def __init__(self, data, total, colors, theme):
                super().__init__()
                self.data   = data
                self.total  = total
                self.colors = colors
                self.t      = theme
                self.setFixedHeight(52)

            def paintEvent(self, e):
                p = QPainter(self)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                W = self.width(); x = 0; bar_h = 28
                items = list(self.data.items())
                for i, (cat, amt) in enumerate(items):
                    w = int(amt / self.total * W) if self.total > 0 else 0
                    if w < 2: continue
                    color = QColor(self.colors[i % len(self.colors)])
                    p.setBrush(QBrush(color)); p.setPen(Qt.PenStyle.NoPen)
                    if i == 0:
                        p.drawRoundedRect(x, 0, w, bar_h, 6, 6)
                    elif i == len(items) - 1:
                        p.drawRoundedRect(x, 0, W - x, bar_h, 6, 6)
                    else:
                        p.drawRect(x, 0, w, bar_h)
                    # Подпись категории если хватает места
                    if w > 40:
                        p.setPen(QColor("white"))
                        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                        short = cat[:6] + ".." if len(cat) > 7 else cat
                        p.drawText(x+4, 0, w-6, bar_h,
                                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                                   short)
                    # Точка легенды внизу
                    p.setBrush(QBrush(color)); p.setPen(Qt.PenStyle.NoPen)
                    p.drawEllipse(x + w//2 - 4, bar_h + 8, 8, 8)
                    x += w
                p.end()

        bw = BarWidget(monthly_by_cat, total_forecast, COLORS, t)
        vl.addWidget(bw)

        dlg.exec()

    def _show_history_popup(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout
        from PyQt6.QtGui import QFont as _QF
        t = self.theme
        dlg = QDialog(self)
        dlg.setWindowTitle("История тугриков")
        dlg.resize(640, 500)
        dlg.setStyleSheet(f"""
            QDialog{{background:{t['bg']};}}
            QTableWidget{{background:{t['surface']};alternate-background-color:{t['row_alt']};
                color:{t['text']};gridline-color:{t['border']};border:none;font-size:13px;}}
            QHeaderView::section{{background:{t['surface2']};color:{t['text']};padding:6px 10px;
                font-weight:700;font-size:12px;border:none;
                border-bottom:1px solid {t['border']};border-right:1px solid {t['border']};}}
            QTableWidget::item{{padding:4px 8px;}}
            QPushButton{{background:{t['accent']};color:white;border:none;border-radius:6px;
                padding:5px 14px;font-size:12px;font-weight:600;}}
            QPushButton:hover{{background:{t['accent']}dd;}}
            QPushButton#active_filter{{background:{t['positive']};}}
            QPushButton#red{{background:{t['negative']};}}
            QPushButton#red:hover{{background:#e05555;}}
            QLabel{{color:{t['text']};background:transparent;}}
        """)

        vl = QVBoxLayout(dlg); vl.setContentsMargins(14,14,14,14); vl.setSpacing(10)

        # Строка 1: баланс + кнопка очистить
        hdr = QHBoxLayout()
        bal = QLabel(f"Текущий баланс: {self.state['tugriki']} 💰")
        bal.setStyleSheet(f"font-size:15px;font-weight:700;color:{t['positive']};")
        hdr.addWidget(bal); hdr.addStretch()
        clr = QPushButton("Очистить историю"); clr.setObjectName("red"); clr.setFixedHeight(30)
        hdr.addWidget(clr); vl.addLayout(hdr)

        # Строка 2: фильтры
        flt = QHBoxLayout()
        btn_all = QPushButton("Все")
        btn_inc = QPushButton("Поступления")
        btn_dec = QPushButton("Списания")
        for b in [btn_all, btn_inc, btn_dec]:
            b.setFixedHeight(28)
            b.setCheckable(False)
            flt.addWidget(b)
        flt.addStretch()
        # Счётчики
        history = self.state.get("history", [])
        cnt_inc = sum(1 for e in history if str(e["amount"]).startswith("+"))
        cnt_dec = len(history) - cnt_inc
        btn_all.setText(f"Все ({len(history)})")
        btn_inc.setText(f"Поступления ({cnt_inc})")
        btn_dec.setText(f"Списания ({cnt_dec})")
        vl.addLayout(flt)

        # Таблица
        tbl = QTableWidget()
        tbl.setColumnCount(4)
        tbl.setHorizontalHeaderLabels(["Дата и время","Операция","Сумма","Баланс после"])
        h = tbl.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed); tbl.setColumnWidth(0,140)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed); tbl.setColumnWidth(2,90)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed); tbl.setColumnWidth(3,110)
        tbl.setAlternatingRowColors(True)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tbl.verticalHeader().setVisible(False)
        vl.addWidget(tbl)

        def fill_table(mode="all"):
            tbl.setRowCount(0)
            for entry in self.state.get("history", []):
                is_plus = str(entry["amount"]).startswith("+")
                if mode == "inc" and not is_plus: continue
                if mode == "dec" and is_plus: continue
                r = tbl.rowCount(); tbl.insertRow(r)
                amt_col = QColor(t["positive"]) if is_plus else QColor(t["negative"])
                for ci, key in enumerate(["date","desc","amount","balance"]):
                    val = str(entry.get(key,""))
                    item = QTableWidgetItem(val)
                    item.setForeground(amt_col if key=="amount" else QColor(t["text"]))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if key!="desc"
                                         else Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
                    if key == "amount":
                        item.setFont(_QF("Segoe UI", 10, 75))
                    tbl.setItem(r, ci, item)
            # Подсвечиваем активную кнопку
            active_style = f"background:{t['accent']}; color:white; border:none; border-radius:6px; padding:5px 14px; font-size:12px; font-weight:700;"
            normal_style = f"background:{t['surface2']}; color:{t['text']}; border:1px solid {t['border']}; border-radius:6px; padding:5px 14px; font-size:12px; font-weight:600;"
            btn_all.setStyleSheet(active_style if mode=="all" else normal_style)
            btn_inc.setStyleSheet(active_style if mode=="inc" else normal_style)
            btn_dec.setStyleSheet(active_style if mode=="dec" else normal_style)

        btn_all.clicked.connect(lambda: fill_table("all"))
        btn_inc.clicked.connect(lambda: fill_table("inc"))
        btn_dec.clicked.connect(lambda: fill_table("dec"))

        def do_clear():
            self._clear_history()
            bal.setText(f"Текущий баланс: {self.state['tugriki']} 💰")
            btn_all.setText("Все (0)"); btn_inc.setText("Поступления (0)"); btn_dec.setText("Списания (0)")
            fill_table("all")
        clr.clicked.connect(do_clear)

        fill_table("all")
        dlg.exec()

    def _refresh_history(self):
        # Обновляем баланс в топбаре
        if hasattr(self, "hist_bal_lbl"):
            self.hist_bal_lbl.setText(f"Баланс: {self.state['tugriki']} 💰")

    def _clear_history(self):
        self.state["history"] = []
        self._save()
        self._refresh_history()

    def _record_history(self, amount_str, description):
        from datetime import datetime
        if "history" not in self.state:
            self.state["history"] = []
        self.state["history"].insert(0, {
            "amount": amount_str,
            "desc":   description,
            "date":   datetime.now().strftime("%Y-%m-%d %H:%M"),
            "balance": self.state["tugriki"]
        })
        # Храним не более 200 записей
        self.state["history"] = self.state["history"][:200]

    def _buy(self,item):
        if self.state["tugriki"]>=item["price"]:
            self.state["tugriki"]-=item["price"]
            self.state["purchased"].append(item["name"])
            self._record_history(f'-{item["price"]}', f'Покупка: {item["name"]}')
            self._save(); self._update_tug(); self._refresh_inv()
            self._msg(self,"info","Куплено!",f"Вы приобрели: {item['name']}")
        else:
            self._msg(self,"warn","","Недостаточно тугриков!")

    def _inv_scroll_update_bg(self):
        from PyQt6.QtGui import QColor, QPalette
        bg = QColor(self.theme["bg"])
        for w in [self.inv_scroll, self.inv_scroll.viewport()]:
            pal = w.palette()
            pal.setColor(QPalette.ColorRole.Window, bg)
            pal.setColor(QPalette.ColorRole.Base, bg)
            w.setAutoFillBackground(True)
            w.setPalette(pal)

    def _refresh_inv(self):
        inner = QWidget()
        inner.setAutoFillBackground(True)
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(20,20,20,20)
        inner_lay.setAlignment(Qt.AlignmentFlag.AlignTop|Qt.AlignmentFlag.AlignHCenter)

        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setContentsMargins(0,0,0,0); grid.setSpacing(16)

        if not self.state["purchased"]:
            el = QLabel("Вы ещё ничего не купили")
            el.setAlignment(Qt.AlignmentFlag.AlignCenter)
            el.setStyleSheet(f"color:{self.theme['text_dim']};font-size:16px;")
            grid.addWidget(el, 0, 0, 1, 4)
        else:
            for i, name in enumerate(reversed(self.state["purchased"])):
                card = QFrame(); card.setObjectName("card"); card.setFixedSize(160,185)
                vl2 = QVBoxLayout(card); vl2.setAlignment(Qt.AlignmentFlag.AlignCenter)
                img = QLabel(); img.setAlignment(Qt.AlignmentFlag.AlignCenter)
                pix = self._get_pix(name)
                img.setPixmap(pix.scaled(90,90,Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation))
                vl2.addWidget(img)
                nl = QLabel(name); nl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                nl.setStyleSheet("font-weight:700;font-size:13px;")
                vl2.addWidget(nl)
                bl = QLabel("Куплено"); bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                bl.setStyleSheet(f"color:{self.theme['positive']};font-size:12px;font-weight:600;")
                vl2.addWidget(bl)
                grid.addWidget(card, i//4, i%4)

        inner_lay.addWidget(grid_w)
        from PyQt6.QtGui import QColor, QPalette
        bg = QColor(self.theme["bg"])
        for w in [inner]:
            pal = w.palette()
            pal.setColor(QPalette.ColorRole.Window, bg)
            pal.setColor(QPalette.ColorRole.Base, bg)
            w.setAutoFillBackground(True)
            w.setPalette(pal)
        self.inv_scroll.setWidget(inner)
        self._inv_scroll_update_bg()

    # ── КУБИК ───────────────────────────────────────────────────────────────
    def _build_dice(self):
        tab=QWidget(); self.tabs.addTab(tab,"Рандомайзер")
        root=QVBoxLayout(tab); root.setContentsMargins(10,10,10,10)

        # QSplitter — панели можно двигать мышью
        splitter=QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)
        splitter.setStyleSheet("""
            QSplitter::handle{background:#545454;border-radius:3px;}
            QSplitter::handle:hover{background:#5b7fc7;}
        """)
        root.addWidget(splitter)

        # ── Левая часть: кубик ──────────────────────────────────────────────
        wrap=QFrame(); wrap.setObjectName("card")
        vl=QVBoxLayout(wrap); vl.setContentsMargins(20,20,20,20); vl.setSpacing(6)
        vl.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Заголовок
        ttl=QLabel("Рандомайзер"); ttl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ttl.setStyleSheet("font-size:20px;font-weight:800;"); vl.addWidget(ttl)
        sub=QLabel("Бросьте кубик и получите случайное число")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"color:{self.theme['text_dim']};font-size:11px;")
        vl.addWidget(sub)

        vl.addSpacing(4)

        # Контейнер фиксированной ширины для обоих строк
        # Строка: От / До — по центру
        rr=QHBoxLayout(); rr.setContentsMargins(0,0,0,0); rr.setSpacing(8)
        rr.addStretch()
        rr.addWidget(QLabel("От:"))
        self.d_min=QLineEdit("1"); self.d_min.setFixedWidth(55); rr.addWidget(self.d_min)
        rr.addSpacing(12)
        rr.addWidget(QLabel("До:"))
        self.d_max=QLineEdit("10"); self.d_max.setFixedWidth(55); rr.addWidget(self.d_max)
        hint=QLabel("макс. 128"); hint.setStyleSheet(f"color:{self.theme['text_dim']};font-size:10px;")
        rr.addSpacing(8); rr.addWidget(hint)
        rr.addStretch()
        vl.addLayout(rr)

        # Строка: Исключить — по центру
        er=QHBoxLayout(); er.setContentsMargins(0,0,0,0); er.setSpacing(8)
        er.addStretch()
        er.addWidget(QLabel("Исключить:"))
        self.d_excl=QLineEdit(); self.d_excl.setPlaceholderText("3, 7, 9")
        self.d_excl.setFixedWidth(90); self.d_excl.returnPressed.connect(self._add_excl)
        er.addWidget(self.d_excl)
        eb=QPushButton("Добавить"); eb.setFixedHeight(28); eb.setFixedWidth(95)
        eb.setStyleSheet(f"background:{self.theme['accent']};color:white;border:none;border-radius:7px;font-size:12px;font-weight:600;")
        eb.clicked.connect(self._add_excl); er.addWidget(eb)
        clr_excl=QPushButton("Очистить"); clr_excl.setFixedHeight(28); clr_excl.setFixedWidth(90)
        clr_excl.setObjectName("outline"); clr_excl.clicked.connect(self._clear_excl)
        er.addWidget(clr_excl)
        er.addStretch()
        vl.addLayout(er)

        # Теги исключённых чисел
        self.tags_w=QWidget(); self.tags_w.setStyleSheet("background:transparent;")
        self.tags_lay=QHBoxLayout(self.tags_w)
        self.tags_lay.setContentsMargins(0,2,0,2); self.tags_lay.setSpacing(5)
        self.tags_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(self.tags_w)

        # Кубик
        self.dice=DiceWidget(); self.dice.update_theme(self.theme)
        vl.addWidget(self.dice, alignment=Qt.AlignmentFlag.AlignCenter)

        # Результат
        self.res_lbl=QLabel("")
        self.res_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.res_lbl.setStyleSheet(f"font-size:12px;color:{self.theme['text_dim']};")
        vl.addWidget(self.res_lbl)

        # Кнопка бросить
        self.roll_btn=QPushButton("Бросить кубик")
        self.roll_btn.setFixedWidth(200); self.roll_btn.setFixedHeight(42)
        self.roll_btn.setStyleSheet("font-size:14px;font-weight:700;border-radius:8px;")
        self.roll_btn.clicked.connect(self._start_roll)
        vl.addWidget(self.roll_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        splitter.addWidget(wrap)

        # ── Правая часть: история бросков ───────────────────────────────────
        hist_frame=QFrame(); hist_frame.setObjectName("card")
        hl=QVBoxLayout(hist_frame); hl.setContentsMargins(12,12,12,12); hl.setSpacing(8)

        hdr_row=QHBoxLayout()
        hdr_lbl=QLabel("История бросков")
        hdr_lbl.setStyleSheet("font-size:14px;font-weight:700;")
        hdr_row.addWidget(hdr_lbl); hdr_row.addStretch()
        clr_btn=QPushButton("Очистить"); clr_btn.setObjectName("outline")
        clr_btn.setFixedHeight(28); clr_btn.setFixedWidth(80); clr_btn.setStyleSheet('font-size:11px;padding:3px 6px;')
        clr_btn.clicked.connect(self._clear_dice_history)
        hdr_row.addWidget(clr_btn); hl.addLayout(hdr_row)

        self.dice_stats_lbl=QLabel("")
        self.dice_stats_lbl.setStyleSheet(f"color:{self.theme['text_dim']};font-size:11px;")
        hl.addWidget(self.dice_stats_lbl)

        sep=QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background:{self.theme['border']};max-height:1px;border:none;")
        hl.addWidget(sep)

        scroll=QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.dice_hist_inner=QWidget()
        self.dice_hist_inner.setStyleSheet("background:transparent;")
        self.dice_hist_lay=QVBoxLayout(self.dice_hist_inner)
        self.dice_hist_lay.setContentsMargins(0,0,0,0); self.dice_hist_lay.setSpacing(4)
        self.dice_hist_lay.addStretch()
        scroll.setWidget(self.dice_hist_inner)
        hl.addWidget(scroll)

        splitter.addWidget(hist_frame)

        # Начальные размеры — кубик 55%, история 45%
        splitter.setSizes([600, 500])

        # История хранится в памяти
        self.dice_history=[]



    def _add_dice_result(self, value):
        self.dice_history.append({"value": value, "note": ""})
        self._refresh_dice_history()

    def _refresh_dice_history(self):
        while self.dice_hist_lay.count() > 1:
            item = self.dice_hist_lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        total = len(self.dice_history)
        if total == 0:
            self.dice_stats_lbl.setText("Бросков: 0")
            return

        vals = [h["value"] for h in self.dice_history]
        self.dice_stats_lbl.setText(
            f"Бросков: {total}  |  Последнее: {vals[-1]}  |"
            f"  Среднее: {sum(vals)/total:.1f}  |  Мин: {min(vals)}  Макс: {max(vals)}"
        )

        for i, entry in enumerate(reversed(self.dice_history)):
            real_idx = total - 1 - i
            row = QFrame(); row.setObjectName("card")
            rl = QHBoxLayout(row); rl.setContentsMargins(8,5,8,5); rl.setSpacing(8)

            num_lbl = QLabel(f"#{real_idx+1}")
            num_lbl.setStyleSheet(f"color:{self.theme['text_dim']};font-size:11px;")
            num_lbl.setFixedWidth(32)

            val_lbl = QLabel(str(entry["value"]))
            val_lbl.setStyleSheet(f"color:{self.theme['accent']};font-size:16px;font-weight:800;")
            val_lbl.setFixedWidth(40)

            note_tf = QLineEdit(entry["note"])
            note_tf.setPlaceholderText("Описание...")
            def make_note(idx):
                def on_change(text): self.dice_history[idx]["note"] = text
                return on_change
            note_tf.textChanged.connect(make_note(real_idx))

            del_btn = QPushButton("✕"); del_btn.setFixedSize(22,22)
            del_btn.setStyleSheet(
                "QPushButton{background:transparent;border:none;color:#c75b5b;"
                "font-size:12px;font-weight:bold;}"
                "QPushButton:hover{color:#e05555;}"
            )
            def make_del(idx):
                def do():
                    self.dice_history.pop(idx)
                    self._refresh_dice_history()
                return do
            del_btn.clicked.connect(make_del(real_idx))

            rl.addWidget(num_lbl); rl.addWidget(val_lbl)
            rl.addWidget(note_tf, stretch=1); rl.addWidget(del_btn)
            self.dice_hist_lay.insertWidget(self.dice_hist_lay.count()-1, row)

    def _clear_dice_history(self):
        self.dice_history.clear()
        self._refresh_dice_history()

    def _add_excl(self):
        for p in self.d_excl.text().replace(";",",").split(","):
            try:
                n=int(p.strip())
                if n not in self.excl: self.excl.append(n)
            except: pass
        self.d_excl.clear(); self._refresh_tags()

    def _refresh_tags(self):
        while self.tags_lay.count():
            item=self.tags_lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for n in self.excl:
            tag=ExclTag(n, self.theme); tag.removed.connect(self._rm_excl)
            self.tags_lay.addWidget(tag)

    def _clear_excl(self):
        self.excl.clear()
        self._refresh_tags()

    def _rm_excl(self,n):
        if n in self.excl: self.excl.remove(n)
        self._refresh_tags()

    def _start_roll(self):
        try:
            a=int(self.d_min.text()); b=min(int(self.d_max.text()),128)
            self.d_max.setText(str(b))
            if a>b: a,b=b,a
            avail=[n for n in range(a,b+1) if n not in self.excl]
            if not avail: self._msg(self,"warn","","Все числа исключены!"); return
            self._dice_avail=avail; self._dice_frames=22; self._dice_delay=30
            self.roll_btn.setEnabled(False); self.res_lbl.setText("")
            self._dice_timer.start(self._dice_delay)
        except: self._msg(self,"error","Ошибка","Введите целые числа")

    def _dice_tick(self):
        if self._dice_frames>0:
            prog=(22-self._dice_frames)/22; scale=1.0+0.11*math.sin(prog*math.pi)
            cols=[self.theme["accent"],"#7090d8","#8a70c8","#6080b8"]
            self.dice.set_face(random.choice(self._dice_avail),cols[self._dice_frames%4],scale)
            self._dice_frames-=1; self._dice_delay+=int(170/(self._dice_frames+2))
            self._dice_timer.setInterval(self._dice_delay)
        else:
            self._dice_timer.stop(); self._bounce_val=random.choice(self._dice_avail)
            self._bounce_step=0; self._do_bounce()

    def _do_bounce(self):
        scales=[1.25,0.92,1.10,0.97,1.0]
        cols=[self.theme["positive"],"#5dcc8a",self.theme["positive"],"#3a9e6a",self.theme["positive"]]
        if self._bounce_step<len(scales):
            self.dice.set_face(self._bounce_val,cols[self._bounce_step],scales[self._bounce_step])
            self._bounce_step+=1; QTimer.singleShot(65,self._do_bounce)
        else:
            self.dice.set_face(self._bounce_val,self.theme["positive"],1.0)
            self.res_lbl.setText(f"Выпало: {self._bounce_val}  |  диапазон {self.d_min.text()}–{self.d_max.text()}")
            self.roll_btn.setEnabled(True)
            self._add_dice_result(self._bounce_val)
            QTimer.singleShot(2500,lambda: self.dice.set_face(self._bounce_val,self.theme["accent"],1.0))

    # ── СВОДКА ──────────────────────────────────────────────────────────────

    def _pick_date(self, target_field):
        """Открывает календарь и вставляет дату в target_field"""
        from PyQt6.QtWidgets import QCalendarWidget, QDialog, QVBoxLayout
        from PyQt6.QtCore import QDate
        dlg=QDialog(self); dlg.setWindowTitle("Выбор даты"); dlg.setFixedSize(300,220)
        t=self.theme
        dlg.setStyleSheet(f"""
            QDialog{{background:{t['surface']};color:{t['text']};}}
            QCalendarWidget{{background:{t['surface']};color:{t['text']};}}
            QCalendarWidget QAbstractItemView{{background:{t['surface2']};color:{t['text']};
                selection-background-color:{t['accent']};selection-color:white;}}
            QCalendarWidget QToolButton{{background:{t['surface2']};color:{t['text']};
                border-radius:4px;padding:3px 8px;}}
            QCalendarWidget QToolButton:hover{{background:{t['accent']};color:white;}}
            QCalendarWidget QWidget#qt_calendar_navigationbar{{background:{t['surface']};}}
            QCalendarWidget QSpinBox{{background:{t['surface2']};color:{t['text']};border:none;}}
        """)
        vl=QVBoxLayout(dlg); vl.setContentsMargins(4,4,4,4)
        cal=QCalendarWidget(); cal.setGridVisible(True)
        try:
            d=QDate.fromString(target_field.text().strip(),"yyyy-MM-dd")
            if d.isValid(): cal.setSelectedDate(d)
        except: pass
        def pick(date):
            target_field.setText(date.toString("yyyy-MM-dd")); dlg.accept()
        cal.clicked.connect(pick); vl.addWidget(cal); dlg.exec()

    def _on_quick_period(self, text):
        from datetime import date as _d, timedelta
        today=_d.today(); y=today.year
        try: y=int(self.sum_year.currentText())
        except: pass
        ranges={
            "1 квартал":    (_d(y,1,1),  _d(y,3,31)),
            "2 квартал":    (_d(y,4,1),  _d(y,6,30)),
            "3 квартал":    (_d(y,7,1),  _d(y,9,30)),
            "4 квартал":    (_d(y,10,1), _d(y,12,31)),
            "1 полугодие":  (_d(y,1,1),  _d(y,6,30)),
            "2 полугодие":  (_d(y,7,1),  _d(y,12,31)),
            "За год":       (_d(y,1,1),  _d(y,12,31)),
        }
        if text == "За всё время":
            self.sum_from.setText("2000-01-01")
            self.sum_to.setText(_d.today().isoformat())
        elif text in ranges:
            d_from, d_to = ranges[text]
            self.sum_from.setText(d_from.isoformat())
            self.sum_to.setText(d_to.isoformat())
        # Показывать/скрывать выбор года
        needs_year = any(text.startswith(q) for q in ["1 кв","2 кв","3 кв","4 кв","1 пол","2 пол","За год"])
        self.sum_year.setVisible(needs_year)

    def _refresh_summary(self):
        from datetime import date as _d
        t=self.theme
        try:
            d_from=_d.fromisoformat(self.sum_from.text().strip())
            d_to  =_d.fromisoformat(self.sum_to.text().strip())
        except:
            self._msg(self,"error","Ошибка","Неверный формат даты (гггг-мм-дд)"); return

        df=self.df.copy()
        if df.empty or "Date" not in df.columns:
            filtered=df
        else:
            df["_d"]=pd.to_datetime(df["Date"],errors="coerce").dt.date
            filtered=df[(df["_d"]>=d_from)&(df["_d"]<=d_to)].drop(columns=["_d"])

        # Статистика
        filtered["Amount"]=pd.to_numeric(filtered.get("Amount",0),errors="coerce").fillna(0)
        inc =filtered[filtered["Type"].astype(str).str.strip()=="Доход" ]["Amount"].sum()
        exp =filtered[filtered["Type"].astype(str).str.strip()=="Расход"]["Amount"].sum()
        bal =inc-exp

        def fmt(v): return f"{v:,.0f}"
        self.sv_income.setText(fmt(inc))
        self.sv_income.setStyleSheet(f"font-size:14px;font-weight:800;color:{t['positive']};")
        self.sv_expense.setText(fmt(exp))
        self.sv_expense.setStyleSheet(f"font-size:14px;font-weight:800;color:{t['negative']};")
        bal_col=t['positive'] if bal>=0 else t['negative']
        self.sv_balance.setText(fmt(bal))
        self.sv_balance.setStyleSheet(f"font-size:14px;font-weight:800;color:{bal_col};")
        # rows stat removed from toolbar

        # Таблица
        self.fin_tbl.setRowCount(0)
        for _,row in filtered.iterrows():
            r=self.fin_tbl.rowCount(); self.fin_tbl.insertRow(r)
            for ci,key in enumerate(["Date","Type","Category","Amount","Comment"]):
                val=str(row.get(key,"")) if pd.notna(row.get(key,"")) else ""
                item=QTableWidgetItem(val)
                if key=="Type":
                    item.setForeground(QColor(t["negative"]) if "расход" in val.lower()
                                       else QColor(t["positive"]) if "доход" in val.lower()
                                       else QColor(t["text"]))
                else: item.setForeground(QColor(t["text"]))
                self.fin_tbl.setItem(r,ci,item)

        # Графики
        self.pie_exp.plot(filtered, t)
        self.pie_inc.plot(filtered, t)




def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: pass
    return {"tasks":[],"tugriki":0,"purchased":[],"history":[]}


if __name__=="__main__":
    # Windows: устанавливаем AppUserModelID чтобы иконка отображалась в панели задач
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("tugrik.finance.app")
    except Exception:
        pass

    app=QApplication(sys.argv); app.setStyle("Fusion")
    import os as _os
    from PyQt6.QtGui import QIcon
    _ico = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "logo.ico")
    _png = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "Logo.png")
    icon = None
    if _os.path.exists(_ico):   icon = QIcon(_ico)
    elif _os.path.exists(_png): icon = QIcon(_png)
    if icon:
        app.setWindowIcon(icon)
    w=App(); w.show(); sys.exit(app.exec())
