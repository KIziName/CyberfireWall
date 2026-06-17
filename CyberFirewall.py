import customtkinter as ctk
import psutil
import threading
import subprocess
from tkinter import messagebox
import os
import sys
import ctypes
import webbrowser
import pystray
from datetime import datetime
from PIL import Image, ImageDraw, ImageTk
import time
import re

# ==================== ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА ====================
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class CyberFirewall(ctk.CTk):
    lang_data = {
        "RU": {
            "start_mon": "▶ Запустить мониторинг", "stop_mon": "⏸ Стоп мониторинг",
            "status_stop": "Мониторинг остановлен", "status_scan": "Сканирование соединений...",
            "status_ready": "Готов к работе", "err_empty": "Ошибка: Поле IP пустое!\n",
            "white_title": "Белый список", "white_header": "IP-адреса, защищенные от блокировки:\n\n",
            "deny_title": "Защита", "deny_text": "IP {} находится в белом списке!",
            "info_blocked": "IP {} уже заблокирован.\n", "success_block": "IP {} успешно заблокирован.\n",
            "err_fw": "Ошибка файрвола для {}: {}\n", "err_exec": "Системная ошибка: {}\n",
            "unblock_working": "Сброс правил...", "unblock_done": "Все правила CyberBlock удалены.",
            "net_err": "Сетевая ошибка: {}\n", "settings_lbl": "НАСТРОЙКИ",
            "tray_open": "Открыть", "tray_exit": "Выход", "about_title": "О программе",
            "proc_count": "соед.", "unblock_ip_success": "IP {} разблокирован.", "unblock_ip_not_found": "IP {} не найден в списке.",
            "notify_title_block": "Cyber Firewall: Блокировка", "notify_body_block": "IP {} был заблокирован.",
            "notify_title_unblock": "Cyber Firewall: Разблокировка", "notify_body_unblock": "IP {} разблокирован.",
            "notify_title_reset": "Cyber Firewall: Сброс", "notify_body_reset": "Все правила блокировки были удалены.",
            "already_running": "Cyber Firewall уже запущен и работает в системном трее!",
            "reset_already_running": "Сброс уже выполняется. Пожалуйста, подождите...",
            "reset_confirm_title": "Подтверждение сброса",
            "reset_confirm_text": "Вы уверены, что хотите удалить ВСЕ правила блокировки?\nЭто действие нельзя отменить.",
            "mode_detailed": "Режим: Детальный", "mode_aggregate": "Режим: По процессам",
            "btn_unblock_all": "❌ Удалить все правила", "btn_about": "ℹ О программе",
            "user_proc_tab": "Пользовательские процессы",
            "system_proc_tab": "Системные процессы",
            "blacklist_tab": "Чёрный список",
            "whitelist_tab": "Белый список",
            "status_tab": "Статус"
        },
        "EN": {
            "start_mon": "▶ Start Monitoring", "stop_mon": "⏸ Stop Monitoring",
            "status_stop": "Monitoring stopped", "status_scan": "Scanning connections...",
            "status_ready": "Ready to work", "err_empty": "Error: IP field is empty!\n",
            "white_title": "Whitelist", "white_header": "IP addresses protected from blocking:\n\n",
            "deny_title": "Protection", "deny_text": "IP {} is whitelisted!",
            "info_blocked": "IP {} already blocked.\n", "success_block": "IP {} blocked.\n",
            "err_fw": "Firewall error for {}: {}\n", "err_exec": "System error: {}\n",
            "unblock_working": "Resetting rules...", "unblock_done": "All rules removed.",
            "net_err": "Network error: {}\\n", "settings_lbl": "SETTINGS",
            "tray_open": "Open", "tray_exit": "Exit", "about_title": "About",
            "proc_count": "conn.", "unblock_ip_success": "IP {} unblocked.", "unblock_ip_not_found": "IP {} not found.",
            "notify_title_block": "Cyber Firewall: Blocked", "notify_body_block": "IP {} has been blocked.",
            "notify_title_unblock": "Cyber Firewall: Unblocked", "notify_body_unblock": "IP {} has been unblocked.",
            "notify_title_reset": "Cyber Firewall: Reset", "notify_body_reset": "All block rules have been removed.",
            "already_running": "Cyber Firewall is already running in the system tray!",
            "reset_already_running": "Reset is already in progress. Please wait...",
            "reset_confirm_title": "Confirm Reset",
            "reset_confirm_text": "Are you sure you want to remove ALL block rules?\nThis action cannot be undone.",
            "mode_detailed": "Mode: Detailed", "mode_aggregate": "Mode: By Processes",
            "btn_unblock_all": "❌ Remove all rules", "btn_about": "ℹ About Program",
            "user_proc_tab": "User Processes",
            "system_proc_tab": "System Processes",
            "blacklist_tab": "Blacklist",
            "whitelist_tab": "Whitelist",
            "status_tab": "Status"
        }
    }

    def __init__(self):
        self.mutex_name = "Local\\CyberFirewall_SingleInstance_Mutex_Protected"
        self.kernel32 = ctypes.windll.kernel32
        self.mutex = self.kernel32.CreateMutexW(None, False, self.mutex_name)
        if self.kernel32.GetLastError() == 183:
            root_temp = ctk.CTk()
            root_temp.withdraw()
            lang = CyberFirewall.lang_data["RU"]
            messagebox.showwarning("Cyber Firewall", lang["already_running"])
            sys.exit(0)

        super().__init__()
        self.title("Cyber Firewall v1.4.5")
        self.geometry("860x680")
        self.resizable(False, False)

        self.icon_img = ImageTk.PhotoImage(self.get_firewall_icon(128))
        try:
            self.iconphoto(True, self.icon_img)
        except Exception:
            pass

        self.is_monitoring = False
        self.current_theme = "Dark"
        self.current_lang = "RU"
        self.last_user_content = ""
        self.last_system_content = ""
        self.db_filename = self.get_data_file_path()
        self.pid_cache = {}
        self.blacklist_ips = set()
        self.file_lock = threading.Lock()
        self.pending_blocks = []
        self.flush_timer = None
        self.monitor_iteration = 0
        self.is_resetting = False
        self.aggregate_mode = False
        self.last_raw_data_full = {}
        self.monitor_thread = None

        self.whitelist = ["8.8.8.8", "8.8.4.4", "1.1.1.1", "77.88.8.8", "127.0.0.1"]

        self.load_blacklist_from_file()
        self.init_ui()

        self.tray_icon = None
        threading.Thread(target=self.init_tray, daemon=True).start()

    # -------------------- РАБОТА С ФАЙЛОМ --------------------
    def get_data_file_path(self):
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        folder = os.path.join(appdata, 'CyberFirewall')
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, 'cyber_blocked_ips.txt')

    def load_blacklist_from_file(self):
        with self.file_lock:
            if os.path.exists(self.db_filename):
                try:
                    with open(self.db_filename, "r", encoding="utf-8") as f:
                        for line in f:
                            parts = line.strip().split("_")
                            if len(parts) >= 2:
                                self.blacklist_ips.add(parts[1])
                except Exception:
                    pass

    def schedule_flush(self):
        if self.flush_timer:
            self.after_cancel(self.flush_timer)
        self.flush_timer = self.after(10000, self.flush_blocks_to_file)  # 10 секунд

    def flush_blocks_to_file(self, force=False):
        if not force and not self.pending_blocks:
            self.flush_timer = None
            return
        with self.file_lock:
            try:
                with open(self.db_filename, "a", encoding="utf-8") as db_file:
                    for block_line in self.pending_blocks:
                        db_file.write(block_line + "\n")
                self.pending_blocks.clear()
            except Exception:
                pass
        self.flush_timer = None

    def add_block_to_buffer(self, rule_name):
        self.pending_blocks.append(rule_name)
        self.schedule_flush()

    # -------------------- UI --------------------
    def init_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Левая панель
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.pack_propagate(False)
        ctk.CTkLabel(self.sidebar, text="Cyber Firewall", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=25)

        self.btn_monitor = ctk.CTkButton(self.sidebar, text="", height=36, corner_radius=8,
                                         command=self.toggle_monitoring, fg_color="#1abc9c", hover_color="#16a085")
        self.btn_monitor.pack(pady=6, padx=15, fill="x")
        self.btn_unblock_all = ctk.CTkButton(self.sidebar, text="", height=36, corner_radius=8,
                                             command=self.unblock_all_rules, fg_color="#c0392b", hover_color="#a93226")
        self.btn_unblock_all.pack(pady=6, padx=15, fill="x")
        self.btn_toggle_mode = ctk.CTkButton(self.sidebar, text="", height=36, corner_radius=8,
                                             command=self.toggle_aggregate_mode, fg_color="#2980b9", hover_color="#3498db")
        self.btn_toggle_mode.pack(pady=6, padx=15, fill="x")

        self.settings_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.settings_frame.pack(side="bottom", fill="x", pady=15, padx=15)
        self.status_lbl = ctk.CTkLabel(self.settings_frame, text="", text_color="#7f8c8d", font=ctk.CTkFont(size=11))
        self.status_lbl.pack(side="bottom", pady=(10, 0))
        self.btn_about = ctk.CTkButton(self.settings_frame, text="", height=30, corner_radius=6,
                                       command=self.show_about_info, fg_color="#27ae60")
        self.btn_about.pack(side="bottom", fill="x", pady=4)
        self.btn_lang = ctk.CTkButton(self.settings_frame, text="🌐 EN", command=self.toggle_language,
                                      fg_color="#9b59b6", height=30)
        self.btn_lang.pack(side="bottom", fill="x", pady=4)
        self.btn_theme = ctk.CTkButton(self.settings_frame, text="", command=self.toggle_theme,
                                       fg_color="#7f8c8d", height=30)
        self.btn_theme.pack(side="bottom", fill="x", pady=4)
        ctk.CTkFrame(self.settings_frame, height=2, fg_color="#34495e").pack(side="bottom", fill="x", pady=(0, 8))
        self.settings_lbl = ctk.CTkLabel(self.settings_frame, text="", text_color="#7f8c8d",
                                         font=ctk.CTkFont(size=10, weight="bold"))
        self.settings_lbl.pack(side="bottom", pady=(0, 2))

        # Правая область
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=15, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=0)

        # Верхние вкладки (процессы)
        self.process_tabs = ctk.CTkTabview(self.main_frame)
        self.process_tabs.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.tab_user = self.process_tabs.add("User")
        self.tab_system = self.process_tabs.add("System")
        # Моноширинный шрифт с хорошим сглаживанием (Cascadia Code, размер 13)
        log_font = ctk.CTkFont(family="Cascadia Code", size=13, weight="normal")
        self.user_log_area = ctk.CTkTextbox(self.tab_user, font=log_font,
                                            wrap="none", state="disabled")
        self.user_log_area.pack(fill="both", expand=True, padx=2, pady=2)
        self.system_log_area = ctk.CTkTextbox(self.tab_system, font=log_font,
                                              wrap="none", state="disabled")
        self.system_log_area.pack(fill="both", expand=True, padx=2, pady=2)

        # Нижние вкладки
        self.tabview = ctk.CTkTabview(self.main_frame, height=180)
        self.tabview.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.tab_black = self.tabview.add("Black")
        self.tab_white = self.tabview.add("White")
        self.tab_status = self.tabview.add("Status")

        # ========== ОТОБРАЖЕНИЕ ЧЁРНОГО СПИСКА (с крестиками) ==========
        self.blacklist_frame = ctk.CTkScrollableFrame(self.tab_black, label_text="")
        self.blacklist_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.tab_black.grid_columnconfigure(0, weight=1)
        self.tab_black.grid_rowconfigure(0, weight=1)
        self.blacklist_widgets = {}

        # Вкладка Blacklist: поле ввода и кнопки
        black_entry_frame = ctk.CTkFrame(self.tab_black, fg_color="transparent")
        black_entry_frame.grid(row=1, column=0, padx=5, pady=(0,5), sticky="ew")
        black_entry_frame.grid_columnconfigure(0, weight=3)
        black_entry_frame.grid_columnconfigure(1, weight=1)
        black_entry_frame.grid_columnconfigure(2, weight=1)
        self.entry_ip = ctk.CTkEntry(black_entry_frame, height=28)
        self.entry_ip.grid(row=0, column=0, padx=2, sticky="ew")
        self.btn_block = ctk.CTkButton(black_entry_frame, text="", height=28, command=self.block_ip_event, fg_color="#e74c3c")
        self.btn_block.grid(row=0, column=1, padx=2, sticky="ew")
        self.btn_unblock = ctk.CTkButton(black_entry_frame, text="", height=28, command=self.unblock_ip_event, fg_color="#f39c12")
        self.btn_unblock.grid(row=0, column=2, padx=2, sticky="ew")

        # Вкладка Whitelist
        self.tab_white.grid_columnconfigure(0, weight=1)
        self.btn_show_white = ctk.CTkButton(self.tab_white, text="", height=32, command=self.show_whitelist,
                                            fg_color="#7f8c8d")
        self.btn_show_white.grid(row=0, column=0, padx=5, pady=15, sticky="ew")

        # Вкладка Status
        self.tab_status.grid_columnconfigure(0, weight=1)
        self.status_indicator = ctk.CTkLabel(self.tab_status, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self.status_indicator.grid(row=0, column=0, padx=5, pady=15, sticky="ew")

        self.update_tab_titles()
        self.update_interface_text()
        self.update_blacklist_display()
        self.protocol('WM_DELETE_WINDOW', self.hide_to_tray)

    def update_tab_titles(self):
        lang = self.lang_data[self.current_lang]
        try:
            self.process_tabs._segmented_button.set_button_text(0, lang["user_proc_tab"])
            self.process_tabs._segmented_button.set_button_text(1, lang["system_proc_tab"])
        except Exception:
            pass
        try:
            self.tabview._segmented_button.set_button_text(0, lang["blacklist_tab"])
            self.tabview._segmented_button.set_button_text(1, lang["whitelist_tab"])
            self.tabview._segmented_button.set_button_text(2, lang["status_tab"])
        except Exception:
            pass

    # -------------------- ОПРЕДЕЛЕНИЕ СИСТЕМНЫХ ПРОЦЕССОВ (РАСШИРЕННОЕ) --------------------
    def is_system_process(self, proc_name, proc_path):
        system_names = {
            "System", "System Idle Process", "Registry", "smss.exe", "csrss.exe", "wininit.exe",
            "winlogon.exe", "services.exe", "lsass.exe", "lsm.exe", "svchost.exe", "dwm.exe",
            "spoolsv.exe", "taskhost.exe", "taskhostw.exe", "sihost.exe", "fontdrvhost.exe",
            "ctfmon.exe", "runtimebroker.exe", "dllhost.exe", "WmiPrvSE.exe", "SearchIndexer.exe",
            "MsMpEng.exe", "NisSrv.exe", "SecurityHealthService.exe", "SecurityHealthSystray.exe",
            "ShellExperienceHost.exe", "StartMenuExperienceHost.exe", "wuauclt.exe", "wuauserv",
            "TrustedInstaller.exe", "TiWorker.exe", "MusNotifyIcon.exe", "OneDriveSetup.exe",
            "SettingSyncHost.exe", "LogonUI.exe", "UserOOBEBroker.exe", "backgroundTaskHost.exe"
        }
        if proc_name in system_names:
            return True
        windows_path = os.environ.get('SystemRoot', 'C:\\Windows').lower()
        proc_path_lower = proc_path.lower()
        if windows_path in proc_path_lower:
            if ('system32' in proc_path_lower or 'syswow64' in proc_path_lower or 
                proc_path_lower == windows_path or proc_path_lower.startswith(windows_path + '\\')):
                return True
        return False

    # -------------------- ОТОБРАЖЕНИЕ ЧЁРНОГО СПИСКА С КРЕСТИКАМИ --------------------
    def update_blacklist_display(self):
        for widget in self.blacklist_frame.winfo_children():
            widget.destroy()
        self.blacklist_widgets.clear()

        if not self.blacklist_ips:
            lbl = ctk.CTkLabel(self.blacklist_frame, text="Нет заблокированных IP" if self.current_lang == "RU" else "No blocked IPs",
                               font=ctk.CTkFont(size=12))
            lbl.pack(pady=10)
            return

        for ip in sorted(self.blacklist_ips):
            frame = ctk.CTkFrame(self.blacklist_frame)
            frame.pack(fill="x", padx=5, pady=2)
            lbl_ip = ctk.CTkLabel(frame, text=ip, font=ctk.CTkFont(size=12), anchor="w")
            lbl_ip.pack(side="left", padx=5, pady=2, fill="x", expand=True)
            btn_del = ctk.CTkButton(frame, text="❌", width=30, height=28,
                                     fg_color="#c0392b", hover_color="#e74c3c",
                                     command=lambda ip_addr=ip: self.unblock_ip(ip_addr))
            btn_del.pack(side="right", padx=5, pady=2)
            self.blacklist_widgets[ip] = frame

    # -------------------- ЛОГИКА РАЗБЛОКИРОВКИ IP (ИСПРАВЛЕННАЯ ВЕРСИЯ) --------------------
    def unblock_ip(self, ip):
        lang = self.lang_data[self.current_lang]
        if ip not in self.blacklist_ips:
            self.log_message(self.user_log_area, lang["unblock_ip_not_found"].format(ip))
            return
        try:
            cmd = ["netsh", "advfirewall", "firewall", "delete", "rule", f"name=CyberBlock_{ip}"]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            self.log_message(self.user_log_area, lang["err_exec"].format(e))
            return

        self.blacklist_ips.discard(ip)

        # --- ИСПРАВЛЕННЫЙ БЛОК ДЛЯ РАБОТЫ С БУФЕРОМ И ФАЙЛОМ ---
        target_rule = f"CyberBlock_{ip}"
        
        with self.file_lock:
            # 1. Удаляем IP из временного буфера.
            self.pending_blocks = [rule for rule in self.pending_blocks if rule != target_rule]
            
            # 2. Удаляем IP из файла (на случай, если он там уже был со старых запусков)
            if os.path.exists(self.db_filename):
                try:
                    with open(self.db_filename, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    
                    # Фильтруем строки по строгому совпадению
                    new_lines = [line for line in lines if line.strip() != target_rule]
                    
                    with open(self.db_filename, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)
                except Exception:
                    pass
        # -----------------------------------------------------------

        self.update_blacklist_display()
        self.log_message(self.user_log_area, lang["unblock_ip_success"].format(ip))
        self.send_notification(lang["notify_title_unblock"], lang["notify_body_unblock"].format(ip))

    def unblock_ip_event(self):
        ip = self.entry_ip.get().strip()
        lang = self.lang_data[self.current_lang]
        if not ip:
            self.log_message(self.user_log_area, lang["err_empty"])
            return
        self.unblock_ip(ip)

    # -------------------- ОСТАЛЬНЫЕ МЕТОДЫ --------------------
    def clear_monitoring_logs(self):
        if not self.user_log_area or not self.system_log_area:
            return
        try:
            self.user_log_area.configure(state="normal")
            self.user_log_area.delete("0.0", "end")
            self.system_log_area.configure(state="normal")
            self.system_log_area.delete("0.0", "end")
            self.last_user_content = ""
            self.last_system_content = ""
            self.user_log_area.configure(state="disabled")
            self.system_log_area.configure(state="disabled")
        except:
            pass
        self.last_raw_data_full = {}

    def toggle_aggregate_mode(self):
        self.aggregate_mode = not self.aggregate_mode
        self.update_interface_text()
        if self.is_monitoring and self.last_raw_data_full:
            self.after(0, self._update_logs_from_raw_data)

    def _update_logs_from_raw_data(self):
        try:
            data_copy = getattr(self, 'last_raw_data_full', {}).copy()
            if not data_copy:
                return
            lang = self.lang_data[self.current_lang]

            if not self.aggregate_mode:
                user_lines = []
                system_lines = []
                for (proc_name, proc_path, ip, proto), count in data_copy.items():
                    display_path = (proc_path[:15] + "..." + proc_path[-25:]) if len(proc_path) > 45 else proc_path
                    is_sys = self.is_system_process(proc_name, proc_path)
                    line = f"[{proc_name} ({display_path})] -> {ip} ({count} {lang['proc_count']})\n"
                    if is_sys:
                        system_lines.append((proc_name, line))
                    else:
                        user_lines.append((proc_name, line))
                user_lines.sort(key=lambda x: x[0])
                system_lines.sort(key=lambda x: x[0])
                user_text = "".join(line for _, line in user_lines)
                system_text = "".join(line for _, line in system_lines)
            else:
                proc_data = {}
                for (proc_name, proc_path, ip, proto), count in data_copy.items():
                    key = (proc_name, proc_path)
                    if key not in proc_data:
                        display_path = (proc_path[:15] + "..." + proc_path[-25:]) if len(proc_path) > 45 else proc_path
                        proc_data[key] = {
                            "display": display_path,
                            "ips": set(),
                            "total": 0,
                            "is_sys": self.is_system_process(proc_name, proc_path)
                        }
                    proc_data[key]["ips"].add(ip)
                    proc_data[key]["total"] += count
                items = []
                for (proc_name, proc_path), data in proc_data.items():
                    ip_count = len(data["ips"])
                    total_conn = data["total"]
                    line = f"[{proc_name} ({data['display']})] -> {ip_count} IP ({total_conn} {lang['proc_count']})\n"
                    items.append((proc_name, line, data["is_sys"]))
                items.sort(key=lambda x: x[0])
                user_text = "".join(line for _, line, is_sys in items if not is_sys)
                system_text = "".join(line for _, line, is_sys in items if is_sys)

            if user_text != self.last_user_content:
                self.last_user_content = user_text
                if self.user_log_area:
                    self.user_log_area.configure(state="normal")
                    self.user_log_area.delete("0.0", "end")
                    self.user_log_area.insert("0.0", user_text)
                    self.user_log_area.configure(state="disabled")
            if system_text != self.last_system_content:
                self.last_system_content = system_text
                if self.system_log_area:
                    self.system_log_area.configure(state="normal")
                    self.system_log_area.delete("0.0", "end")
                    self.system_log_area.insert("0.0", system_text)
                    self.system_log_area.configure(state="disabled")
        except Exception as e:
            print(f"Error updating logs: {e}")

    # -------------------- ИКОНКА В ТРЕЕ --------------------
    def get_firewall_icon(self, size=128):
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        shield_color = (52, 152, 219)
        border_color = (255, 255, 255)
        inner_color = (255, 255, 255)
        margin = size // 8
        top = margin
        left = margin
        right = size - margin
        bottom = size - margin
        point_x = size // 2
        point_y = size - margin
        polygon = [
            (left, top), (right, top),
            (right, bottom - margin),
            (point_x, point_y),
            (left, bottom - margin),
        ]
        draw.polygon(polygon, fill=shield_color, outline=border_color, width=max(2, size // 32))
        inner_r = size // 5
        draw.ellipse(
            (size // 2 - inner_r, size // 2 - inner_r, size // 2 + inner_r, size // 2 + inner_r),
            fill=inner_color
        )
        return img

    def init_tray(self):
        lang = self.lang_data[self.current_lang]
        icon = self.get_firewall_icon(64)
        menu = pystray.Menu(
            pystray.MenuItem(lang["tray_open"], self.show_from_tray, default=True),
            pystray.MenuItem(lang["tray_exit"], self.completely_exit)
        )
        self.tray_icon = pystray.Icon("cyber_firewall", icon, "Cyber Firewall", menu)
        self.tray_icon.run()

    def hide_to_tray(self):
        self.withdraw()

    def show_from_tray(self):
        self.deiconify()

    def completely_exit(self):
        self.flush_blocks_to_file(force=True)
        self.is_monitoring = False
        if self.tray_icon:
            self.tray_icon.stop()
        if hasattr(self, "mutex") and self.mutex:
            ctypes.windll.kernel32.CloseHandle(self.mutex)
        self.quit()
        sys.exit(0)

    def send_notification(self, title, message):
        if self.tray_icon:
            self.after(0, lambda: self._do_notify(title, message))

    def _do_notify(self, title, message):
        try:
            self.tray_icon.notify(message, title)
        except Exception:
            pass

    # -------------------- БЛОКИРОВКА IP --------------------
    def block_ip_event(self):
        ip = self.entry_ip.get().strip()
        lang = self.lang_data[self.current_lang]
        if not ip:
            self.log_message(self.user_log_area, lang["err_empty"])
            return
        if ip in self.whitelist:
            messagebox.showerror(title=lang["deny_title"], message=lang["deny_text"].format(ip))
            return
        self.execute_block(ip)

    def execute_block(self, ip):
        lang = self.lang_data[self.current_lang]
        if ip in self.blacklist_ips:
            self.log_message(self.user_log_area, lang["info_blocked"].format(ip))
            return
        rule_name = f"CyberBlock_{ip}"
        try:
            cmd = ["netsh", "advfirewall", "firewall", "add", "rule", f"name={rule_name}",
                   "dir=out", "action=block", f"remoteip={ip}"]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
            if res.returncode == 0:
                self.log_message(self.user_log_area, lang["success_block"].format(ip))
                self.add_block_to_buffer(rule_name)
                self.blacklist_ips.add(ip)
                self.update_blacklist_display()
                self.send_notification(lang["notify_title_block"], lang["notify_body_block"].format(ip))
            else:
                self.log_message(self.user_log_area, lang["err_fw"].format(ip, "Firewall Error"))
        except Exception as e:
            self.log_message(self.user_log_area, lang["err_exec"].format(e))

    # -------------------- СБРОС ВСЕХ ПРАВИЛ --------------------
    def unblock_all_rules(self):
        lang = self.lang_data[self.current_lang]
        if self.is_resetting:
            self.log_message(self.user_log_area, lang["reset_already_running"])
            return
        if not messagebox.askyesno(lang["reset_confirm_title"], lang["reset_confirm_text"]):
            return
        self.is_resetting = True
        self.status_lbl.configure(text=lang["unblock_working"], text_color="#e67e22")
        threading.Thread(target=self._unblock_all_worker, daemon=True).start()

    def _unblock_all_worker(self):
        try:
            ps_cmd = "Get-NetFirewallRule | Where-Object { $_.Name -like 'CyberBlock_*' } | Remove-NetFirewallRule"
            subprocess.run(["powershell", "-Command", ps_cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass
        with self.file_lock:
            if os.path.exists(self.db_filename):
                try:
                    os.remove(self.db_filename)
                except Exception:
                    pass
        self.blacklist_ips.clear()
        self.pending_blocks.clear()
        if self.flush_timer:
            self.after_cancel(self.flush_timer)
            self.flush_timer = None
        self.after(0, self._finalize_unblock_all)

    def _finalize_unblock_all(self):
        lang = self.lang_data[self.current_lang]
        self.update_blacklist_display()
        self.log_message(self.user_log_area, f"\n[🧹] {lang['unblock_done']}\n")
        self.update_status_indicator()
        self.status_lbl.configure(text=lang["status_ready"] if not self.is_monitoring else lang["status_scan"])
        self.send_notification(lang["notify_title_reset"], lang["notify_body_reset"])
        self.is_resetting = False

    # -------------------- МОНИТОРИНГ СОЕДИНЕНИЙ --------------------
    def toggle_monitoring(self):
        lang = self.lang_data[self.current_lang]
        if self.is_monitoring:
            self.is_monitoring = False
            self.btn_monitor.configure(text=lang["start_mon"], fg_color="#1abc9c")
            self.status_lbl.configure(text=lang["status_stop"], text_color="#e74c3c")
            self.log_message(self.user_log_area, f"\n[#] {lang['status_stop']}\n")
            self.clear_monitoring_logs()
        else:
            self.is_monitoring = True
            self.btn_monitor.configure(text=lang["stop_mon"], fg_color="#e74c3c")
            self.status_lbl.configure(text=lang["status_scan"], text_color="#27ae60")
            self.log_message(self.user_log_area, f"\n[*] {lang['status_scan']}\n")
            self.monitor_thread = threading.Thread(target=self.monitor_logic, daemon=True)
            self.monitor_thread.start()
        self.update_status_indicator()

    def update_status_indicator(self):
        lang = self.lang_data[self.current_lang]
        if self.is_monitoring:
            self.status_indicator.configure(text="🟢 " + lang["status_scan"], text_color="#27ae60")
        else:
            self.status_indicator.configure(text="🔴 " + lang["status_stop"], text_color="#e74c3c")

    def clean_pid_cache(self):
        to_remove = [pid for pid in self.pid_cache if not psutil.pid_exists(pid)]
        for pid in to_remove:
            del self.pid_cache[pid]

    def monitor_logic(self):
        last_err_time = 0
        while self.is_monitoring:
            try:
                self.monitor_iteration += 1
                if self.monitor_iteration >= 20:
                    self.monitor_iteration = 0
                    self.clean_pid_cache()

                conns = psutil.net_connections(kind='inet')
                raw_data = {}
                for conn in conns:
                    if not conn.raddr:
                        continue
                    proto = "TCP" if "STREAM" in str(conn.type) or conn.type == 1 else "UDP"
                    if proto == 'TCP' and conn.status not in ['ESTABLISHED', 'SYN_SENT']:
                        continue
                    ip = conn.raddr.ip
                    pid = conn.pid
                    if not pid or ip in ['127.0.0.1', '::1', '0.0.0.0', '*']:
                        continue
                    try:
                        if pid in self.pid_cache:
                            proc_name, proc_path = self.pid_cache[pid]
                        else:
                            proc = psutil.Process(pid)
                            proc_name = proc.name()
                            proc_path = proc.exe()
                            self.pid_cache[pid] = (proc_name, proc_path)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        proc_name, proc_path = "unknown_process", "unknown_path"
                    except Exception:
                        proc_name, proc_path = "error_process", "error_path"

                    group_key = (proc_name, proc_path, ip, proto)
                    raw_data[group_key] = raw_data.get(group_key, 0) + 1

                self.last_raw_data_full = raw_data.copy()
                self.after(0, self._update_logs_from_raw_data)
            except Exception as e:
                curr_time = time.time()
                if curr_time - last_err_time > 5.0:
                    last_err_time = curr_time
                    lang = self.lang_data[self.current_lang]
                    self.after(0, lambda error_msg=e: self.log_message(self.user_log_area, lang["net_err"].format(error_msg)))
            time.sleep(1.0)

    # -------------------- ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ --------------------
    def log_message(self, textbox, message):
        if not textbox:
            return
        try:
            textbox.configure(state="normal")
            timestamp = datetime.now().strftime("[%H:%M:%S] ")
            textbox.insert("end", timestamp + message)
            textbox.see("end")
            textbox.configure(state="disabled")
        except Exception:
            pass

    def show_whitelist(self):
        lang = self.lang_data[self.current_lang]
        white_text = lang["white_header"] + "".join([f" • {ip}\n" for ip in self.whitelist])
        messagebox.showinfo(title=lang["white_title"], message=white_text)

    def show_about_info(self):
        lang = self.lang_data[self.current_lang]
        about_win = ctk.CTkToplevel(self)
        about_win.title(lang["about_title"])
        about_win.geometry("460x220")
        about_win.resizable(False, False)
        about_win.transient(self)
        about_win.grab_set()

        x = self.winfo_x() + (self.winfo_width() // 2) - 230
        y = self.winfo_y() + (self.winfo_height() // 2) - 110
        about_win.geometry(f"+{x}+{y}")

        main_text = (
            "Cyber Firewall\n\n"
            "Версия: 1.4.5\nАвтор: KiziName\n\n"
            "Ручное управление блокировками IP через брандмауэр Windows."
        ) if self.current_lang == "RU" else (
            "Cyber Firewall\n\n"
            "Version: 1.4.5\nAuthor: KiziName\n\n"
            "Manual IP blocking via Windows Firewall."
        )
        lbl_main = ctk.CTkLabel(about_win, text=main_text, justify="left", font=ctk.CTkFont(size=13))
        lbl_main.pack(pady=(20, 5), padx=20, anchor="w")

        link_frame = ctk.CTkFrame(about_win, fg_color="transparent")
        link_frame.pack(padx=20, anchor="w", fill="x")
        ctk.CTkLabel(link_frame, text="GitHub: ", font=ctk.CTkFont(size=13)).pack(side="left")
        url = "https://github.com/KIziName/Cyber_firewall-Pro/releases"
        lbl_link = ctk.CTkLabel(link_frame, text="github.com/KIziName/Cyber_firewall-Pro",
                                text_color="#3498db", cursor="hand2", font=ctk.CTkFont(size=13))
        lbl_link.pack(side="left")
        lbl_link.bind("<Button-1>", lambda e: webbrowser.open_new(url))

    def toggle_language(self):
        self.current_lang = "EN" if self.current_lang == "RU" else "RU"
        self.btn_lang.configure(text="🌐 EN" if self.current_lang == "RU" else "🌐 RU")
        self.update_interface_text()
        self.update_blacklist_display()
        self.update_status_indicator()
        self.update_tab_titles()
        if self.is_monitoring and self.last_raw_data_full:
            self.after(0, self._update_logs_from_raw_data)

    def toggle_theme(self):
        if self.current_theme == "Dark":
            self.current_theme = "Light"
            ctk.set_appearance_mode("Light")
        else:
            self.current_theme = "Dark"
            ctk.set_appearance_mode("Dark")
        self.update_interface_text()

    def update_interface_text(self):
        lang = self.lang_data[self.current_lang]
        self.btn_monitor.configure(text=lang["start_mon"] if not self.is_monitoring else lang["stop_mon"])
        self.btn_unblock_all.configure(text=lang["btn_unblock_all"])
        self.btn_toggle_mode.configure(text=lang["mode_detailed"] if not self.aggregate_mode else lang["mode_aggregate"])
        self.btn_about.configure(text=lang["btn_about"])
        self.btn_theme.configure(text="☀ Light" if self.current_theme == "Dark" else "🌙 Dark")
        self.settings_lbl.configure(text=lang["settings_lbl"])
        self.btn_block.configure(text="🚫 Block IP" if self.current_lang == "EN" else "🚫 Блокировать")
        self.btn_unblock.configure(text="🔓 Unblock IP" if self.current_lang == "EN" else "🔓 Разблокировать")
        self.btn_show_white.configure(text="📋 Show Whitelist" if self.current_lang == "EN" else "📋 Показать Белый Список")
        self.status_lbl.configure(text=lang["status_ready"] if not self.is_monitoring else lang["status_scan"])


if __name__ == "__main__":
    app = CyberFirewall()
    app.mainloop()