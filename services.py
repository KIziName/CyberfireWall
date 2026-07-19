import os
import time
import ipaddress
import threading
import subprocess
import psutil

class EventEmitter:
    def __init__(self):
        self._listeners = {}

    def on(self, event: str, callback):
        self._listeners.setdefault(event, []).append(callback)

    def emit(self, event: str, *args, **kwargs):
        for cb in self._listeners.get(event, []):
            cb(*args, **kwargs)

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

class StorageService:
    def __init__(self, blacklist_path: str):
        self.blacklist = BlacklistStorage(blacklist_path)

    def load_blacklist(self) -> set:
        return self.blacklist.load()

    def add_to_blacklist(self, ip: str) -> bool:
        return self.blacklist.add(ip)

    def remove_from_blacklist(self, ip: str) -> bool:
        return self.blacklist.remove(ip)

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
