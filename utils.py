import sys
import os
import ctypes
import atexit
import subprocess
from PIL import Image, ImageDraw

def init_system_wide_mutex():
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

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def enforce_admin():
    if not is_admin():
        cmd_line = subprocess.list2cmdline(sys.argv)
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, cmd_line, None, 1)
        sys.exit()

def get_firewall_icon(size=128):
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
