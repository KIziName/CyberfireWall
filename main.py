import sys
import os
import customtkinter as ctk
from tkinter import messagebox

from utils import init_system_wide_mutex, enforce_admin
from gui import CyberFirewall

def check_dependencies():
    # Проверка наличия netsh.exe
    netsh_path = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'netsh.exe')
    if not os.path.exists(netsh_path):
        root = ctk.CTk()
        root.withdraw()
        messagebox.showerror("Ошибка", "netsh.exe не найден в системе.\nУбедитесь, что Windows установлена корректно.")
        sys.exit(1)

if __name__ == "__main__":
    # 1. Защита от повторного запуска
    init_system_wide_mutex()
    
    # 2. Проверка и форсирование прав админа
    enforce_admin()
    
    # 3. Проверка зависимостей системы
    check_dependencies()
    
    # 4. Инициализация глобального стиля темы
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    
    # 5. Запуск
    try:
        app = CyberFirewall()
        app.mainloop()
    except Exception as e:
        import traceback
        try:
            root = ctk.CTk()
            root.withdraw()
            messagebox.showerror("Ошибка запуска", f"Не удалось запустить программу:\n\n{traceback.format_exc()}")
        except:
            traceback.print_exc()
            input("Нажмите Enter для выхода...")
        sys.exit(1)
