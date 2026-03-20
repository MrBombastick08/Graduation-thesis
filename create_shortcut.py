"""
Запусти этот файл один раз чтобы создать ярлык на рабочем столе.
python create_shortcut.py
"""
import os
import sys

def create_shortcut():
    # Путь к папке с приложением
    app_dir  = os.path.dirname(os.path.abspath(__file__))
    main_py  = os.path.join(app_dir, "main.py")
    icon_ico = os.path.join(app_dir, "logo.ico")

    # Путь к Python в текущем окружении
    python_exe = sys.executable
    # pythonw.exe запускает скрипт без окна консоли
    pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")
    if os.path.exists(pythonw_exe):
        python_exe = pythonw_exe

    # Рабочий стол текущего пользователя
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if not os.path.exists(desktop):
        # Попробуем через shell folders (Windows)
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
        desktop = winreg.QueryValueEx(key, "Desktop")[0]

    shortcut_path = os.path.join(desktop, "Финансы и Тугрики.lnk")

    try:
        import win32com.client
        shell    = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(shortcut_path)
        shortcut.TargetPath       = python_exe
        shortcut.Arguments        = f'"{main_py}"'
        shortcut.WorkingDirectory = app_dir
        shortcut.IconLocation     = icon_ico if os.path.exists(icon_ico) else python_exe
        shortcut.Description      = "Управление финансами и Тугрики"
        shortcut.WindowStyle      = 1  # Normal window
        shortcut.save()
        print(f"Ярлык создан: {shortcut_path}")

    except ImportError:
        # Если pywin32 не установлен — создаём через PowerShell
        ps_script = f"""
$shell    = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut("{shortcut_path}")
$shortcut.TargetPath       = "{python_exe}"
$shortcut.Arguments        = '"{main_py}"'
$shortcut.WorkingDirectory = "{app_dir}"
$shortcut.IconLocation     = "{icon_ico if os.path.exists(icon_ico) else python_exe}"
$shortcut.Description      = "Управление финансами и Тугрики"
$shortcut.WindowStyle      = 1
$shortcut.Save()
""".strip()

        ps_file = os.path.join(app_dir, "_tmp_shortcut.ps1")
        with open(ps_file, "w", encoding="utf-8") as f:
            f.write(ps_script)

        ret = os.system(
            f'powershell -ExecutionPolicy Bypass -File "{ps_file}"'
        )
        os.remove(ps_file)

        if ret == 0:
            print(f"Ярлык создан: {shortcut_path}")
        else:
            print("Не удалось создать ярлык через PowerShell.")
            print("Установите pywin32:  pip install pywin32")


if __name__ == "__main__":
    if sys.platform != "win32":
        print("Этот скрипт предназначен только для Windows.")
        sys.exit(1)

    create_shortcut()
    input("\nНажмите Enter для выхода...")