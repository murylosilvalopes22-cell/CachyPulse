"""
NVML Client for CachyPulse.
Provides direct C-level hardware telemetry for NVIDIA GPUs via libnvidia-ml.so.1.
Zero subprocess overhead, microsecond latency.
"""

import ctypes
from ctypes import c_uint, c_ulonglong, c_void_p, byref, create_string_buffer, Structure, c_int
import os

class Utilization(Structure):
    _fields_ = [('gpu', c_uint), ('memory', c_uint)]

class Memory(Structure):
    _fields_ = [('total', c_ulonglong), ('free', c_ulonglong), ('used', c_ulonglong)]

class NvmlClient:
    def __init__(self):
        self.available = False
        self.lib = None
        self.handle = None
        self.device_name = ""
        self.driver_version = ""
        self._init_nvml()

    def _init_nvml(self):
        for lib_name in ["libnvidia-ml.so.1", "libnvidia-ml.so"]:
            try:
                self.lib = ctypes.CDLL(lib_name)
                ret = self.lib.nvmlInit_v2()
                if ret == 0:
                    self.available = True
                    break
            except Exception:
                continue

        if not self.available:
            return

        try:
            device_count = c_uint()
            self.lib.nvmlDeviceGetCount_v2(byref(device_count))
            if device_count.value > 0:
                h = c_void_p()
                if self.lib.nvmlDeviceGetHandleByIndex_v2(0, byref(h)) == 0:
                    self.handle = h
                    buf = create_string_buffer(64)
                    if self.lib.nvmlDeviceGetName(self.handle, buf, 64) == 0:
                        self.device_name = buf.value.decode("utf-8", errors="ignore")
                    v_buf = create_string_buffer(64)
                    if self.lib.nvmlSystemGetDriverVersion(v_buf, 64) == 0:
                        self.driver_version = v_buf.value.decode("utf-8", errors="ignore")
        except Exception:
            self.available = False

    def get_telemetry(self):
        """Returns real-time GPU telemetry dict, or None if unavailable."""
        if not self.available or not self.handle:
            return None

        telemetry = {
            "name": self.device_name,
            "driver": self.driver_version,
            "gpu_load": 0,
            "mem_util": 0,
            "vram_total_mb": 0,
            "vram_used_mb": 0,
            "vram_free_mb": 0,
            "vram_pct": 0.0,
            "temp_c": 0,
            "power_w": 0.0,
            "power_limit_w": 0.0,
            "clock_core_mhz": 0,
            "clock_mem_mhz": 0,
            "fan_pct": 0,
            "pstate": 0,
            "thermal_slowdown": False
        }

        try:
            util = Utilization()
            if self.lib.nvmlDeviceGetUtilizationRates(self.handle, byref(util)) == 0:
                telemetry["gpu_load"] = util.gpu
                telemetry["mem_util"] = util.memory

            mem = Memory()
            if self.lib.nvmlDeviceGetMemoryInfo(self.handle, byref(mem)) == 0:
                total_mb = mem.total // (1024 * 1024)
                used_mb = mem.used // (1024 * 1024)
                free_mb = mem.free // (1024 * 1024)
                telemetry["vram_total_mb"] = total_mb
                telemetry["vram_used_mb"] = used_mb
                telemetry["vram_free_mb"] = free_mb
                if total_mb > 0:
                    telemetry["vram_pct"] = round(100.0 * used_mb / total_mb, 1)

            temp = c_uint()
            if self.lib.nvmlDeviceGetTemperature(self.handle, 0, byref(temp)) == 0:
                telemetry["temp_c"] = temp.value

            power = c_uint()
            if self.lib.nvmlDeviceGetPowerUsage(self.handle, byref(power)) == 0:
                telemetry["power_w"] = round(power.value / 1000.0, 1)

            power_lim = c_uint()
            if hasattr(self.lib, "nvmlDeviceGetPowerManagementLimit"):
                if self.lib.nvmlDeviceGetPowerManagementLimit(self.handle, byref(power_lim)) == 0:
                    telemetry["power_limit_w"] = round(power_lim.value / 1000.0, 1)

            clock = c_uint()
            if self.lib.nvmlDeviceGetClockInfo(self.handle, 0, byref(clock)) == 0: # Graphics
                telemetry["clock_core_mhz"] = clock.value

            clock_mem = c_uint()
            if self.lib.nvmlDeviceGetClockInfo(self.handle, 2, byref(clock_mem)) == 0: # Mem
                telemetry["clock_mem_mhz"] = clock_mem.value

            fan = c_uint()
            if self.lib.nvmlDeviceGetFanSpeed(self.handle, byref(fan)) == 0:
                telemetry["fan_pct"] = fan.value

            pstate = c_int()
            if hasattr(self.lib, "nvmlDeviceGetPerformanceState"):
                if self.lib.nvmlDeviceGetPerformanceState(self.handle, byref(pstate)) == 0:
                    telemetry["pstate"] = pstate.value

            reasons = c_ulonglong()
            if hasattr(self.lib, "nvmlDeviceGetCurrentClocksThrottleReasons"):
                if self.lib.nvmlDeviceGetCurrentClocksThrottleReasons(self.handle, byref(reasons)) == 0:
                    # 0x0000000000000020 = SW Thermal Slowdown
                    # 0x0000000000000040 = HW Thermal Slowdown
                    telemetry["thermal_slowdown"] = bool(reasons.value & 0x60)

        except Exception:
            pass

        return telemetry

    def close(self):
        if self.available and self.lib:
            try:
                self.lib.nvmlShutdown()
            except Exception:
                pass
            self.available = False
