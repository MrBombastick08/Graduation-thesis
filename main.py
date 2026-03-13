import csv
import json
import os
import random
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import customtkinter as ctk
from tkcalendar import DateEntry

# Настройки темы
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Файл для хранения Тугриков и Списка задач (чтобы они не терялись)
DATA_FILE = "app_internal_data.json"


class FinanceApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Управление финансами и Тугрики")
        self.geometry("1350x850")

        # Переменные данных
        self.current_csv_path = None
        self.operations = []
        self.tasks = []
        self.tugriki = 0

        # Наполнение магазина
        self.shop_items = [
            {"name": "Вечер кино", "price": 50},
            {"name": "Вкусный ужин", "price": 150},
            {"name": "Выходной от дел", "price": 500},
            {"name": "Подарок себе", "price": 1000}
        ]

        self._load_internal_data()
        self._setup_styles()
        self._build_ui()

    # ================= ЛОГИКА ФАЙЛОВ =================

    def _load_internal_data(self):
        """Загрузка задач и баланса тугриков"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.tasks = data.get("tasks", [])
                    self.tugriki = data.get("tugriki", 0)
            except:
                pass

    def _save_internal_data(self):
        """Сохранение задач и баланса тугриков"""
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"tasks": self.tasks, "tugriki": self.tugriki}, f, ensure_ascii=False, indent=2)

    def _select_csv(self):
        """Открыть существующий файл"""
        path = filedialog.askopenfilename(filetypes=[("CSV файлы", "*.csv")])
        if path:
            self.current_csv_path = path
            self.lbl_file_path.configure(text=f"Файл: {os.path.basename(path)}")
            self._refresh_table_from_csv()

    def _create_csv(self):
        """Создать новый файл с заголовками"""
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV файлы", "*.csv")])
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Дата", "Тип", "Категория", "Сумма", "Комментарий"])
            self.current_csv_path = path
            self.lbl_file_path.configure(text=f"Файл: {os.path.basename(path)}")
            self._refresh_table_from_csv()

    def _refresh_table_from_csv(self):
        """Очистка и полная загрузка таблицы из выбранного CSV"""
        for i in self.tree.get_children(): self.tree.delete(i)
        if not self.current_csv_path: return

        try:
            with open(self.current_csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.tree.insert("", "end", values=(row["Дата"], row["Тип"], row["Категория"], row["Сумма"],
                                                        row["Комментарий"]))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл: {e}")

    # ================= ИНТЕРФЕЙС =================

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", borderwidth=0)
        style.configure("Treeview.Heading", background="#1f538d", foreground="white", relief="flat")
        style.map("Treeview", background=[('selected', '#1f538d')])

    def _build_ui(self):
        # Верхняя панель управления файлом и тугриками
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

        # Вкладки
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

    # --- ВКЛАДКА ФИНАНСЫ ---
    def _init_finance_tab(self):
        tab = self.tabs.tab("Финансы")
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # Форма ввода (слева)
        form = ctk.CTkFrame(tab, width=300)
        form.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(form, text="Добавить запись", font=("Roboto", 16, "bold")).pack(pady=10)

        self.f_type = ctk.CTkOptionMenu(form, values=["Расход", "Доход"])
        self.f_type.pack(fill=tk.X, padx=15, pady=5)

        # Календарь
        date_f = ctk.CTkFrame(form, fg_color="transparent")
        date_f.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(date_f, text="Дата:").pack(side=tk.LEFT)
        self.f_date = DateEntry(date_f, background='#1f538d', foreground='white', date_pattern='yyyy-mm-dd')
        self.f_date.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))

        self.f_cat = ctk.CTkOptionMenu(form, values=["Продукты", "Транспорт", "Жилье", "Здоровье", "Досуг", "Зарплата"])
        self.f_cat.pack(fill=tk.X, padx=15, pady=5)

        self.f_amt = ctk.CTkEntry(form, placeholder_text="Сумма")
        self.f_amt.pack(fill=tk.X, padx=15, pady=5)

        self.f_comm = ctk.CTkEntry(form, placeholder_text="Комментарий")
        self.f_comm.pack(fill=tk.X, padx=15, pady=5)

        ctk.CTkButton(form, text="Сохранить в CSV", command=self._add_finance_to_csv).pack(fill=tk.X, padx=15, pady=20)

        # Таблица (справа)
        table_fr = ctk.CTkFrame(tab)
        table_fr.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        cols = ("date", "type", "cat", "amt", "comm")
        self.tree = ttk.Treeview(table_fr, columns=cols, show="headings")
        self.tree.heading("date", text="Дата");
        self.tree.heading("type", text="Тип")
        self.tree.heading("cat", text="Категория");
        self.tree.heading("amt", text="Сумма")
        self.tree.heading("comm", text="Комментарий")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _add_finance_to_csv(self):
        if not self.current_csv_path:
            messagebox.showwarning("Внимание", "Сначала выберите или создайте CSV файл!")
            return

        try:
            amt = float(self.f_amt.get())
            row = [self.f_date.get(), self.f_type.get(), self.f_cat.get(), amt, self.f_comm.get()]

            # Дозапись в конец файла
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

        # Поле ввода задачи
        input_fr = ctk.CTkFrame(tab)
        input_fr.pack(fill=tk.X, padx=20, pady=10)

        self.t_name = ctk.CTkEntry(input_fr, placeholder_text="Название задачи...", width=400)
        self.t_name.pack(side=tk.LEFT, padx=10, pady=10)

        self.t_rew = ctk.CTkEntry(input_fr, placeholder_text="Награда", width=80)
        self.t_rew.pack(side=tk.LEFT, padx=5, pady=10)

        ctk.CTkButton(input_fr, text="Добавить", width=100, command=self._add_task).pack(side=tk.LEFT, padx=10)

        # Список прокрутки
        self.tasks_container = ctk.CTkScrollableFrame(tab, label_text="Список текущих задач")
        self.tasks_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
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
        for w in self.tasks_container.winfo_children(): w.destroy()
        for i, t in enumerate(self.tasks):
            if t["done"]: continue
            f = ctk.CTkFrame(self.tasks_container)
            f.pack(fill=tk.X, pady=3, padx=5)
            ctk.CTkLabel(f, text=f"🎯 {t['title']}").pack(side=tk.LEFT, padx=15)
            ctk.CTkLabel(f, text=f"+{t['reward']} 💰", text_color="#facc15").pack(side=tk.LEFT)

            ctk.CTkButton(f, text="Выполнено", width=80, fg_color="#10b981",
                          command=lambda idx=i: self._complete_task(idx)).pack(side=tk.RIGHT, padx=5)

    def _complete_task(self, idx):
        self.tugriki += self.tasks[idx]["reward"]
        self.tasks[idx]["done"] = True
        self.tugriki_var.set(f"Тугрики: {self.tugriki} 💰")
        self._save_internal_data()
        self._refresh_task_list()

    # --- ВКЛАДКА МАГАЗИН ---
    def _init_shop_tab(self):
        tab = self.tabs.tab("Магазин")
        ctk.CTkLabel(tab, text="Потрать Тугрики на заслуженный отдых", font=("Roboto", 18, "bold")).pack(pady=20)

        grid = ctk.CTkFrame(tab, fg_color="transparent")
        grid.pack()

        for i, item in enumerate(self.shop_items):
            card = ctk.CTkFrame(grid, width=220, height=160)
            card.grid(row=i // 2, column=i % 2, padx=15, pady=15)
            card.grid_propagate(False)

            ctk.CTkLabel(card, text=item["name"], font=("Roboto", 15, "bold")).pack(pady=10)
            ctk.CTkLabel(card, text=f"Цена: {item['price']} 💰", text_color="#facc15").pack()

            ctk.CTkButton(card, text="Купить", width=120,
                          command=lambda it=item: self._buy_reward(it)).pack(side=tk.BOTTOM, pady=15)

    def _buy_reward(self, item):
        if self.tugriki >= item["price"]:
            self.tugriki -= item["price"]
            self.tugriki_var.set(f"Тугрики: {self.tugriki} 💰")
            self._save_internal_data()
            messagebox.showinfo("Поздравляем!", f"Вы приобрели: {item['name']}")
        else:
            messagebox.showwarning("Эх...", "Недостаточно тугриков. Время поработать!")

    # --- ВКЛАДКА КУБИК ---
    def _init_dice_tab(self):
        tab = self.tabs.tab("Кубик")

        ctk.CTkLabel(tab, text="🎲 Рандомайзер", font=("Roboto", 24, "bold")).pack(pady=20)

        input_f = ctk.CTkFrame(tab, fg_color="transparent")
        input_f.pack()

        ctk.CTkLabel(input_f, text="От:").grid(row=0, column=0, padx=5)
        self.d_min = ctk.CTkEntry(input_f, width=60);
        self.d_min.insert(0, "1");
        self.d_min.grid(row=0, column=1)

        ctk.CTkLabel(input_f, text="До:").grid(row=0, column=2, padx=5)
        self.d_max = ctk.CTkEntry(input_f, width=60);
        self.d_max.insert(0, "10");
        self.d_max.grid(row=0, column=3)

        self.dice_val = ctk.CTkLabel(tab, text="?", font=("Roboto", 100, "bold"), text_color="#6366f1")
        self.dice_val.pack(pady=40)

        ctk.CTkButton(tab, text="Бросить кубик", font=("Roboto", 16), command=self._roll_dice).pack()

    def _roll_dice(self):
        try:
            a, b = int(self.d_min.get()), int(self.d_max.get())
            res = random.randint(min(a, b), max(a, b))
            self.dice_val.configure(text=str(res))
        except:
            pass


if __name__ == "__main__":
    app = FinanceApp()
    app.mainloop()