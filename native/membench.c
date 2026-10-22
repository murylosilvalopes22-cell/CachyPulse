#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <time.h>
#include <omp.h>
#include <immintrin.h>

#define LATENCY_BYTES (256ULL * 1024ULL * 1024ULL) // 256 MB > L3 cache
#define BANDWIDTH_BYTES (1024ULL * 1024ULL * 1024ULL) // 1 GB buffer

typedef struct {
    double latency_ns;
    double read_gb_s;
    double write_gb_s;
    double copy_gb_s;
} MemBenchResult;

// Sattolo permutation for uniform single-cycle pointer chase
static void sattolo_shuffle(uint32_t *arr, size_t n, uint32_t *seed) {
    for (size_t i = n - 1; i > 0; i--) {
        *seed = *seed * 1664525u + 1013904223u;
        size_t j = *seed % i;
        uint32_t tmp = arr[i];
        arr[i] = arr[j];
        arr[j] = tmp;
    }
}

// Memory Latency test (sub-nanosecond precision)
double mem_measure_latency(volatile int *cancel_flag) {
    size_t line_size = 64; // 64-byte cache line
    size_t num_lines = LATENCY_BYTES / line_size;
    
    // Allocate 64-byte aligned memory
    uint64_t *buffer = NULL;
    if (posix_memalign((void **)&buffer, 64, LATENCY_BYTES) != 0 || !buffer) {
        return -1.0;
    }

    uint32_t *order = (uint32_t *)malloc(num_lines * sizeof(uint32_t));
    if (!order) {
        free(buffer);
        return -1.0;
    }

    for (size_t i = 0; i < num_lines; i++) {
        order[i] = (uint32_t)i;
    }

    uint32_t seed = 42u;
    sattolo_shuffle(order, num_lines, &seed);

    size_t words_per_line = line_size / sizeof(uint64_t);
    for (size_t i = 0; i < num_lines; i++) {
        size_t next_idx = order[(i + 1) % num_lines];
        buffer[order[i] * words_per_line] = (uint64_t)(next_idx * words_per_line);
    }
    free(order);

    // Warm-up TLB
    uint64_t curr = 0;
    for (int i = 0; i < 200000; i++) {
        curr = buffer[curr];
    }

    // Timed pointer chase: 20 million steps
    const int steps = 20000000;
    double t0 = omp_get_wtime();

    for (int i = 0; i < steps; i++) {
        curr = buffer[curr];
        if ((i & 0xFFFFF) == 0 && cancel_flag && *cancel_flag) break;
    }

    double elapsed = omp_get_wtime() - t0;
    free(buffer);

    // Prevent compiler dead-code elimination
    if (curr == 0xDEADBEEF) printf("%lu\n", curr);

    double ns_per_access = (elapsed * 1e9) / (double)steps;
    return ns_per_access;
}

// Multi-threaded Read Bandwidth (GB/s)
double mem_measure_read(int threads, volatile int *cancel_flag) {
    if (threads <= 0) threads = omp_get_max_threads();
    omp_set_num_threads(threads);

    uint64_t *src = NULL;
    if (posix_memalign((void **)&src, 64, BANDWIDTH_BYTES) != 0 || !src) return -1.0;

    size_t count = BANDWIDTH_BYTES / sizeof(uint64_t);
    #pragma omp parallel for schedule(static)
    for (size_t i = 0; i < count; i++) {
        src[i] = (uint64_t)i + 1;
    }

    double best_gb_s = 0.0;
    for (int rep = 0; rep < 3; rep++) {
        if (cancel_flag && *cancel_flag) break;
        uint64_t global_sum = 0;
        double t0 = omp_get_wtime();

        #pragma omp parallel reduction(+:global_sum)
        {
            int tid = omp_get_thread_num();
            size_t chunk = count / threads;
            size_t start = tid * chunk;
            size_t end = (tid == threads - 1) ? count : start + chunk;

            uint64_t s0 = 0, s1 = 0, s2 = 0, s3 = 0;
            for (size_t i = start; i + 3 < end; i += 4) {
                s0 += src[i];
                s1 += src[i + 1];
                s2 += src[i + 2];
                s3 += src[i + 3];
            }
            global_sum += (s0 + s1 + s2 + s3);
        }

        double elapsed = omp_get_wtime() - t0;
        if (global_sum == 0x12345678) printf("%lu\n", global_sum);

        double gb_s = ((double)BANDWIDTH_BYTES / 1e9) / elapsed;
        if (gb_s > best_gb_s) best_gb_s = gb_s;
    }

    free(src);
    return best_gb_s;
}

// Multi-threaded Write Bandwidth (GB/s)
double mem_measure_write(int threads, volatile int *cancel_flag) {
    if (threads <= 0) threads = omp_get_max_threads();
    omp_set_num_threads(threads);

    uint64_t *dst = NULL;
    if (posix_memalign((void **)&dst, 64, BANDWIDTH_BYTES) != 0 || !dst) return -1.0;

    size_t count = BANDWIDTH_BYTES / sizeof(uint64_t);

    double best_gb_s = 0.0;
    for (int rep = 0; rep < 3; rep++) {
        if (cancel_flag && *cancel_flag) break;
        double t0 = omp_get_wtime();

        #pragma omp parallel
        {
            int tid = omp_get_thread_num();
            size_t chunk = count / threads;
            size_t start = tid * chunk;
            size_t end = (tid == threads - 1) ? count : start + chunk;
            uint64_t val = (uint64_t)(rep + 1) * 0x9E3779B97F4A7C15ULL;

            for (size_t i = start; i + 3 < end; i += 4) {
                dst[i] = val;
                dst[i + 1] = val;
                dst[i + 2] = val;
                dst[i + 3] = val;
            }
        }

        double elapsed = omp_get_wtime() - t0;
        double gb_s = ((double)BANDWIDTH_BYTES / 1e9) / elapsed;
        if (gb_s > best_gb_s) best_gb_s = gb_s;
    }

    free(dst);
    return best_gb_s;
}

// Multi-threaded Copy Bandwidth (GB/s)
double mem_measure_copy(int threads, volatile int *cancel_flag) {
    if (threads <= 0) threads = omp_get_max_threads();
    omp_set_num_threads(threads);

    uint64_t *src = NULL;
    uint64_t *dst = NULL;
    if (posix_memalign((void **)&src, 64, BANDWIDTH_BYTES) != 0 || !src) return -1.0;
    if (posix_memalign((void **)&dst, 64, BANDWIDTH_BYTES) != 0 || !dst) {
        free(src);
        return -1.0;
    }

    size_t count = BANDWIDTH_BYTES / sizeof(uint64_t);
    #pragma omp parallel for schedule(static)
    for (size_t i = 0; i < count; i++) src[i] = (uint64_t)i;

    double best_gb_s = 0.0;
    for (int rep = 0; rep < 3; rep++) {
        if (cancel_flag && *cancel_flag) break;
        double t0 = omp_get_wtime();

        #pragma omp parallel
        {
            int tid = omp_get_thread_num();
            size_t chunk = count / threads;
            size_t start = tid * chunk;
            size_t end = (tid == threads - 1) ? count : start + chunk;
            size_t bytes = (end - start) * sizeof(uint64_t);

            memcpy(&dst[start], &src[start], bytes);
        }

        double elapsed = omp_get_wtime() - t0;
        // Copy reads from src and writes to dst (counts 2 * size, like AIDA64)
        double gb_s = (2.0 * (double)BANDWIDTH_BYTES / 1e9) / elapsed;
        if (gb_s > best_gb_s) best_gb_s = gb_s;
    }

    free(src);
    free(dst);
    return best_gb_s;
}

// Full AIDA64-grade test in one call
MemBenchResult mem_run_full_bench(int threads, volatile int *cancel_flag) {
    MemBenchResult res = {0};
    res.latency_ns = mem_measure_latency(cancel_flag);
    res.read_gb_s = mem_measure_read(threads, cancel_flag);
    res.write_gb_s = mem_measure_write(threads, cancel_flag);
    res.copy_gb_s = mem_measure_copy(threads, cancel_flag);
    return res;
}
