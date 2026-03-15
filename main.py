import json, os, random, sys, math, io

import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QTabWidget,
    QFileDialog, QMessageBox, QScrollArea, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit,
    QGridLayout, QSizePolicy
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
    "dice_bg1": "#e0e0e0", "dice_bg2": "#cccccc",
}
PIE_COLORS = ["#5b7fc7","#e08040","#4caf7d","#9b59b6","#e74c3c","#1abc9c","#f1c40f","#e67e22"]
CATS_EXP = ["Продукты","Транспорт","Жилье","Здоровье","Развлечения","Досуг","Перевод","Наличка","Прочее"]
CATS_INC = ["Зарплата","Перевод","Наличка"]


class DiceWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(160, 160)
        self._value = "?"; self._color = QColor("#5b7fc7")
        self._scale = 1.0; self._bg1 = QColor("#484848"); self._bg2 = QColor("#333333")
        self.setAutoFillBackground(True)

    def update_theme(self, t):
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(t["surface"]))
        self.setPalette(pal)
        self._bg1 = QColor(t["dice_bg1"]); self._bg2 = QColor(t["dice_bg2"])
        self.update()

    def set_face(self, value, color, scale=1.0):
        self._value = str(value); self._color = QColor(color); self._scale = scale
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), self.palette().color(QPalette.ColorRole.Window))
        cx = cy = 80; h = int(58 * self._scale); r = h * 0.28
        p.setBrush(QBrush(QColor(0,0,0,55))); p.setPen(Qt.PenStyle.NoPen)
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
    def __init__(self, n, accent):
        super().__init__(); self.n = n
        lay = QHBoxLayout(self); lay.setContentsMargins(8,2,4,2); lay.setSpacing(4)
        self.setFixedHeight(26)
        lbl = QLabel(str(n)); lbl.setStyleSheet(f"color:{accent};font-weight:bold;font-size:12px;background:transparent;")
        btn = QPushButton("✕"); btn.setFixedSize(16,16)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("QPushButton{background:transparent;border:none;}QPushButton:hover{color:white;}")
        btn.clicked.connect(lambda: self.removed.emit(self.n))
        lay.addWidget(lbl); lay.addWidget(btn)
        self.setStyleSheet(f"QFrame{{background:{accent}28;border-radius:11px;border:1px solid {accent}55;}}")


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

    def plot(self, df, theme):
        self._theme = theme; self._data = []
        pal = ["#5b7fc7","#e08040","#4caf7d","#9b59b6","#e74c3c","#1abc9c","#f1c40f","#e67e22"] \
              if self.entry_type=="Расход" else \
              ["#4caf7d","#2e86ab","#74c69d","#457b9d","#52b788","#a8dadc","#1d3557"]
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
        self.resize(1350,860)
        self.is_dark=True; self.theme=DARK
        self.csv_path=None
        self.df=pd.DataFrame(columns=["Date","Type","Category","Amount","Comment"])
        self.state=load_data()
        self.excl=[]
        self.image_cache={}
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

    # ── тема ────────────────────────────────────────────────────────────────
    def _apply_theme(self):
        t=self.theme
        self.setStyleSheet(f"""
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
            QPushButton#outline{{background:transparent;border:1.5px solid {t['accent']};color:{t['accent']};}}
            QPushButton#outline:hover{{background:{t['accent']}18;}}
            QPushButton#red{{background:#c75b5b;color:white;}}
            QPushButton#red:hover{{background:#e05555;}}
            QLineEdit,QComboBox,QDateEdit{{background:{t['surface2']};border:1px solid {t['border']};
                border-radius:6px;padding:5px 10px;color:{t['text']};font-size:13px;}}
            QLineEdit:focus,QComboBox:focus,QDateEdit:focus{{border-color:{t['accent']};}}
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
        """)
        if hasattr(self,"tug_lbl"):
            self.tug_lbl.setStyleSheet(f"color:{t['positive']};font-size:19px;font-weight:800;background:transparent;")
        if hasattr(self,"dice"): self.dice.update_theme(t)
        if hasattr(self,"pie_exp"): self.pie_exp.plot(self.df,t)
        if hasattr(self,"pie_inc"): self.pie_inc.plot(self.df,t)
        if hasattr(self,"theme_btn"):
            self.theme_btn.setText("☀️ Светлая" if self.is_dark else "🌙 Тёмная")

    def _toggle_theme(self):
        self.is_dark=not self.is_dark; self.theme=DARK if self.is_dark else LIGHT
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
        b=QPushButton("📂 Открыть CSV"); b.clicked.connect(self._open_csv); tl.addWidget(b)
        b2=QPushButton("➕ Создать CSV"); b2.setObjectName("outline")
        b2.clicked.connect(self._create_csv); tl.addWidget(b2)
        tl.addStretch()
        self.theme_btn=QPushButton("☀️ Светлая"); self.theme_btn.setObjectName("outline")
        self.theme_btn.setFixedWidth(120); self.theme_btn.clicked.connect(self._toggle_theme)
        tl.addWidget(self.theme_btn); tl.addSpacing(14)
        self.tug_lbl=QLabel(f"Тугрики: {self.state['tugriki']} 💰")
        tl.addWidget(self.tug_lbl); root.addWidget(tb)

        self.tabs=QTabWidget(); self.tabs.setDocumentMode(False)
        root.addWidget(self.tabs)
        self._build_finance(); self._build_tasks()
        self._build_shop();    self._build_dice()

    # ── ФИНАНСЫ ─────────────────────────────────────────────────────────────
    def _build_finance(self):
        tab=QWidget(); self.tabs.addTab(tab,"Финансы")
        lay=QHBoxLayout(tab); lay.setContentsMargins(10,10,10,10); lay.setSpacing(12)

        form=QFrame(); form.setObjectName("card"); form.setFixedWidth(258)
        fl=QVBoxLayout(form); fl.setContentsMargins(14,14,14,14); fl.setSpacing(9)
        lh=QLabel("Добавить запись"); lh.setStyleSheet("font-size:14px;font-weight:700;")
        fl.addWidget(lh)
        self.f_type=QComboBox(); self.f_type.addItems(["Расход","Доход"])
        self.f_type.currentTextChanged.connect(self._update_cats); fl.addWidget(self.f_type)
        dr=QHBoxLayout(); dr.setSpacing(6); dr.addWidget(QLabel("Дата:"))
        self.f_date=QDateEdit(QDate.currentDate())
        self.f_date.setCalendarPopup(True); self.f_date.setDisplayFormat("yyyy-MM-dd")
        dr.addWidget(self.f_date); fl.addLayout(dr)
        self.f_cat=QComboBox(); self._update_cats(); fl.addWidget(self.f_cat)
        self.f_amt=QLineEdit(); self.f_amt.setPlaceholderText("Сумма"); fl.addWidget(self.f_amt)
        self.f_com=QLineEdit(); self.f_com.setPlaceholderText("Комментарий"); fl.addWidget(self.f_com)
        sb=QPushButton("💾 Сохранить в CSV"); sb.clicked.connect(self._add_row); fl.addWidget(sb)
        fl.addStretch(); lay.addWidget(form)

        tf=QFrame(); tf.setObjectName("card")
        tfl=QVBoxLayout(tf); tfl.setContentsMargins(0,0,0,0)
        bar=QWidget(); bl=QHBoxLayout(bar); bl.setContentsMargins(8,6,8,4); bl.setSpacing(8)
        db=QPushButton("🗑 Удалить выбранную строку"); db.setObjectName("red")
        db.setFixedHeight(30); db.clicked.connect(self._del_row); bl.addWidget(db)
        bl.addStretch()
        hint=QLabel("Выберите строку и нажмите Удалить")
        hint.setStyleSheet(f"color:{self.theme['text_dim']};font-size:11px;")
        bl.addWidget(hint); tfl.addWidget(bar)

        self.fin_tbl=QTableWidget()
        self.fin_tbl.setColumnCount(5)
        self.fin_tbl.setHorizontalHeaderLabels(["Дата","Тип","Категория","Сумма","Комментарий"])
        self.fin_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.fin_tbl.setAlternatingRowColors(True)
        self.fin_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.fin_tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.fin_tbl.verticalHeader().setVisible(False)
        tfl.addWidget(self.fin_tbl); lay.addWidget(tf,stretch=2)

        charts=QWidget(); cl=QVBoxLayout(charts); cl.setContentsMargins(0,0,0,0); cl.setSpacing(8)
        cf1=QFrame(); cf1.setObjectName("card"); cfl1=QVBoxLayout(cf1); cfl1.setContentsMargins(6,6,6,6)
        self.pie_exp=PieWidget("Расход"); cfl1.addWidget(self.pie_exp); cl.addWidget(cf1,stretch=1)
        cf2=QFrame(); cf2.setObjectName("card"); cfl2=QVBoxLayout(cf2); cfl2.setContentsMargins(6,6,6,6)
        self.pie_inc=PieWidget("Доход");  cfl2.addWidget(self.pie_inc); cl.addWidget(cf2,stretch=1)
        lay.addWidget(charts,stretch=1)

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

    def _refresh_charts(self):
        self.pie_exp.plot(self.df,self.theme)
        self.pie_inc.plot(self.df,self.theme)

    def _add_row(self):
        if not self.csv_path:
            QMessageBox.warning(self,"Внимание","Сначала выберите или создайте CSV файл!"); return
        try: amt=float(self.f_amt.text().replace(",","."))
        except: QMessageBox.critical(self,"Ошибка","Сумма должна быть числом!"); return
        nr={"Date":self.f_date.date().toString("yyyy-MM-dd"),"Type":self.f_type.currentText(),
            "Category":self.f_cat.currentText(),"Amount":amt,"Comment":self.f_com.text()}
        self.df=pd.concat([self.df,pd.DataFrame([nr])],ignore_index=True)
        self.df.to_csv(self.csv_path,index=False,encoding="utf-8-sig")
        self.f_amt.clear(); self.f_com.clear()
        self._refresh_tbl(); self._refresh_charts()

    def _del_row(self):
        rows=self.fin_tbl.selectionModel().selectedRows()
        if not rows: QMessageBox.information(self,"","Выберите строку."); return
        idx=rows[0].row()
        msg=QMessageBox(self); msg.setWindowTitle("Подтверждение")
        msg.setText(f"Удалить строку {idx+1}?"); msg.setIcon(QMessageBox.Icon.Question)
        yes=msg.addButton("Да",QMessageBox.ButtonRole.YesRole)
        msg.addButton("Нет",QMessageBox.ButtonRole.NoRole); msg.exec()
        if msg.clickedButton()==yes:
            self.df=self.df.drop(index=idx).reset_index(drop=True)
            if self.csv_path: self.df.to_csv(self.csv_path,index=False,encoding="utf-8-sig")
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
        ab=QPushButton("＋ Добавить"); ab.clicked.connect(self._add_task)
        self.t_name.returnPressed.connect(self._add_task); il.addWidget(ab); il.addStretch()
        vl.addWidget(inp)
        lim=QLabel(f"Максимальная награда: {MAX_REWARD} тугриков")
        lim.setStyleSheet("color:#999;font-size:11px;"); vl.addWidget(lim)
        cols=QHBoxLayout(); cols.setSpacing(12)
        self.a_col,self.a_lay=self._task_col("🔥 Активные задачи")
        self.d_col,self.d_lay=self._task_col("✅ Выполненные")
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
                QMessageBox.warning(self,"",f"Награда от 1 до {MAX_REWARD}."); return
        except ValueError:
            QMessageBox.critical(self,"Ошибка","Заполните название и награду (целое число)."); return
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
                btn=QPushButton("✔ Выполнено")
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
        self.state["tugriki"]+=self.state["tasks"][idx]["reward"]
        self.state["tasks"][idx]["done"]=True
        self._save(); self._update_tug(); self._refresh_tasks()

    # ── МАГАЗИН ─────────────────────────────────────────────────────────────
    def _build_shop(self):
        tab=QWidget(); self.tabs.addTab(tab,"Магазин")
        vl=QVBoxLayout(tab); vl.setContentsMargins(12,12,12,12)
        it=QTabWidget(); vl.addWidget(it)
        sw=QWidget(); self._build_store(sw); it.addTab(sw,"Витрина")
        self.inv_w=QWidget(); it.addTab(self.inv_w,"Приобретённое")
        self._refresh_inv()

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
            btn=QPushButton("🛒  Купить"); btn.setFixedWidth(140); btn.setFixedHeight(36)
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

    def _buy(self,item):
        if self.state["tugriki"]>=item["price"]:
            self.state["tugriki"]-=item["price"]
            self.state["purchased"].append(item["name"])
            self._save(); self._update_tug(); self._refresh_inv()
            QMessageBox.information(self,"🎉 Куплено!",f"Вы приобрели: {item['name']}")
        else:
            QMessageBox.warning(self,"","Недостаточно тугриков!")

    def _refresh_inv(self):
        old=self.inv_w.layout()
        if old:
            while old.count():
                w=old.takeAt(0)
                if w.widget(): w.widget().deleteLater()
            old.deleteLater()
        scroll=QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        inner=QWidget(); inner.setStyleSheet("background:transparent;")
        outer_lay=QVBoxLayout(inner); outer_lay.setContentsMargins(20,20,20,20)
        outer_lay.setAlignment(Qt.AlignmentFlag.AlignTop|Qt.AlignmentFlag.AlignHCenter)
        grid_w=QWidget(); grid_w.setStyleSheet("background:transparent;")
        grid=QGridLayout(grid_w); grid.setContentsMargins(0,0,0,0); grid.setSpacing(16)
        if not self.state["purchased"]:
            el=QLabel("Вы ещё ничего не купили 😢")
            el.setAlignment(Qt.AlignmentFlag.AlignCenter)
            el.setStyleSheet(f"color:{self.theme['text_dim']};font-size:16px;")
            grid.addWidget(el,0,0,1,4)
        else:
            for i,name in enumerate(reversed(self.state["purchased"])):
                card=QFrame(); card.setObjectName("card"); card.setFixedSize(160,185)
                vl2=QVBoxLayout(card); vl2.setAlignment(Qt.AlignmentFlag.AlignCenter)
                img=QLabel(); img.setAlignment(Qt.AlignmentFlag.AlignCenter)
                pix=self._get_pix(name)
                img.setPixmap(pix.scaled(90,90,Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation))
                vl2.addWidget(img)
                nl=QLabel(name); nl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                nl.setStyleSheet("font-weight:700;font-size:13px;"); vl2.addWidget(nl)
                bl=QLabel("Куплено ✓"); bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                bl.setStyleSheet(f"color:{self.theme['positive']};font-size:12px;font-weight:600;")
                vl2.addWidget(bl); grid.addWidget(card,i//4,i%4)
        outer_lay.addWidget(grid_w); scroll.setWidget(inner)
        pl=QVBoxLayout(self.inv_w); pl.setContentsMargins(0,0,0,0); pl.addWidget(scroll)

    # ── КУБИК ───────────────────────────────────────────────────────────────
    def _build_dice(self):
        tab=QWidget(); self.tabs.addTab(tab,"Кубик")
        outer=QVBoxLayout(tab); outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wrap=QFrame(); wrap.setObjectName("card"); wrap.setFixedWidth(520)
        vl=QVBoxLayout(wrap); vl.setContentsMargins(30,28,30,28); vl.setSpacing(12)
        vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ttl=QLabel("🎲 Рандомайзер"); ttl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ttl.setStyleSheet("font-size:22px;font-weight:800;"); vl.addWidget(ttl)
        sub=QLabel("Бросьте кубик и получите случайное число")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"color:{self.theme['text_dim']};font-size:12px;"); vl.addWidget(sub)

        rr=QHBoxLayout(); rr.setAlignment(Qt.AlignmentFlag.AlignCenter); rr.setSpacing(6)
        rr.addWidget(QLabel("От:"))
        self.d_min=QLineEdit("1"); self.d_min.setFixedWidth(60); rr.addWidget(self.d_min)
        rr.addSpacing(12); rr.addWidget(QLabel("До:"))
        self.d_max=QLineEdit("10"); self.d_max.setFixedWidth(60); rr.addWidget(self.d_max)
        hint=QLabel("(макс. 128)"); hint.setStyleSheet(f"color:{self.theme['text_dim']};font-size:11px;")
        rr.addSpacing(6); rr.addWidget(hint); vl.addLayout(rr)

        er=QHBoxLayout(); er.setAlignment(Qt.AlignmentFlag.AlignCenter); er.setSpacing(6)
        er.addWidget(QLabel("Исключить:"))
        self.d_excl=QLineEdit(); self.d_excl.setPlaceholderText("напр: 3, 7, 9")
        self.d_excl.setFixedWidth(140); self.d_excl.returnPressed.connect(self._add_excl)
        er.addWidget(self.d_excl)
        eb=QPushButton("Добавить"); eb.setFixedWidth(90); eb.clicked.connect(self._add_excl)
        er.addWidget(eb); vl.addLayout(er)

        self.tags_w=QWidget(); self.tags_lay=QHBoxLayout(self.tags_w)
        self.tags_lay.setContentsMargins(0,0,0,0); self.tags_lay.setSpacing(5)
        self.tags_lay.setAlignment(Qt.AlignmentFlag.AlignCenter); vl.addWidget(self.tags_w)

        self.dice=DiceWidget(); self.dice.update_theme(self.theme)
        vl.addWidget(self.dice,alignment=Qt.AlignmentFlag.AlignCenter)

        self.res_lbl=QLabel(""); self.res_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.res_lbl.setStyleSheet(f"font-size:13px;color:{self.theme['text_dim']};"); vl.addWidget(self.res_lbl)

        self.roll_btn=QPushButton("🎲 Бросить кубик"); self.roll_btn.setFixedWidth(210)
        self.roll_btn.setFixedHeight(44)
        self.roll_btn.setStyleSheet("font-size:15px;font-weight:700;border-radius:8px;")
        self.roll_btn.clicked.connect(self._start_roll); vl.addWidget(self.roll_btn,alignment=Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(wrap)

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
            tag=ExclTag(n,self.theme["accent"]); tag.removed.connect(self._rm_excl)
            self.tags_lay.addWidget(tag)

    def _rm_excl(self,n):
        if n in self.excl: self.excl.remove(n)
        self._refresh_tags()

    def _start_roll(self):
        try:
            a=int(self.d_min.text()); b=min(int(self.d_max.text()),128)
            self.d_max.setText(str(b))
            if a>b: a,b=b,a
            avail=[n for n in range(a,b+1) if n not in self.excl]
            if not avail: QMessageBox.warning(self,"","Все числа исключены!"); return
            self._dice_avail=avail; self._dice_frames=22; self._dice_delay=30
            self.roll_btn.setEnabled(False); self.res_lbl.setText("")
            self._dice_timer.start(self._dice_delay)
        except: QMessageBox.critical(self,"Ошибка","Введите целые числа")

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
            QTimer.singleShot(2500,lambda: self.dice.set_face(self._bounce_val,self.theme["accent"],1.0))


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: pass
    return {"tasks":[],"tugriki":0,"purchased":[]}


if __name__=="__main__":
    app=QApplication(sys.argv); app.setStyle("Fusion")
    w=App(); w.show(); sys.exit(app.exec())