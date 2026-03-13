import csv
import json
import os
import random
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import customtkinter as ctk
from tkcalendar import DateEntry
from PIL import Image, ImageDraw

# Настройки темы
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Файл для хранения Тугриков и Списка задач
DATA_FILE = "app_internal_data.json"
IMAGES_DIR = "images"

# Создаем папку для картинок магазина, если ее нет
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)


class FinanceApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Управление финансами и Тугрики")
        self.geometry("1350x850")
        self._current_theme = "Dark"
        self.configure(bg="#1a1a1a")

        # Переменные данных
        self.current_csv_path = None
        self.operations = []
        self.tasks = []
        self.purchased_items = []  # Новый список для покупок
        self.tugriki = 0

        # Наполнение магазина
        self.shop_items = [
            {"name": "Вечер кино", "price": 50},
            {"name": "Вкусный ужин", "price": 150},
            {"name": "Выходной от дел", "price": 500},
            {"name": "Подарок себе", "price": 1000}
        ]

        # Кэш для картинок, чтобы они не удалялись сборщиком мусора
        self.image_cache = {}

        self._load_internal_data()
        self._setup_styles()
        self._build_ui()

    # ================= ЛОГИКА ФАЙЛОВ И ДАННЫХ =================

    def _load_internal_data(self):
        """Загрузка задач, баланса и покупок"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.tasks = data.get("tasks", [])
                    self.tugriki = data.get("tugriki", 0)
                    self.purchased_items = data.get("purchased", [])
            except:
                pass

    def _save_internal_data(self):
        """Сохранение задач, баланса и покупок"""
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "tasks": self.tasks,
                "tugriki": self.tugriki,
                "purchased": self.purchased_items
            }, f, ensure_ascii=False, indent=2)

    def _select_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV файлы", "*.csv")])
        if path:
            self.current_csv_path = path
            self.lbl_file_path.configure(text=f"Файл: {os.path.basename(path)}")
            self._refresh_table_from_csv()

    def _create_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV файлы", "*.csv")])
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Type", "Category", "Amount", "Comment"])
            self.current_csv_path = path
            self.lbl_file_path.configure(text=f"Файл: {os.path.basename(path)}")
            self._refresh_table_from_csv()

    def _refresh_table_from_csv(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        if not self.current_csv_path: return

        try:
            with open(self.current_csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.tree.insert("", "end",
                                     values=(row["Date"], row["Type"], row["Category"], row["Amount"], row["Comment"]))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл: {e}")

    # ================= УТИЛИТЫ ДЛЯ КАРТИНОК =================

    def _get_shop_image(self, item_name):
        """Пытается загрузить картинку, если ее нет - рисует цветной квадрат-заглушку"""
        if item_name in self.image_cache:
            return self.image_cache[item_name]

        img_path = os.path.join(IMAGES_DIR, f"{item_name}.png")
        if os.path.exists(img_path):
            img = Image.open(img_path)
        else:
            # Создаем заглушку
            img = Image.new('RGB', (120, 120),
                            color=(random.randint(40, 100), random.randint(40, 100), random.randint(60, 150)))
            d = ImageDraw.Draw(img)
            # Рисуем первую букву названия для красоты
            d.text((45, 45), item_name[0].upper(), fill=(255, 255, 255))

        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(120, 120))
        self.image_cache[item_name] = ctk_img
        return ctk_img

    # ================= ИНТЕРФЕЙС =================

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", borderwidth=0)
        style.configure("Treeview.Heading", background="#1f538d", foreground="white", relief="flat")
        style.map("Treeview", background=[('selected', '#1f538d')])

    def _build_ui(self):
        top_panel = ctk.CTkFrame(self, height=70)
        top_panel.pack(side=tk.TOP, fill=tk.X, padx=20, pady=10)

        self.lbl_file_path = ctk.CTkLabel(top_panel, text="Файл не выбран", font=("Roboto", 12, "italic"))
        self.lbl_file_path.pack(side=tk.LEFT, padx=15)

        ctk.CTkButton(top_panel, text="Открыть CSV", width=110, command=self._select_csv).pack(side=tk.LEFT, padx=5)
        ctk.CTkButton(top_panel, text="Создать CSV", width=110, fg_color="transparent", border_width=1,
                      command=self._create_csv).pack(side=tk.LEFT, padx=5)

        self.tugriki_var = tk.StringVar(value=f"Тугрики: {self.tugriki} 💰")
        ctk.CTkLabel(top_panel, textvariable=self.tugriki_var, font=("Roboto", 20, "bold"), text_color="#facc15").pack(
            side=tk.RIGHT, padx=20)

        self.theme_btn = ctk.CTkButton(top_panel, text="☀️ Светлая", width=120, fg_color="transparent",
                                       border_width=1, command=self._toggle_theme)
        self.theme_btn.pack(side=tk.RIGHT, padx=5)

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        self.tabs.add("Финансы")
        self.tabs.add("Задачи")
        self.tabs.add("Магазин")
        self.tabs.add("Кубик")

        self._init_finance_tab()
        self._init_tasks_tab()
        self._init_shop_tab()
        self._init_dice_tab()

    def _toggle_theme(self):
        if self._current_theme == "Dark":
            self._current_theme = "Light"
            ctk.set_appearance_mode("Light")
            self.configure(bg="#ebebeb")
            self.theme_btn.configure(text="🌙 Тёмная")
        else:
            self._current_theme = "Dark"
            ctk.set_appearance_mode("Dark")
            self.configure(bg="#1a1a1a")
            self.theme_btn.configure(text="☀️ Светлая")

    # --- ВКЛАДКА ФИНАНСЫ ---
    def _init_finance_tab(self):
        tab = self.tabs.tab("Финансы")
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        form = ctk.CTkFrame(tab, width=300)
        form.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(form, text="Добавить запись", font=("Roboto", 16, "bold")).pack(pady=10)

        self.f_type = ctk.CTkOptionMenu(form, values=["Расход", "Доход"])
        self.f_type.pack(fill=tk.X, padx=15, pady=5)

        date_f = ctk.CTkFrame(form, fg_color="transparent")
        date_f.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(date_f, text="Дата:").pack(side=tk.LEFT)
        self.f_date = DateEntry(date_f, background='#1f538d', foreground='white', date_pattern='yyyy-mm-dd')
        self.f_date.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))

        self.f_cat = ctk.CTkOptionMenu(form,
                                       values=["Продукты", "Транспорт", "Жилье", "Здоровье", "Развлечения", "Зарплата"])
        self.f_cat.pack(fill=tk.X, padx=15, pady=5)

        self.f_amt = ctk.CTkEntry(form, placeholder_text="Сумма")
        self.f_amt.pack(fill=tk.X, padx=15, pady=5)

        self.f_comm = ctk.CTkEntry(form, placeholder_text="Комментарий")
        self.f_comm.pack(fill=tk.X, padx=15, pady=5)

        ctk.CTkButton(form, text="Сохранить в CSV", command=self._add_finance_to_csv).pack(fill=tk.X, padx=15, pady=20)

        table_fr = ctk.CTkFrame(tab)
        table_fr.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        cols = ("Date", "Type", "Category", "Amount", "Comment")
        self.tree = ttk.Treeview(table_fr, columns=cols, show="headings")
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _add_finance_to_csv(self):
        if not self.current_csv_path:
            messagebox.showwarning("Внимание", "Сначала выберите или создайте CSV файл!")
            return

        try:
            amt = float(self.f_amt.get())
            row = [self.f_date.get(), self.f_type.get(), self.f_cat.get(), amt, self.f_comm.get()]
            with open(self.current_csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(row)

            self._refresh_table_from_csv()
            self.f_amt.delete(0, 'end');
            self.f_comm.delete(0, 'end')
        except ValueError:
            messagebox.showerror("Ошибка", "Сумма должна быть числом!")

    # --- ВКЛАДКА ЗАДАЧИ ---
    def _init_tasks_tab(self):
        tab = self.tabs.tab("Задачи")

        input_fr = ctk.CTkFrame(tab)
        input_fr.pack(fill=tk.X, padx=20, pady=10)

        self.t_name = ctk.CTkEntry(input_fr, placeholder_text="Название задачи...", width=400)
        self.t_name.pack(side=tk.LEFT, padx=10, pady=10)

        self.t_rew = ctk.CTkEntry(input_fr, placeholder_text="Награда", width=80)
        self.t_rew.pack(side=tk.LEFT, padx=5, pady=10)

        ctk.CTkButton(input_fr, text="Добавить", width=100, command=self._add_task).pack(side=tk.LEFT, padx=10)

        # Контейнер для двух списков (Активные и Выполненные)
        lists_fr = ctk.CTkFrame(tab, fg_color="transparent")
        lists_fr.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.tasks_active_container = ctk.CTkScrollableFrame(lists_fr, label_text="🔥 Активные задачи")
        self.tasks_active_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.tasks_done_container = ctk.CTkScrollableFrame(lists_fr, label_text="✅ Выполненные")
        self.tasks_done_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        self._refresh_task_list()

    def _add_task(self):
        name = self.t_name.get().strip()
        try:
            rew = int(self.t_rew.get())
            if not name: raise ValueError
            self.tasks.append({"title": name, "reward": rew, "done": False})
            self._save_internal_data()
            self._refresh_task_list()
            self.t_name.delete(0, 'end');
            self.t_rew.delete(0, 'end')
        except:
            messagebox.showerror("Ошибка", "Заполните название и награду (число)")

    def _refresh_task_list(self):
        # Очищаем оба списка
        for w in self.tasks_active_container.winfo_children(): w.destroy()
        for w in self.tasks_done_container.winfo_children(): w.destroy()

        for i, t in enumerate(self.tasks):
            if not t.get("done"):
                # Активная задача
                f = ctk.CTkFrame(self.tasks_active_container)
                f.pack(fill=tk.X, pady=3, padx=5)
                ctk.CTkLabel(f, text=f"🎯 {t['title']}").pack(side=tk.LEFT, padx=15)
                ctk.CTkLabel(f, text=f"+{t['reward']} 💰", text_color="#facc15").pack(side=tk.LEFT)
                ctk.CTkButton(f, text="Выполнено", width=80, fg_color="#10b981", hover_color="#059669",
                              command=lambda idx=i: self._complete_task(idx)).pack(side=tk.RIGHT, padx=5)
            else:
                # Выполненная задача
                f = ctk.CTkFrame(self.tasks_done_container, fg_color="#1f2937")
                f.pack(fill=tk.X, pady=3, padx=5)
                ctk.CTkLabel(f, text=f"<s>{t['title']}</s>", text_color="#9ca3af").pack(side=tk.LEFT, padx=15)
                ctk.CTkLabel(f, text=f"Получено: {t['reward']} 💰", text_color="#6ee7b7").pack(side=tk.RIGHT, padx=15)

    def _complete_task(self, idx):
        self.tugriki += self.tasks[idx]["reward"]
        self.tasks[idx]["done"] = True
        self.tugriki_var.set(f"Тугрики: {self.tugriki} 💰")
        self._save_internal_data()
        self._refresh_task_list()

    # --- ВКЛАДКА МАГАЗИН ---
    def _init_shop_tab(self):
        tab = self.tabs.tab("Магазин")

        shop_tabs = ctk.CTkTabview(tab)
        shop_tabs.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        t_store = shop_tabs.add("Витрина")
        t_inventory = shop_tabs.add("Приобретённое")

        # --- Витрина ---
        grid = ctk.CTkScrollableFrame(t_store, fg_color="transparent")
        grid.pack(fill=tk.BOTH, expand=True)

        # Центрируем колонки с карточками
        num_cols = 3
        for c in range(num_cols):
            grid.grid_columnconfigure(c, weight=1)

        for i, item in enumerate(self.shop_items):
            card = ctk.CTkFrame(grid, width=220, height=250)
            card.grid(row=i // 3, column=i % 3, padx=15, pady=15)
            card.grid_propagate(False)

            # Картинка
            img = self._get_shop_image(item["name"])
            ctk.CTkLabel(card, text="", image=img).pack(pady=(15, 5))

            ctk.CTkLabel(card, text=item["name"], font=("Roboto", 15, "bold")).pack()
            ctk.CTkLabel(card, text=f"{item['price']} 💰", text_color="#facc15", font=("Roboto", 14)).pack()

            ctk.CTkButton(card, text="Купить", width=120,
                          command=lambda it=item: self._buy_reward(it)).pack(side=tk.BOTTOM, pady=15)

        # --- Инвентарь ---
        self.inventory_container = ctk.CTkScrollableFrame(t_inventory, fg_color="transparent")
        self.inventory_container.pack(fill=tk.BOTH, expand=True)
        self._refresh_inventory()

    def _buy_reward(self, item):
        if self.tugriki >= item["price"]:
            self.tugriki -= item["price"]
            self.purchased_items.append(item["name"])  # Добавляем в инвентарь
            self.tugriki_var.set(f"Тугрики: {self.tugriki} 💰")
            self._save_internal_data()
            self._refresh_inventory()
            messagebox.showinfo("Поздравляем!", f"Вы приобрели: {item['name']}")
        else:
            messagebox.showwarning("Эх...", "Недостаточно тугриков. Время поработать!")

    def _refresh_inventory(self):
        for w in self.inventory_container.winfo_children(): w.destroy()

        if not self.purchased_items:
            ctk.CTkLabel(self.inventory_container, text="Вы пока ничего не купили 😢", text_color="#9ca3af",
                         font=("Roboto", 16)).pack(pady=50)
            return

        for i, item_name in enumerate(reversed(self.purchased_items)):  # Показываем новые сверху
            card = ctk.CTkFrame(self.inventory_container, width=150, height=180)
            card.grid(row=i // 4, column=i % 4, padx=15, pady=15)
            card.grid_propagate(False)

            img = self._get_shop_image(item_name)
            ctk.CTkLabel(card, text="", image=img).pack(pady=(15, 5))
            ctk.CTkLabel(card, text=item_name, font=("Roboto", 13, "bold")).pack()
            ctk.CTkLabel(card, text="Куплено ✔️", text_color="#10b981").pack(side=tk.BOTTOM, pady=10)

        # --- ВКЛАДКА КУБИК ---
    def _init_dice_tab(self):
        tab = self.tabs.tab("Кубик")

        center_frame = ctk.CTkFrame(tab, fg_color="transparent")
        center_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        ctk.CTkLabel(center_frame, text="🎲 Рандомайзер", font=("Roboto", 24, "bold")).pack(pady=(0, 15))

        # Диапазон
        input_f = ctk.CTkFrame(center_frame, fg_color="transparent")
        input_f.pack()

        ctk.CTkLabel(input_f, text="От:").grid(row=0, column=0, padx=5)
        self.d_min = ctk.CTkEntry(input_f, width=60)
        self.d_min.insert(0, "1")
        self.d_min.grid(row=0, column=1)

        ctk.CTkLabel(input_f, text="До:").grid(row=0, column=2, padx=5)
        self.d_max = ctk.CTkEntry(input_f, width=60)
        self.d_max.insert(0, "10")
        self.d_max.grid(row=0, column=3)

        # Исключения
        excl_f = ctk.CTkFrame(center_frame, fg_color="transparent")
        excl_f.pack(pady=(10, 0))
        ctk.CTkLabel(excl_f, text="Исключить числа:", font=("Roboto", 13)).pack(side=tk.LEFT, padx=(0, 8))
        self.d_excl = ctk.CTkEntry(excl_f, width=140, placeholder_text="напр: 3, 7, 9")
        self.d_excl.pack(side=tk.LEFT)
        ctk.CTkButton(excl_f, text="+ Добавить", width=90, height=28,
                      command=self._add_excl_tag).pack(side=tk.LEFT, padx=(8, 0))

        # Теги исключённых чисел
        self.excl_tags_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        self.excl_tags_frame.pack(pady=(6, 0))

        app_bg = "#1a1a1a"
        self.dice_label = ctk.CTkLabel(center_frame, text="")
        self.dice_label.pack(pady=18)
        self._draw_dice_face("?", color="#6366f1")

        self.btn_roll = ctk.CTkButton(center_frame, text="🎲 Бросить кубик", font=("Roboto", 18), height=44,
                                      command=self._start_roll_animation)
        self.btn_roll.pack()

        self.excluded_numbers = []

    def _add_excl_tag(self):
        raw = self.d_excl.get().strip()
        if not raw:
            return
        for part in raw.replace(";", ",").split(","):
            part = part.strip()
            try:
                n = int(part)
                if n not in self.excluded_numbers:
                    self.excluded_numbers.append(n)
            except ValueError:
                pass
        self.d_excl.delete(0, "end")
        self._refresh_excl_tags()

    def _refresh_excl_tags(self):
        for w in self.excl_tags_frame.winfo_children():
            w.destroy()
        for n in self.excluded_numbers:
            tag_f = ctk.CTkFrame(self.excl_tags_frame, fg_color="#3b1f6b", corner_radius=12)
            tag_f.pack(side=tk.LEFT, padx=3, pady=2)
            ctk.CTkLabel(tag_f, text=str(n), font=("Roboto", 12, "bold"),
                         text_color="#c4b5fd").pack(side=tk.LEFT, padx=(8, 2), pady=2)
            ctk.CTkButton(tag_f, text="✕", width=20, height=20, font=("Roboto", 10),
                          fg_color="transparent", hover_color="#6d28d9",
                          command=lambda num=n: self._remove_excl_tag(num)).pack(side=tk.LEFT, padx=(0, 4))

    def _remove_excl_tag(self, n):
        if n in self.excluded_numbers:
            self.excluded_numbers.remove(n)
        self._refresh_excl_tags()

    def _draw_dice_face(self, value, color="#6366f1", scale=1.0):
        from PIL import Image, ImageDraw, ImageFont
        import math

        size = 160
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))  # прозрачный фон
        draw = ImageDraw.Draw(img)

        cx, cy = size // 2, size // 2
        half = int(60 * scale)
        r = int(half * 0.30)
        x0, y0, x1, y1 = cx - half, cy - half, cx + half, cy + half

        # Цвет кубика
        def hex_to_rgba(h, a=255):
            h = h.lstrip("#")
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (a,)

        dice_fill = hex_to_rgba("#2d2b55")
        border_col = hex_to_rgba(color)
        shadow_col = (0, 0, 0, 120)
        text_col = hex_to_rgba(color)

        # Тень (скруглённый прямоугольник, смещение)
        so = 6
        draw.rounded_rectangle([x0 + so, y0 + so, x1 + so, y1 + so], radius=r, fill=shadow_col)

        # Основной кубик
        draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=dice_fill, outline=border_col, width=3)

        # Число по центру
        fsize = max(10, int(48 * scale))
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fsize)
        except:
            font = ImageFont.load_default()

        txt = str(value)
        bbox = draw.textbbox((0, 0), txt, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((cx - tw // 2, cy - th // 2 - 2), txt, font=font, fill=text_col)

        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
        self.dice_label.configure(image=ctk_img)
        self.dice_label._image = ctk_img  # защита от GC

    def _start_roll_animation(self):
        try:
            a, b = int(self.d_min.get()), int(self.d_max.get())
            if a > b: a, b = b, a

            available = [n for n in range(a, b + 1) if n not in self.excluded_numbers]
            if not available:
                messagebox.showwarning("Ошибка", "Все числа в диапазоне исключены!")
                return

            self.btn_roll.configure(state="disabled")
            self._animate_roll(available, frames_left=22, delay=30)
        except ValueError:
            messagebox.showerror("Ошибка", "Введите целые числа")

    def _animate_roll(self, available, frames_left, delay):
        if frames_left > 0:
            import math
            total = 22
            progress = (total - frames_left) / total
            scale = 1.0 + 0.12 * math.sin(progress * math.pi)
            colors = ["#6366f1", "#818cf8", "#a78bfa", "#7c3aed"]
            color = colors[frames_left % len(colors)]
            num = random.choice(available)
            self._draw_dice_face(num, color=color, scale=scale)
            new_delay = delay + int(170 / (frames_left + 1))
            self.after(new_delay, self._animate_roll, available, frames_left - 1, new_delay)
        else:
            final_res = random.choice(available)
            self._bounce_animation(final_res)

    def _bounce_animation(self, value):
        scales = [1.28, 0.90, 1.10, 0.97, 1.0]
        colors = ["#10b981", "#34d399", "#10b981", "#059669", "#10b981"]

        def do_bounce(idx):
            if idx < len(scales):
                self._draw_dice_face(value, color=colors[idx], scale=scales[idx])
                self.after(65, do_bounce, idx + 1)
            else:
                self._draw_dice_face(value, color="#10b981", scale=1.0)
                self.btn_roll.configure(state="normal")
                self.after(2200, lambda: self._draw_dice_face(value, color="#6366f1", scale=1.0))

        do_bounce(0)


if __name__ == "__main__":
    app = FinanceApp()
    app.mainloop()