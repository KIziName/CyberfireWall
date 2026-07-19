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

LANG_DATA = {
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
