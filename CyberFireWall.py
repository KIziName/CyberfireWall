# ==================== УНИВЕРСАЛЬНЫЙ GLOBAL МЬЮТЕКС ====================
import sys
import ctypes
import atexit
import os

def _init_system_wide_mutex():
    kernel32 = ctypes.windll.kernel32
    clean_name = os.path.basename(sys.argv[0]).replace('.', '_').replace(' ', '_')
    mutex_name = f"Global\\AutoGuard_{clean_name}_Mutex"
    mutex_handle = kernel32.CreateMutexW(None, False, mutex_name)

    if kernel32.GetLastError() == 183:
        if mutex_handle:
            kernel32.CloseHandle(mutex_handle)
        try:
            is_russian = ctypes.windll.kernel32.GetUserDefaultUILanguage() == 1049
        except Exception:
            is_russian = True
        if is_russian:
            msg = "Приложение уже запущено!\nРазрешена только одна активная копия."
            title = "Защита от повторного запуска"
        else:
            msg = "The application is already running!\nOnly one active instance is allowed."
            title = "Already Running"
        ctypes.windll.user32.MessageBoxW(0, msg, title, 0x10 | 0x00)
        sys.exit(0)
    atexit.register(lambda: kernel32.CloseHandle(mutex_handle) if mutex_handle else None)

_init_system_wide_mutex()
# ======================================================================

import customtkinter as ctk
import psutil
import threading
import subprocess
from tkinter import messagebox
import webbrowser
import pystray
from datetime import datetime
from PIL import Image, ImageDraw, ImageTk
import time
import ipaddress

# ==================== КОНСТАНТЫ ====================
class Config:
    WINDOW_WIDTH = 860
    WINDOW_HEIGHT = 680
    SIDEBAR_WIDTH = 250
    MONITOR_INTERVAL_SEC = 1.0
    TRAY_ICON_SIZE = 64
    LOG_FONT_FAMILY = "Cascadia Code"
    LOG_FONT_SIZE = 13
    ABOUT_WIN_WIDTH = 460
    ABOUT_WIN_HEIGHT = 220
    BLACKLIST_ENTRY_HEIGHT = 28

# ==================== ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА ====================
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    cmd_line = subprocess.list2cmdline(sys.argv)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, cmd_line, None, 1)
    sys.exit()

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ==================== ПРОВЕРКА НАЛИЧИЯ netsh.exe ====================
netsh_path = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'netsh.exe')
if not os.path.exists(netsh_path):
    root = ctk.CTk()
    root.withdraw()
    messagebox.showerror("Ошибка", "netsh.exe не найден в системе.\nУбедитесь, что Windows установлена корректно.")
    sys.exit(1)

# ==================== СЕРВИС: FirewallService ====================
class FirewallService:
    RULE_PREFIX = "CyberBlock_"

    @staticmethod
    def is_valid_ip(ip: str) -> bool:
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    def block_ip(self, ip: str) -> bool:
        if not self.is_valid_ip(ip):
            return False
        rule_name = f"{self.RULE_PREFIX}{ip}"
        cmd = [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={rule_name}", "dir=out", "action=block", f"remoteip={ip}"
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return result.returncode == 0
        except Exception:
            return False

    def unblock_ip(self, ip: str) -> bool:
        rule_name = f"{self.RULE_PREFIX}{ip}"
        cmd = ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rule_name}"]
        try:
            result = subprocess.run(cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return result.returncode == 0
        except Exception:
            return False

    def get_blocked_ips(self) -> set:
        """Возвращает множество IP, заблокированных нашей программой."""
        cmd = ["netsh", "advfirewall", "firewall", "show", "rule", f'name="{self.RULE_PREFIX}*"']
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore',
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                return set()
            blocked = set()
            for line in result.stdout.splitlines():
                if self.RULE_PREFIX in line:
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        rule_name = parts[1].strip()
                        if rule_name.startswith(self.RULE_PREFIX):
                            ip = rule_name[len(self.RULE_PREFIX):]
                            if self.is_valid_ip(ip):
                                blocked.add(ip)
            return blocked
        except Exception:
            return set()

# ==================== ХРАНИЛИЩЕ: BlacklistStorage ====================
class BlacklistStorage:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self._lock = threading.Lock()
        self._ensure_dir()

    def _ensure_dir(self):
        dirname = os.path.dirname(self.filepath)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)

    def load(self) -> set:
        with self._lock:
            if not os.path.exists(self.filepath):
                return set()
            ips = set()
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith(FirewallService.RULE_PREFIX):
                            ip = line[len(FirewallService.RULE_PREFIX):]
                            if FirewallService.is_valid_ip(ip):
                                ips.add(ip)
            except Exception:
                pass
            return ips

    def add(self, ip: str) -> bool:
        if not FirewallService.is_valid_ip(ip):
            return False
        with self._lock:
            try:
                with open(self.filepath, "a", encoding="utf-8") as f:
                    f.write(f"{FirewallService.RULE_PREFIX}{ip}\n")
                return True
            except Exception:
                return False

    def remove(self, ip: str) -> bool:
        if not FirewallService.is_valid_ip(ip):
            return False
        with self._lock:
            if not os.path.exists(self.filepath):
                return False
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                target = f"{FirewallService.RULE_PREFIX}{ip}\n"
                new_lines = [line for line in lines if line != target]
                with open(self.filepath, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                return True
            except Exception:
                return False

    def clear(self) -> bool:
        with self._lock:
            if os.path.exists(self.filepath):
                try:
                    os.remove(self.filepath)
                    return True
                except Exception:
                    return False
            return True

# ==================== ФАСАД: StorageService (только чёрный список) ====================
class StorageService:
    def __init__(self, blacklist_path: str):
        self.blacklist = BlacklistStorage(blacklist_path)

    def load_blacklist(self) -> set:
        return self.blacklist.load()

    def add_to_blacklist(self, ip: str) -> bool:
        return self.blacklist.add(ip)

    def remove_from_blacklist(self, ip: str) -> bool:
        return self.blacklist.remove(ip)

# ==================== ПРОСТОЙ EventEmitter ====================
class EventEmitter:
    def __init__(self):
        self._listeners = {}

    def on(self, event: str, callback):
        self._listeners.setdefault(event, []).append(callback)

    def emit(self, event: str, *args, **kwargs):
        for cb in self._listeners.get(event, []):
            cb(*args, **kwargs)

# ==================== СЕРВИС: MonitoringService ====================
class MonitoringService(EventEmitter):
    def __init__(self, interval_sec: float = 1.0):
        super().__init__()
        self.interval = interval_sec
        self._running = threading.Event()
        self._thread = None
        self._pid_cache = {}

    def start(self):
        if self._running.is_set():
            return
        self._running.set()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running.clear()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

    def is_running(self) -> bool:
        return self._running.is_set()

    def _monitor_loop(self):
        while self._running.is_set():
            data = self._collect_connections()
            self.emit('update', data)
            time.sleep(self.interval)

    def _collect_connections(self) -> dict:
        active_pids = set(psutil.pids())
        self._pid_cache = {pid: val for pid, val in self._pid_cache.items() if pid in active_pids}
        raw = {}
        try:
            conns = psutil.net_connections(kind='inet')
        except Exception:
            return raw
        for conn in conns:
            if not conn.raddr:
                continue
            proto = "TCP" if (conn.type == 1) else "UDP"
            if proto == 'TCP' and conn.status not in ('ESTABLISHED', 'SYN_SENT'):
                continue
            ip = conn.raddr.ip
            pid = conn.pid
            if not pid or ip in ('127.0.0.1', '::1', '0.0.0.0', '*'):
                continue
            try:
                proc = psutil.Process(pid)
                if pid in self._pid_cache and proc.name() == self._pid_cache[pid][0]:
                    proc_name, proc_path = self._pid_cache[pid]
                else:
                    proc_name = proc.name()
                    proc_path = proc.exe()
                    self._pid_cache[pid] = (proc_name, proc_path)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                if pid in self._pid_cache:
                    del self._pid_cache[pid]
                proc_name, proc_path = "unknown_process", "unknown_path"
            key = (proc_name, proc_path, ip, proto)
            raw[key] = raw.get(key, 0) + 1
        return raw

# ==================== ОСНОВНОЙ КЛАСС ПРИЛОЖЕНИЯ (рефакторинг, белый список статический) ====================
class CyberFirewall(ctk.CTk):
    lang_data = {
        "RU": {
            "start_mon": "▶ Запустить мониторинг",
            "stop_mon": "⏸ Стоп мониторинг",
            "status_stop": "Мониторинг остановлен",
            "status_scan": "Сканирование соединений...",
            "status_ready": "Готов к работе",
            "err_empty": "Ошибка: Поле IP пустое!\n",
            "white_title": "Белый список",
            "white_header": "IP-адреса, защищенные от блокировки:\n\n",
            "deny_title": "Защита",
            "deny_text": "IP {} находится в белом списке!",
            "info_blocked": "IP {} уже заблокирован.\n",
            "success_block": "IP {} успешно заблокирован.\n",
            "err_fw": "Ошибка файрвола для {}: {}\n",
            "err_exec": "Системная ошибка: {}\n",
            "net_err": "Сетевая ошибка: {}\n",
            "settings_lbl": "НАСТРОЙКИ",
            "tray_open": "Открыть",
            "tray_exit": "Выход",
            "about_title": "О программе",
            "proc_count": "соед.",
            "unblock_ip_success": "IP {} разблокирован.",
            "unblock_ip_not_found": "IP {} не найден в списке.",
            "notify_title_block": "Cyber Firewall: Блокировка",
            "notify_body_block": "IP {} был заблокирован.",
            "notify_title_unblock": "Cyber Firewall: Разблокировка",
            "notify_body_unblock": "IP {} разблокирован.",
            "mode_detailed": "Режим: Детальный",
            "mode_aggregate": "Режим: По процессам",
            "btn_about": "ℹ О программе",
            "user_proc_tab": "Пользовательские процессы",
            "system_proc_tab": "Системные процессы",
            "blacklist_tab": "Чёрный список",
            "whitelist_tab": "Белый список",
            "status_tab": "Статус",
            "invalid_ip": "Некорректный IP-адрес",
            "netsh_error_title": "Ошибка",
            "netsh_error_msg": "netsh.exe не найден в системе.\nУбедитесь, что Windows установлена корректно."
        },
        "EN": {
            "start_mon": "▶ Start Monitoring",
            "stop_mon": "⏸ Stop Monitoring",
            "status_stop": "Monitoring stopped",
            "status_scan": "Scanning connections...",
            "status_ready": "Ready to work",
            "err_empty": "Error: IP field is empty!\n",
            "white_title": "Whitelist",
            "white_header": "IP addresses protected from blocking:\n\n",
            "deny_title": "Protection",
            "deny_text": "IP {} is whitelisted!",
            "info_blocked": "IP {} already blocked.\n",
            "success_block": "IP {} blocked.\n",
            "err_fw": "Firewall error for {}: {}\n",
            "err_exec": "System error: {}\n",
            "net_err": "Network error: {}\n",
            "settings_lbl": "SETTINGS",
            "tray_open": "Open",
            "tray_exit": "Exit",
            "about_title": "About",
            "proc_count": "conn.",
            "unblock_ip_success": "IP {} unblocked.",
            "unblock_ip_not_found": "IP {} not found.",
            "notify_title_block": "Cyber Firewall: Blocked",
            "notify_body_block": "IP {} has been blocked.",
            "notify_title_unblock": "Cyber Firewall: Unblocked",
            "notify_body_unblock": "IP {} has been unblocked.",
            "mode_detailed": "mode: Detailed",
            "mode_aggregate": "mode: By Processes",
            "btn_about": "ℹ About Program",
            "user_proc_tab": "User Processes",
            "system_proc_tab": "System Processes",
            "blacklist_tab": "Blacklist",
            "whitelist_tab": "Whitelist",
            "status_tab": "Status",
            "invalid_ip": "Invalid IP address",
            "netsh_error_title": "Error",
            "netsh_error_msg": "netsh.exe not found in system.\nPlease ensure Windows is installed correctly."
        }
    }

    def __init__(self):
        super().__init__()
        self.title("CyberFireWall")
        self.geometry(f"{Config.WINDOW_WIDTH}x{Config.WINDOW_HEIGHT}")
        self.resizable(False, False)

        self.icon_img = ImageTk.PhotoImage(self.get_firewall_icon(128))
        try:
            self.iconphoto(True, self.icon_img)
        except Exception:
            pass

        # ---- Инициализация сервисов ----
        self.firewall = FirewallService()
        storage_path_black = self.get_data_file_path('blacklist.txt')
        self.storage = StorageService(storage_path_black)
        self.monitor = MonitoringService(interval_sec=Config.MONITOR_INTERVAL_SEC)

        # ---- Переменные состояния ----
        self.current_lang = "RU"
        self.current_theme = "Dark"
        self.aggregate_mode = False
        self.blacklist_lock = threading.Lock()

        # Загрузка чёрного списка из файла
        self.blacklist_ips = self.storage.load_blacklist()

        # Белый список - жёстко задан, как в оригинале
        self.whitelist_ips = ["8.8.8.8", "8.8.4.4", "1.1.1.1", "77.88.8.8", "127.0.0.1"]

        # ---- Состояние для логов ----
        self.last_user_content = ""
        self.last_system_content = ""
        self.last_raw_data_full = {}

        # ---- UI ----
        self.init_ui()
        self.update_interface_text()
        self.update_blacklist_display()
        self.update_status_indicator()
        self.update_tab_titles()

        # ---- Подписка на события мониторинга ----
        self.monitor.on('update', self.on_monitor_update)

        # ---- Синхронизация с брандмауэром (фон) ----
        threading.Thread(target=self._sync_in_background, daemon=True).start()

        # ---- Трей ----
        self.tray_icon = None
        threading.Thread(target=self.init_tray, daemon=True).start()

        self.protocol('WM_DELETE_WINDOW', self.hide_to_tray)

    # ==================== ФОНОВАЯ СИНХРОНИЗАЦИЯ ====================
    def _sync_in_background(self):
        """Синхронизирует память с брандмауэром без задержки UI."""
        fw_ips = self.firewall.get_blocked_ips()
        changed = False
        with self.blacklist_lock:
            for ip in fw_ips:
                if ip not in self.blacklist_ips:
                    self.blacklist_ips.add(ip)
                    self.storage.add_to_blacklist(ip)
                    changed = True
        if changed:
            self.after(0, self.update_blacklist_display)

    # ==================== РАБОТА С ФАЙЛАМИ ====================
    def get_data_file_path(self, filename: str) -> str:
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        folder = os.path.join(appdata, 'CyberFirewall')
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, filename)

    # ==================== UI ИНИЦИАЛИЗАЦИЯ ====================
    def init_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=Config.SIDEBAR_WIDTH, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.pack_propagate(False)
        ctk.CTkLabel(self.sidebar, text="CyberFireWall", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=25)

        self.btn_monitor = ctk.CTkButton(self.sidebar, text="", height=36, corner_radius=8,
                                         command=self.toggle_monitoring, fg_color="#1abc9c", hover_color="#16a085")
        self.btn_monitor.pack(pady=6, padx=15, fill="x")
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

        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=15, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=4)
        self.main_frame.grid_rowconfigure(1, weight=1)

        self.process_tabs = ctk.CTkTabview(self.main_frame)
        self.process_tabs.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.tab_user = self.process_tabs.add("User")
        self.tab_system = self.process_tabs.add("System")

        log_font = ctk.CTkFont(family=Config.LOG_FONT_FAMILY, size=Config.LOG_FONT_SIZE, weight="normal")
        self.user_log_area = ctk.CTkTextbox(self.tab_user, font=log_font, wrap="none", state="disabled")
        self.user_log_area.pack(fill="both", expand=True, padx=2, pady=2)
        self.system_log_area = ctk.CTkTextbox(self.tab_system, font=log_font, wrap="none", state="disabled")
        self.system_log_area.pack(fill="both", expand=True, padx=2, pady=2)

        self.tabview = ctk.CTkTabview(self.main_frame, height=120)
        self.tabview.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.tab_black = self.tabview.add("Black")
        self.tab_white = self.tabview.add("White")
        self.tab_status = self.tabview.add("Status")

        self.blacklist_frame = ctk.CTkScrollableFrame(self.tab_black, label_text="")
        self.blacklist_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.tab_black.grid_columnconfigure(0, weight=1)
        self.tab_black.grid_rowconfigure(0, weight=1)
        self.blacklist_widgets = {}

        black_entry_frame = ctk.CTkFrame(self.tab_black, fg_color="transparent")
        black_entry_frame.grid(row=1, column=0, padx=5, pady=(0,5), sticky="ew")
        black_entry_frame.grid_columnconfigure(0, weight=3)
        black_entry_frame.grid_columnconfigure(1, weight=1)
        black_entry_frame.grid_columnconfigure(2, weight=1)
        self.entry_ip = ctk.CTkEntry(black_entry_frame, height=Config.BLACKLIST_ENTRY_HEIGHT)
        self.entry_ip.grid(row=0, column=0, padx=2, sticky="ew")
        self.btn_block = ctk.CTkButton(black_entry_frame, text="", height=28, command=self.block_ip_event, fg_color="#e74c3c")
        self.btn_block.grid(row=0, column=1, padx=2, sticky="ew")
        self.btn_unblock = ctk.CTkButton(black_entry_frame, text="", height=28, command=self.unblock_ip_event, fg_color="#f39c12")
        self.btn_unblock.grid(row=0, column=2, padx=2, sticky="ew")

        self.tab_white.grid_columnconfigure(0, weight=1)
        self.btn_show_white = ctk.CTkButton(self.tab_white, text="", height=32, command=self.show_whitelist, fg_color="#7f8c8d")
        self.btn_show_white.grid(row=0, column=0, padx=5, pady=15, sticky="ew")

        self.tab_status.grid_columnconfigure(0, weight=1)
        self.status_indicator = ctk.CTkLabel(self.tab_status, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self.status_indicator.grid(row=0, column=0, padx=5, pady=15, sticky="ew")

    # ==================== ОБНОВЛЕНИЕ ЗАГОЛОВКОВ ВКЛАДОК ====================
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

    # ==================== ОПРЕДЕЛЕНИЕ СИСТЕМНЫХ ПРОЦЕССОВ ====================
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

    # ==================== ОТОБРАЖЕНИЕ ЧЁРНОГО СПИСКА ====================
    def update_blacklist_display(self):
        for widget in self.blacklist_frame.winfo_children():
            widget.destroy()
        self.blacklist_widgets.clear()

        with self.blacklist_lock:
            if not self.blacklist_ips:
                lbl = ctk.CTkLabel(self.blacklist_frame, text="Нет заблокированных IP" if self.current_lang == "RU" else "No blocked IPs",
                                   font=ctk.CTkFont(size=12))
                lbl.pack(pady=10)
                return
            ips_sorted = sorted(self.blacklist_ips)

        for ip in ips_sorted:
            frame = ctk.CTkFrame(self.blacklist_frame)
            frame.pack(fill="x", padx=5, pady=2)
            lbl_ip = ctk.CTkLabel(frame, text=ip, font=ctk.CTkFont(size=12), anchor="w")
            lbl_ip.pack(side="left", padx=5, pady=2, fill="x", expand=True)
            btn_del = ctk.CTkButton(frame, text="❌", width=30, height=28,
                                     fg_color="#c0392b", hover_color="#e74c3c",
                                     command=lambda ip_addr=ip: self.unblock_ip(ip_addr))
            btn_del.pack(side="right", padx=5, pady=2)
            self.blacklist_widgets[ip] = frame

    # ==================== ЛОГИКА БЛОКИРОВКИ / РАЗБЛОКИРОВКИ ====================
    def block_ip_event(self):
        ip = self.entry_ip.get().strip()
        lang = self.lang_data[self.current_lang]
        if not ip:
            self.log_message(self.user_log_area, lang["err_empty"])
            return
        if not FirewallService.is_valid_ip(ip):
            self.log_message(self.user_log_area, lang["invalid_ip"])
            return
        if ip in self.whitelist_ips:
            messagebox.showerror(title=lang["deny_title"], message=lang["deny_text"].format(ip))
            return
        self.execute_block(ip)

    def execute_block(self, ip):
        lang = self.lang_data[self.current_lang]
        with self.blacklist_lock:
            if ip in self.blacklist_ips:
                self.log_message(self.user_log_area, lang["info_blocked"].format(ip))
                return
        if self.firewall.block_ip(ip):
            with self.blacklist_lock:
                self.blacklist_ips.add(ip)
            self.storage.add_to_blacklist(ip)
            self.log_message(self.user_log_area, lang["success_block"].format(ip))
            self.update_blacklist_display()
            self.send_notification(lang["notify_title_block"], lang["notify_body_block"].format(ip))
        else:
            self.log_message(self.user_log_area, lang["err_fw"].format(ip, "Firewall Error"))

    def unblock_ip(self, ip):
        lang = self.lang_data[self.current_lang]
        with self.blacklist_lock:
            if ip not in self.blacklist_ips:
                self.log_message(self.user_log_area, lang["unblock_ip_not_found"].format(ip))
                return
        if self.firewall.unblock_ip(ip):
            with self.blacklist_lock:
                self.blacklist_ips.discard(ip)
            self.storage.remove_from_blacklist(ip)
            self.log_message(self.user_log_area, lang["unblock_ip_success"].format(ip))
            self.update_blacklist_display()
            self.send_notification(lang["notify_title_unblock"], lang["notify_body_unblock"].format(ip))
        else:
            self.log_message(self.user_log_area, lang["err_exec"].format("Ошибка удаления правила"))

    def unblock_ip_event(self):
        ip = self.entry_ip.get().strip()
        lang = self.lang_data[self.current_lang]
        if not ip:
            self.log_message(self.user_log_area, lang["err_empty"])
            return
        if not FirewallService.is_valid_ip(ip):
            self.log_message(self.user_log_area, lang["invalid_ip"])
            return
        self.unblock_ip(ip)

    # ==================== МОНИТОРИНГ ====================
    def toggle_monitoring(self):
        lang = self.lang_data[self.current_lang]
        if self.monitor.is_running():
            self.monitor.stop()
            self.btn_monitor.configure(text=lang["start_mon"], fg_color="#1abc9c")
            self.status_lbl.configure(text=lang["status_stop"], text_color="#e74c3c")
            self.log_message(self.user_log_area, f"\n[#] {lang['status_stop']}\n")
            self.clear_monitoring_logs()
        else:
            self.monitor.start()
            self.btn_monitor.configure(text=lang["stop_mon"], fg_color="#e74c3c")
            self.status_lbl.configure(text=lang["status_scan"], text_color="#27ae60")
            self.log_message(self.user_log_area, f"\n[*] {lang['status_scan']}\n")
        self.update_status_indicator()

    def on_monitor_update(self, raw_data):
        self.last_raw_data_full = raw_data
        self.after(0, self._update_logs_from_raw_data)

    def _update_logs_from_raw_data(self):
        lang = self.lang_data[self.current_lang]
        data_copy = self.last_raw_data_full.copy()
        if not data_copy:
            return

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
                yview = self.user_log_area.yview()
                self.user_log_area.configure(state="normal")
                self.user_log_area.delete("0.0", "end")
                self.user_log_area.insert("0.0", user_text)
                self.user_log_area.configure(state="disabled")
                self.user_log_area.yview_moveto(yview[0])

        if system_text != self.last_system_content:
            self.last_system_content = system_text
            if self.system_log_area:
                yview = self.system_log_area.yview()
                self.system_log_area.configure(state="normal")
                self.system_log_area.delete("0.0", "end")
                self.system_log_area.insert("0.0", system_text)
                self.system_log_area.configure(state="disabled")
                self.system_log_area.yview_moveto(yview[0])

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
        if self.last_raw_data_full:
            self.after(0, self._update_logs_from_raw_data)

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
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

    def update_status_indicator(self):
        lang = self.lang_data[self.current_lang]
        if self.monitor.is_running():
            self.status_indicator.configure(text="🟢 " + lang["status_scan"], text_color="#27ae60")
        else:
            self.status_indicator.configure(text="🔴 " + lang["status_stop"], text_color="#e74c3c")

    def show_whitelist(self):
        lang = self.lang_data[self.current_lang]
        white_text = lang["white_header"] + "".join([f" • {ip}\n" for ip in self.whitelist_ips])
        messagebox.showinfo(title=lang["white_title"], message=white_text)

    def show_about_info(self):
        lang = self.lang_data[self.current_lang]
        about_win = ctk.CTkToplevel(self)
        about_win.title(lang["about_title"])
        about_win.geometry(f"{Config.ABOUT_WIN_WIDTH}x{Config.ABOUT_WIN_HEIGHT}")
        about_win.resizable(False, False)
        about_win.transient(self)
        about_win.grab_set()

        x = self.winfo_x() + (self.winfo_width() // 2) - Config.ABOUT_WIN_WIDTH // 2
        y = self.winfo_y() + (self.winfo_height() // 2) - Config.ABOUT_WIN_HEIGHT // 2
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

    # ==================== ИКОНКА В ТРЕЕ ====================
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
        icon = self.get_firewall_icon(Config.TRAY_ICON_SIZE)
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
        if self.monitor.is_running():
            self.monitor.stop()
        if self.tray_icon:
            self.tray_icon.stop()
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

    # ==================== НАСТРОЙКИ ЯЗЫКА И ТЕМЫ ====================
    def toggle_language(self):
        self.current_lang = "EN" if self.current_lang == "RU" else "RU"
        self.btn_lang.configure(text="🌐 EN" if self.current_lang == "RU" else "🌐 RU")
        self.update_interface_text()
        self.update_blacklist_display()
        self.update_status_indicator()
        self.update_tab_titles()
        if self.last_raw_data_full:
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
        self.btn_monitor.configure(text=lang["start_mon"] if not self.monitor.is_running() else lang["stop_mon"])
        self.btn_toggle_mode.configure(text=lang["mode_detailed"] if not self.aggregate_mode else lang["mode_aggregate"])
        self.btn_about.configure(text=lang["btn_about"])
        self.btn_theme.configure(text="☀ Light" if self.current_theme == "Dark" else "🌙 Dark")
        self.settings_lbl.configure(text=lang["settings_lbl"])
        self.btn_block.configure(text="🚫 Block IP" if self.current_lang == "EN" else "🚫 Блокировать")
        self.btn_unblock.configure(text="🔓 Unblock IP" if self.current_lang == "EN" else "🔓 Разблокировать")
        self.btn_show_white.configure(text="📋 Show Whitelist" if self.current_lang == "EN" else "📋 Показать Белый Список")
        self.status_lbl.configure(text=lang["status_ready"] if not self.monitor.is_running() else lang["status_scan"])

# ==================== ТОЧКА ВХОДА ====================
if __name__ == "__main__":
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
