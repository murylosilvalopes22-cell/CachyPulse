"""
CrystalDiskMark-Grade Storage Benchmark for CachyPulse (Linux).
Bypasses Linux page cache using POSIX O_DIRECT & O_SYNC with page-aligned buffers.
Measures Sequential 1MB Read/Write (MB/s), 4K QD1 IOPS & Latency, and 4K QD8 Parallel IOPS.
"""

import os
import mmap
import time
import random
import concurrent.futures

BLOCK_SIZE = 1024 * 1024 # 1 MB
SMALL_SIZE = 4096        # 4 KB

class DiskBenchmark:
    def __init__(self):
        self.canceled = False

    def cancel(self):
        self.canceled = True

    def run(self, target_dir="/tmp", test_size_mb=512, progress_cb=None):
        self.canceled = False
        bench_dir = os.path.join(target_dir, "cachypulse_bench")
        os.makedirs(bench_dir, exist_ok=True)
        file_path = os.path.join(bench_dir, "bench.tmp")
        total_bytes = test_size_mb * 1024 * 1024

        # Page-aligned buffer via anonymous mmap
        buf_1m = mmap.mmap(-1, BLOCK_SIZE)
        # Fill with random non-compressible pattern
        random_bytes = os.urandom(65536)
        for i in range(16):
            buf_1m.write(random_bytes)
        buf_1m.seek(0)

        results = {
            "seq_write_mbs": 0.0,
            "seq_read_mbs": 0.0,
            "read_iops_q1": 0.0,
            "write_iops_q1": 0.0,
            "read_lat_us": 0.0,
            "write_lat_us": 0.0,
            "read_iops_q8": 0.0
        }

        flags = os.O_RDWR | os.O_CREAT | os.O_SYNC
        if hasattr(os, "O_DIRECT"):
            flags |= os.O_DIRECT

        try:
            fd = os.open(file_path, flags, 0o666)

            # 1. Sequential Write
            if progress_cb: progress_cb("Escrita Sequencial (1 MB)...", 0.05)
            t0 = time.time()
            written = 0
            while written < total_bytes:
                if self.canceled: break
                os.write(fd, buf_1m)
                written += BLOCK_SIZE
                if progress_cb and (written % (64 * 1024 * 1024) == 0):
                    progress_cb("Escrita Sequencial (1 MB)...", 0.05 + 0.25 * (written / total_bytes))
            t_write = time.time() - t0
            results["seq_write_mbs"] = round((written / (1024 * 1024)) / t_write, 1)

            # 2. Sequential Read
            if not self.canceled:
                if progress_cb: progress_cb("Leitura Sequencial (1 MB)...", 0.30)
                os.lseek(fd, 0, os.SEEK_SET)
                t0 = time.time()
                read_bytes = 0
                while read_bytes < total_bytes:
                    if self.canceled: break
                    data = os.read(fd, BLOCK_SIZE)
                    if not data: break
                    read_bytes += len(data)
                    if progress_cb and (read_bytes % (64 * 1024 * 1024) == 0):
                        progress_cb("Leitura Sequencial (1 MB)...", 0.30 + 0.25 * (read_bytes / total_bytes))
                t_read = time.time() - t0
                results["seq_read_mbs"] = round((read_bytes / (1024 * 1024)) / t_read, 1)

            # 3. Random 4K QD1 Read
            num_slots = total_bytes // SMALL_SIZE
            buf_4k = mmap.mmap(-1, SMALL_SIZE)
            buf_4k.write(os.urandom(SMALL_SIZE))
            buf_4k.seek(0)

            if not self.canceled:
                if progress_cb: progress_cb("Leitura 4K Aleatória (QD1)...", 0.60)
                ops = 0
                t0 = time.time()
                end_time = t0 + 3.0 # 3 seconds test
                while time.time() < end_time and not self.canceled:
                    slot = random.randint(0, num_slots - 1)
                    os.lseek(fd, slot * SMALL_SIZE, os.SEEK_SET)
                    os.read(fd, SMALL_SIZE)
                    ops += 1
                t_dur = time.time() - t0
                results["read_iops_q1"] = round(ops / t_dur, 0)
                results["read_lat_us"] = round((t_dur / max(ops, 1)) * 1e6, 1)

            # 4. Random 4K QD1 Write
            if not self.canceled:
                if progress_cb: progress_cb("Escrita 4K Aleatória (QD1)...", 0.75)
                ops = 0
                t0 = time.time()
                end_time = t0 + 3.0
                while time.time() < end_time and not self.canceled:
                    slot = random.randint(0, num_slots - 1)
                    os.lseek(fd, slot * SMALL_SIZE, os.SEEK_SET)
                    os.write(fd, buf_4k)
                    ops += 1
                t_dur = time.time() - t0
                results["write_iops_q1"] = round(ops / t_dur, 0)
                results["write_lat_us"] = round((t_dur / max(ops, 1)) * 1e6, 1)

            # 5. Random 4K QD8 Parallel Read
            if not self.canceled:
                if progress_cb: progress_cb("Leitura 4K Aleatória QD8 (Paralela)...", 0.90)
                total_ops = 0
                t0 = time.time()

                def worker_q8():
                    w_fd = os.open(file_path, flags, 0o666)
                    w_ops = 0
                    end_t = time.time() + 3.0
                    while time.time() < end_t and not self.canceled:
                        slot = random.randint(0, num_slots - 1)
                        os.lseek(w_fd, slot * SMALL_SIZE, os.SEEK_SET)
                        os.read(w_fd, SMALL_SIZE)
                        w_ops += 1
                    os.close(w_fd)
                    return w_ops

                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                    futures = [executor.submit(worker_q8) for _ in range(8)]
                    for f in futures:
                        total_ops += f.result()
                t_dur = time.time() - t0
                results["read_iops_q8"] = round(total_ops / t_dur, 0)

            os.close(fd)
            buf_1m.close()
            buf_4k.close()

        finally:
            if os.path.exists(file_path):
                try: os.remove(file_path)
                except Exception: pass
            if os.path.exists(bench_dir):
                try: os.rmdir(bench_dir)
                except Exception: pass

        if progress_cb: progress_cb("Benchmark de disco finalizado!", 1.0)
        return results
