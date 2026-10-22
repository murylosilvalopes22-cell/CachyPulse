"""
System and Gaming Optimizer for CachyPulse (Linux & CachyOS).
Provides memory cache cleanup, ZRAM compaction, CPU governor management,
ananicy-cpp status, and background process management.
"""

import os
import subprocess
import psutil
import glob

class SystemOptimizer:
    @staticmethod
    def get_governors():
        govs = []
        cur = ""
        p_avail = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors"
        p_cur = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"

        if os.path.exists(p_avail):
            try:
                with open(p_avail) as f:
                    govs = f.read().strip().split()
            except Exception:
                govs = ["performance", "schedutil", "powersave"]

        if os.path.exists(p_cur):
            try:
                with open(p_cur) as f:
                    cur = f.read().strip()
            except Exception:
                cur = "performance"

        return {"available": govs, "current": cur}

    @staticmethod
    def set_governor(governor):
        """Sets scaling governor across all CPU cores via pkexec."""
        cmd = f"sh -c 'for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo {governor} > \"$g\"; done'"
        try:
            res = subprocess.run(["pkexec", "sh", "-c", cmd], capture_output=True, text=True, timeout=15)
            return res.returncode == 0
        except Exception as e:
            return False

    @staticmethod
    def drop_caches():
        """Drops Linux pagecache, dentries, and inodes via pkexec."""
        cmd = "sync && echo 3 > /proc/sys/vm/drop_caches"
        try:
            res = subprocess.run(["pkexec", "sh", "-c", cmd], capture_output=True, text=True, timeout=15)
            return res.returncode == 0
        except Exception:
            # Fallback to user-space sync
            os.system("sync")
            return False

    @staticmethod
    def compact_zram():
        """Triggers ZRAM memory compaction."""
        if not os.path.exists("/sys/block/zram0"):
            return False, "ZRAM não está ativo neste sistema."
        cmd = "echo 1 > /sys/block/zram0/compact"
        try:
            res = subprocess.run(["pkexec", "sh", "-c", cmd], capture_output=True, text=True, timeout=15)
            if res.returncode == 0:
                return True, "ZRAM compactado com sucesso!"
        except Exception:
            pass
        return False, "Falha ou permissão negada ao compactar ZRAM."

    @staticmethod
    def get_cachyos_services():
        """Checks status of performance services like ananicy-cpp and gamemoded."""
        services = {}
        for srv in ["ananicy-cpp", "gamemoded"]:
            try:
                res = subprocess.run(["systemctl", "is-active", srv], capture_output=True, text=True)
                services[srv] = (res.stdout.strip() == "active")
            except Exception:
                services[srv] = False
        return services

    @staticmethod
    def get_heavy_processes():
        """Returns list of processes consuming significant RAM."""
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'memory_percent', 'memory_info']):
            try:
                mem_mb = p.info['memory_info'].rss / (1024 * 1024)
                if mem_mb > 150: # Only apps using > 150 MB
                    procs.append({
                        "pid": p.info['pid'],
                        "name": p.info['name'],
                        "mem_mb": round(mem_mb, 1),
                        "mem_pct": round(p.info['memory_percent'], 1)
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda x: x["mem_mb"], reverse=True)
        return procs

    @staticmethod
    def terminate_process(pid):
        try:
            p = psutil.Process(pid)
            p.terminate()
            return True
        except Exception:
            return False
