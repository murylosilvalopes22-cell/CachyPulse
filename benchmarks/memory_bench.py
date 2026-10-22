"""
AIDA64-Grade Memory Benchmark for CachyPulse.
Measures true hardware DDR4/DDR5 cache-busting latency via Sattolo pointer chasing
and multi-threaded Read, Write, and Copy bandwidth in GB/s.
"""

import os
import ctypes
from ctypes import c_double, c_int, Structure, byref

class MemBenchResultC(Structure):
    _fields_ = [
        ("latency_ns", c_double),
        ("read_gb_s", c_double),
        ("write_gb_s", c_double),
        ("copy_gb_s", c_double)
    ]

class MemoryBenchmark:
    def __init__(self, lib_path=None):
        if not lib_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            lib_path = os.path.join(base_dir, "libcachypulse_native.so")

        self.lib = ctypes.CDLL(lib_path)
        self.lib.mem_run_full_bench.restype = MemBenchResultC
        self.lib.mem_measure_latency.restype = c_double
        self.lib.mem_measure_read.restype = c_double
        self.lib.mem_measure_write.restype = c_double
        self.lib.mem_measure_copy.restype = c_double

        self.cancel_flag = c_int(0)
        self.running = False

    def cancel(self):
        self.cancel_flag.value = 1

    def run_full(self, threads=0, progress_cb=None):
        self.cancel_flag.value = 0
        self.running = True

        if progress_cb: progress_cb("Medindo latência da RAM (Sattolo Pointer Chase)...", 0.1)
        lat = self.lib.mem_measure_latency(byref(self.cancel_flag))

        if self.cancel_flag.value:
            self.running = False
            return None

        if progress_cb: progress_cb("Medindo largura de banda de LEITURA (GB/s)...", 0.35)
        read_bw = self.lib.mem_measure_read(c_int(threads), byref(self.cancel_flag))

        if self.cancel_flag.value:
            self.running = False
            return None

        if progress_cb: progress_cb("Medindo largura de banda de ESCRITA (GB/s)...", 0.65)
        write_bw = self.lib.mem_measure_write(c_int(threads), byref(self.cancel_flag))

        if self.cancel_flag.value:
            self.running = False
            return None

        if progress_cb: progress_cb("Medindo largura de banda de CÓPIA (GB/s)...", 0.90)
        copy_bw = self.lib.mem_measure_copy(c_int(threads), byref(self.cancel_flag))

        if progress_cb: progress_cb("Benchmark de memória concluído!", 1.0)
        self.running = False

        return {
            "latency_ns": round(lat, 2),
            "read_gb_s": round(read_bw, 2),
            "write_gb_s": round(write_bw, 2),
            "copy_gb_s": round(copy_bw, 2)
        }
