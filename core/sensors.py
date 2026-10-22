"""
Hardware Sensor Monitor for CachyPulse.
Runs a background collector thread reading hwmon (CPU, NVMe, Motherboard)
and NVML (NVIDIA GPU) every 1 second, maintaining real-time history queues.
"""

import time
import threading
import glob
import os
from collections import deque
import psutil
from .nvml_client import NvmlClient

class SensorRow:
    def __init__(self, category, name, value, unit, raw_val=0.0):
        self.category = category # CPU, GPU, RAM, Storage, Motherboard
        self.name = name
        self.value = value
        self.unit = unit
        self.raw_val = raw_val

class SensorMonitor:
    def __init__(self, history_len=120):
        self.history_len = history_len
        self.running = False
        self._thread = None
        self._lock = threading.Lock()
        self.nvml = NvmlClient()

        # Telemetry history (deque of floats)
        self.history = {
            "time": deque(maxlen=history_len),
            "cpu_load": deque(maxlen=history_len),
            "cpu_temp": deque(maxlen=history_len),
            "gpu_load": deque(maxlen=history_len),
            "gpu_temp": deque(maxlen=history_len),
            "vram_used": deque(maxlen=history_len),
            "ram_used": deque(maxlen=history_len),
            "power_draw": deque(maxlen=history_len)
        }

        # Current sensor list
        self.rows = []
        self.current_snapshot = {}

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="CachyPulseSensorThread")
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=1.5)
        self.nvml.close()

    def _read_cpu_temp(self):
        for h in glob.glob("/sys/class/hwmon/hwmon*"):
            name_file = os.path.join(h, "name")
            if os.path.exists(name_file):
                try:
                    with open(name_file) as f:
                        name = f.read().strip()
                    if name in ["k10temp", "coretemp", "zenpower"]:
                        # temp1 is usually Tctl / Package
                        t1 = os.path.join(h, "temp1_input")
                        if os.path.exists(t1):
                            with open(t1) as tf:
                                return float(tf.read().strip()) / 1000.0
                except Exception:
                    pass
        return 0.0

    def _read_nvme_temps(self):
        nvmes = []
        for h in glob.glob("/sys/class/hwmon/hwmon*"):
            name_file = os.path.join(h, "name")
            if os.path.exists(name_file):
                try:
                    with open(name_file) as f:
                        name = f.read().strip()
                    if name == "nvme":
                        t1 = os.path.join(h, "temp1_input")
                        if os.path.exists(t1):
                            with open(t1) as tf:
                                nvmes.append(float(tf.read().strip()) / 1000.0)
                except Exception:
                    pass
        return nvmes

    def _loop(self):
        while self.running:
            t0 = time.time()
            cpu_load = psutil.cpu_percent(interval=None)
            per_core = psutil.cpu_percent(interval=None, percpu=True)
            vm = psutil.virtual_memory()
            cpu_temp = self._read_cpu_temp()
            nvme_temps = self._read_nvme_temps()
            gpu_data = self.nvml.get_telemetry()

            gpu_load = gpu_data["gpu_load"] if gpu_data else 0.0
            gpu_temp = gpu_data["temp_c"] if gpu_data else 0.0
            vram_used = gpu_data["vram_used_mb"] if gpu_data else 0.0
            power_w = gpu_data["power_w"] if gpu_data else 0.0

            rows = []
            # CPU rows
            rows.append(SensorRow("CPU", "Uso Total da CPU", f"{cpu_load:.1f}", "%", cpu_load))
            rows.append(SensorRow("CPU", "Temperatura da CPU (Tctl)", f"{cpu_temp:.1f}", "°C", cpu_temp))
            for i, load in enumerate(per_core):
                rows.append(SensorRow("CPU", f"Núcleo #{i}", f"{load:.1f}", "%", load))

            # RAM rows
            rows.append(SensorRow("RAM", "Uso da Memória", f"{vm.percent:.1f}", "%", vm.percent))
            rows.append(SensorRow("RAM", "RAM Usada", f"{vm.used / (1024**3):.2f}", "GB", vm.used / (1024**3)))
            rows.append(SensorRow("RAM", "RAM Disponível", f"{vm.available / (1024**3):.2f}", "GB", vm.available / (1024**3)))

            # GPU rows
            if gpu_data:
                rows.append(SensorRow("GPU", "Carga do Núcleo GPU", f"{gpu_data['gpu_load']}", "%", gpu_data['gpu_load']))
                rows.append(SensorRow("GPU", "Temperatura da GPU", f"{gpu_data['temp_c']}", "°C", gpu_data['temp_c']))
                rows.append(SensorRow("GPU", "Consumo de Energia", f"{gpu_data['power_w']}", "W", gpu_data['power_w']))
                rows.append(SensorRow("GPU", "Clock do Núcleo", f"{gpu_data['clock_core_mhz']}", "MHz", gpu_data['clock_core_mhz']))
                rows.append(SensorRow("GPU", "Clock da Memória", f"{gpu_data['clock_mem_mhz']}", "MHz", gpu_data['clock_mem_mhz']))
                rows.append(SensorRow("GPU", "VRAM Usada", f"{gpu_data['vram_used_mb']}", "MB", gpu_data['vram_used_mb']))
                rows.append(SensorRow("GPU", "Ventoinha", f"{gpu_data['fan_pct']}", "%", gpu_data['fan_pct']))

            # Storage rows
            for idx, temp in enumerate(nvme_temps):
                rows.append(SensorRow("Armazenamento", f"NVMe #{idx+1} Temp", f"{temp:.1f}", "°C", temp))

            now_str = time.strftime("%H:%M:%S")

            with self._lock:
                self.rows = rows
                self.history["time"].append(now_str)
                self.history["cpu_load"].append(cpu_load)
                self.history["cpu_temp"].append(cpu_temp)
                self.history["gpu_load"].append(gpu_load)
                self.history["gpu_temp"].append(gpu_temp)
                self.history["vram_used"].append(vram_used)
                self.history["ram_used"].append(vm.used / (1024**3))
                self.history["power_draw"].append(power_w)

                self.current_snapshot = {
                    "cpu_load": cpu_load,
                    "cpu_temp": cpu_temp,
                    "per_core": per_core,
                    "ram_pct": vm.percent,
                    "ram_used_gb": vm.used / (1024**3),
                    "ram_total_gb": vm.total / (1024**3),
                    "gpu_load": gpu_load,
                    "gpu_temp": gpu_temp,
                    "vram_used_mb": vram_used,
                    "vram_total_mb": gpu_data["vram_total_mb"] if gpu_data else 0,
                    "power_w": power_w,
                    "clock_core": gpu_data["clock_core_mhz"] if gpu_data else 0,
                    "fan_pct": gpu_data["fan_pct"] if gpu_data else 0,
                    "thermal_slowdown": gpu_data["thermal_slowdown"] if gpu_data else False
                }

            time.sleep(max(0.2, 1.0 - (time.time() - t0)))

    def get_snapshot(self):
        with self._lock:
            return dict(self.current_snapshot)

    def get_history(self):
        with self._lock:
            return {k: list(v) for k, v in self.history.items()}

    def get_rows(self, category_filter=None, search=""):
        with self._lock:
            res = list(self.rows)

        if category_filter and category_filter != "Todos":
            res = [r for r in res if r.category == category_filter]
        if search:
            s = search.lower()
            res = [r for r in res if s in r.name.lower() or s in r.category.lower()]
        return res
