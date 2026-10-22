"""
CPU Path Tracer Benchmark (Cinebench principle) for CachyPulse.
Executes the native C-compiled path tracer with dynamic bucket scheduling.
Provides real-time tile rendering visualization and deterministic scoring.
"""

import os
import time
import ctypes
from ctypes import c_uint32, c_int, c_double, CFUNCTYPE, POINTER, byref

WIDTH = 960
HEIGHT = 540

PROGRESS_CB = CFUNCTYPE(None, c_int, c_int, c_double)

class CpuRaytracerBench:
    def __init__(self, lib_path=None):
        if not lib_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            lib_path = os.path.join(base_dir, "libcachypulse_native.so")

        self.lib = ctypes.CDLL(lib_path)
        self.lib.raytracer_init()
        self.lib.raytracer_get_bucket_count.restype = c_int
        self.lib.raytracer_run_bench.restype = c_double
        self.total_buckets = self.lib.raytracer_get_bucket_count()

        # Shared pixel buffer for Qt QImage rendering (BGRA32)
        self.pixel_buffer = (c_uint32 * (WIDTH * HEIGHT))()
        self.cancel_flag = c_int(0)
        self.running = False

    def cancel(self):
        self.cancel_flag.value = 1

    def run(self, threads=0, spp=256, on_progress=None):
        self.cancel_flag.value = 0
        self.running = True

        def c_callback(completed, total, elapsed):
            if on_progress:
                on_progress(completed, total, elapsed)

        cb_func = PROGRESS_CB(c_callback)
        score = self.lib.raytracer_run_bench(
            self.pixel_buffer,
            c_int(threads),
            c_int(spp),
            cb_func,
            byref(self.cancel_flag)
        )
        self.running = False
        return score

    def get_pixel_buffer_bytes(self):
        return ctypes.string_at(ctypes.addressof(self.pixel_buffer), WIDTH * HEIGHT * 4)
