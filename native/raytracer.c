#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#include <string.h>
#include <omp.h>

#define WIDTH 960
#define HEIGHT 540
#define BUCKET_SIZE 32
#define MAX_DEPTH 6
#define LAMP_POWER 9.0f

typedef struct { float x, y, z; } Vec3;

static inline Vec3 v3_add(Vec3 a, Vec3 b) { return (Vec3){a.x + b.x, a.y + b.y, a.z + b.z}; }
static inline Vec3 v3_sub(Vec3 a, Vec3 b) { return (Vec3){a.x - b.x, a.y - b.y, a.z - b.z}; }
static inline Vec3 v3_mul(Vec3 a, float s) { return (Vec3){a.x * s, a.y * s, a.z * s}; }
static inline Vec3 v3_mulv(Vec3 a, Vec3 b) { return (Vec3){a.x * b.x, a.y * b.y, a.z * b.z}; }
static inline float v3_dot(Vec3 a, Vec3 b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
static inline Vec3 v3_cross(Vec3 a, Vec3 b) {
    return (Vec3){
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x
    };
}
static inline float v3_length(Vec3 a) { return sqrtf(v3_dot(a, a)); }
static inline Vec3 v3_norm(Vec3 a) {
    float l = v3_length(a);
    return l > 1e-8f ? v3_mul(a, 1.0f / l) : (Vec3){0, 0, 0};
}
static inline Vec3 v3_reflect(Vec3 v, Vec3 n) {
    return v3_sub(v, v3_mul(n, 2.0f * v3_dot(v, n)));
}

typedef enum { MAT_DIFFUSE = 0, MAT_METAL = 1, MAT_GLASS = 2, MAT_LIGHT = 3 } MatType;

typedef struct {
    Vec3 center;
    float radius;
    MatType mat;
    float albedo;
    float rough;
} Sphere;

#define NUM_SPHERES 19
static Sphere spheres[NUM_SPHERES];
static Sphere lamp_sphere = {{-4.0f, 7.0f, -3.0f}, 2.2f, MAT_LIGHT, 0.0f, 0.0f};

static void init_scene(void) {
    spheres[0] = (Sphere){{0.0f, 1.1f, 0.0f}, 1.1f, MAT_GLASS, 0.98f, 0.0f};
    spheres[1] = (Sphere){{-2.5f, 0.9f, 0.9f}, 0.9f, MAT_METAL, 0.92f, 0.03f};
    spheres[2] = (Sphere){{2.4f, 0.8f, 0.7f}, 0.8f, MAT_DIFFUSE, 0.85f, 0.0f};
    spheres[3] = (Sphere){{1.0f, 0.45f, -1.9f}, 0.45f, MAT_METAL, 0.85f, 0.25f};
    spheres[4] = (Sphere){{-1.1f, 0.35f, -2.0f}, 0.35f, MAT_DIFFUSE, 0.15f, 0.0f};

    for (int i = 0; i < 14; i++) {
        float a = ((float)i / 14.0f) * 6.2831853f;
        MatType m = (i % 3 == 0) ? MAT_METAL : ((i % 3 == 1) ? MAT_DIFFUSE : MAT_GLASS);
        float albedo = (i % 2 == 0) ? 0.9f : 0.3f;
        spheres[5 + i] = (Sphere){
            {cosf(a) * 4.2f, 0.28f, sinf(a) * 4.2f + 1.5f},
            0.28f, m, albedo, 0.1f
        };
    }
}

// Pseudo-random generator (LCG / PCG fast hash)
static inline float rnd(uint32_t *seed) {
    *seed = *seed * 1664525u + 1013904223u;
    return (*seed >> 8) * (1.0f / 16777216.0f);
}

static inline Vec3 random_in_unit_sphere(uint32_t *seed) {
    while (1) {
        Vec3 p = {rnd(seed) * 2.0f - 1.0f, rnd(seed) * 2.0f - 1.0f, rnd(seed) * 2.0f - 1.0f};
        if (v3_dot(p, p) < 1.0f) return p;
    }
}

static inline Vec3 cosine_hemisphere(Vec3 n, uint32_t *seed) {
    float u = rnd(seed), v = rnd(seed);
    float r = sqrtf(u), phi = 6.2831853f * v;
    Vec3 p = {r * cosf(phi), r * sinf(phi), sqrtf(1.0f - u)};
    Vec3 up = fabsf(n.z) < 0.999f ? (Vec3){0, 0, 1} : (Vec3){1, 0, 0};
    Vec3 tx = v3_norm(v3_cross(up, n));
    Vec3 ty = v3_cross(n, tx);
    return v3_add(v3_add(v3_mul(tx, p.x), v3_mul(ty, p.y)), v3_mul(n, p.z));
}

static inline bool intersect_sphere(Vec3 ro, Vec3 rd, Sphere s, float *t) {
    Vec3 oc = v3_sub(ro, s.center);
    float b = v3_dot(oc, rd);
    float c = v3_dot(oc, oc) - s.radius * s.radius;
    float disc = b * b - c;
    if (disc > 0.0f) {
        float sdisc = sqrtf(disc);
        float t0 = -b - sdisc;
        if (t0 > 0.001f) { *t = t0; return true; }
        float t1 = -b + sdisc;
        if (t1 > 0.001f) { *t = t1; return true; }
    }
    return false;
}

static inline bool scene_intersect(Vec3 ro, Vec3 rd, float *out_t, int *out_idx, bool *out_lamp) {
    float t_min = 1e30f;
    int hit_idx = -2;
    bool is_lamp = false;

    // Ground plane y = 0
    if (fabsf(rd.y) > 1e-4f) {
        float t = -ro.y / rd.y;
        if (t > 0.001f && t < t_min) {
            t_min = t;
            hit_idx = -1; // Ground
        }
    }

    // Lamp
    float t_lamp;
    if (intersect_sphere(ro, rd, lamp_sphere, &t_lamp)) {
        if (t_lamp > 0.001f && t_lamp < t_min) {
            t_min = t_lamp;
            hit_idx = -2;
            is_lamp = true;
        }
    }

    // Spheres
    for (int i = 0; i < NUM_SPHERES; i++) {
        float t;
        if (intersect_sphere(ro, rd, spheres[i], &t)) {
            if (t > 0.001f && t < t_min) {
                t_min = t;
                hit_idx = i;
                is_lamp = false;
            }
        }
    }

    if (hit_idx != -2 || is_lamp) {
        *out_t = t_min;
        *out_idx = hit_idx;
        *out_lamp = is_lamp;
        return true;
    }
    return false;
}

static inline float sky(Vec3 d) {
    float t = 0.5f * (d.y + 1.0f);
    return 0.15f + 0.25f * t;
}

static inline bool refract_vec(Vec3 v, Vec3 n, float ni_over_nt, Vec3 *refracted) {
    Vec3 uv = v3_norm(v);
    float dt = v3_dot(uv, n);
    float disc = 1.0f - ni_over_nt * ni_over_nt * (1.0f - dt * dt);
    if (disc > 0.0f) {
        *refracted = v3_sub(v3_mul(v3_sub(uv, v3_mul(n, dt)), ni_over_nt), v3_mul(n, sqrtf(disc)));
        return true;
    }
    return false;
}

static inline float schlick(float cosine, float ref_idx) {
    float r0 = (1.0f - ref_idx) / (1.0f + ref_idx);
    r0 = r0 * r0;
    return r0 + (1.0f - r0) * powf(1.0f - cosine, 5.0f);
}

static float trace_ray(Vec3 ro, Vec3 rd, uint32_t *seed) {
    float radiance = 0.0f;
    float throughput = 1.0f;
    bool specular = true;

    for (int depth = 0; depth < MAX_DEPTH; depth++) {
        float t;
        int idx;
        bool is_lamp;
        if (!scene_intersect(ro, rd, &t, &idx, &is_lamp)) {
            radiance += throughput * sky(rd);
            break;
        }

        if (is_lamp) {
            if (specular) radiance += throughput * LAMP_POWER;
            break;
        }

        Vec3 p = v3_add(ro, v3_mul(rd, t));
        Vec3 n;
        MatType mat;
        float albedo, rough = 0.0f;

        if (idx < 0) {
            // Ground
            n = (Vec3){0.0f, 1.0f, 0.0f};
            mat = MAT_DIFFUSE;
            int cx = (int)floorf(p.x * 0.9f);
            int cz = (int)floorf(p.z * 0.9f);
            albedo = ((cx + cz) & 1) == 0 ? 0.62f : 0.38f;
        } else {
            Sphere sp = spheres[idx];
            n = v3_mul(v3_sub(p, sp.center), 1.0f / sp.radius);
            mat = sp.mat;
            albedo = sp.albedo;
            rough = sp.rough;
        }

        if (mat == MAT_DIFFUSE) {
            // Direct light
            Vec3 to_light = v3_sub(lamp_sphere.center, p);
            float dist2 = v3_dot(to_light, to_light);
            Vec3 l_dir = v3_norm(to_light);
            float cos_theta = v3_dot(n, l_dir);
            if (cos_theta > 0.0f) {
                float shadow_t; int s_idx; bool s_lamp;
                if (scene_intersect(p, l_dir, &shadow_t, &s_idx, &s_lamp) && s_lamp) {
                    radiance += throughput * albedo * (LAMP_POWER * cos_theta / (dist2 * 0.1f + 1.0f));
                }
            }
            ro = p;
            rd = cosine_hemisphere(n, seed);
            throughput *= albedo;
            specular = false;
        } else if (mat == MAT_METAL) {
            Vec3 refl = v3_reflect(v3_norm(rd), n);
            if (rough > 0.0f) {
                refl = v3_norm(v3_add(refl, v3_mul(random_in_unit_sphere(seed), rough)));
            }
            ro = p;
            rd = refl;
            throughput *= albedo;
            specular = true;
        } else if (mat == MAT_GLASS) {
            Vec3 outward_n;
            float ni_over_nt;
            float cosine;
            if (v3_dot(rd, n) > 0.0f) {
                outward_n = v3_mul(n, -1.0f);
                ni_over_nt = 1.5f;
                cosine = 1.5f * v3_dot(rd, n) / v3_length(rd);
            } else {
                outward_n = n;
                ni_over_nt = 1.0f / 1.5f;
                cosine = -v3_dot(rd, n) / v3_length(rd);
            }
            Vec3 refracted;
            float refl_prob = refract_vec(rd, outward_n, ni_over_nt, &refracted) ? schlick(cosine, 1.5f) : 1.0f;
            ro = p;
            if (rnd(seed) < refl_prob) {
                rd = v3_reflect(v3_norm(rd), n);
            } else {
                rd = refracted;
            }
            throughput *= albedo;
            specular = true;
        }

        if (throughput < 1e-4f) break;
    }

    return radiance;
}

// Camera vectors
static Vec3 cam_origin = {0.0f, 2.1f, -7.2f};
static Vec3 cam_lower, cam_horizontal, cam_vertical;

static void init_camera(void) {
    Vec3 target = {0.0f, 0.75f, 0.0f};
    float vfov = 38.0f * 3.14159265f / 180.0f;
    float aspect = (float)WIDTH / (float)HEIGHT;
    float hh = tanf(vfov / 2.0f);
    float hw = aspect * hh;
    Vec3 w = v3_norm(v3_sub(cam_origin, target));
    Vec3 u = v3_norm(v3_cross((Vec3){0, 1, 0}, w));
    Vec3 v = v3_cross(w, u);
    cam_lower = v3_sub(v3_sub(v3_add(cam_origin, v3_mul(v, hh)), v3_mul(u, hw)), w);
    cam_horizontal = v3_mul(u, 2.0f * hw);
    cam_vertical = v3_mul(v, -2.0f * hh);
}

typedef struct {
    int x, y, w, h;
} Bucket;

static Bucket *buckets = NULL;
static int total_buckets = 0;

static int compare_buckets(const void *a, const void *b) {
    const Bucket *ba = (const Bucket *)a;
    const Bucket *bb = (const Bucket *)b;
    float ca_x = ba->x + ba->w * 0.5f - WIDTH * 0.5f;
    float ca_y = (ba->y + ba->h * 0.5f - HEIGHT * 0.5f) * 1.6f;
    float dist_a = ca_x * ca_x + ca_y * ca_y;

    float cb_x = bb->x + bb->w * 0.5f - WIDTH * 0.5f;
    float cb_y = (bb->y + bb->h * 0.5f - HEIGHT * 0.5f) * 1.6f;
    float dist_b = cb_x * cb_x + cb_y * cb_y;

    return (dist_a > dist_b) - (dist_a < dist_b);
}

static void init_buckets(void) {
    if (buckets) return;
    int num_x = (WIDTH + BUCKET_SIZE - 1) / BUCKET_SIZE;
    int num_y = (HEIGHT + BUCKET_SIZE - 1) / BUCKET_SIZE;
    total_buckets = num_x * num_y;
    buckets = (Bucket *)malloc(total_buckets * sizeof(Bucket));

    int idx = 0;
    for (int y = 0; y < HEIGHT; y += BUCKET_SIZE) {
        for (int x = 0; x < WIDTH; x += BUCKET_SIZE) {
            int w = (x + BUCKET_SIZE > WIDTH) ? (WIDTH - x) : BUCKET_SIZE;
            int h = (y + BUCKET_SIZE > HEIGHT) ? (HEIGHT - y) : BUCKET_SIZE;
            buckets[idx++] = (Bucket){x, y, w, h};
        }
    }
    qsort(buckets, total_buckets, sizeof(Bucket), compare_buckets);
}

// Tone mapping
static inline uint32_t to_bgra(float v) {
    float tone = v / (1.0f + v);
    tone = powf(tone, 1.0f / 2.2f); // gamma
    int c = (int)(tone * 255.0f);
    if (c > 255) c = 255;
    if (c < 0) c = 0;
    return 0xFF000000u | ((uint32_t)c << 16) | ((uint32_t)c << 8) | (uint32_t)c;
}

// C-exported API for Python ctypes
void raytracer_init(void) {
    static bool inited = false;
    if (!inited) {
        init_scene();
        init_camera();
        init_buckets();
        inited = true;
    }
}

int raytracer_get_bucket_count(void) {
    raytracer_init();
    return total_buckets;
}

void raytracer_render_bucket(uint32_t *pixels, int bucket_idx, int spp, volatile int *cancel_flag) {
    if (bucket_idx < 0 || bucket_idx >= total_buckets) return;
    if (cancel_flag && *cancel_flag) return;

    Bucket b = buckets[bucket_idx];
    for (int y = b.y; y < b.y + b.h; y++) {
        if (cancel_flag && *cancel_flag) return;
        for (int x = b.x; x < b.x + b.w; x++) {
            uint32_t seed = (uint32_t)(y * WIDTH + x) * 9781u + 0x9E3779B9u;
            float sum = 0.0f;
            for (int s = 0; s < spp; s++) {
                float u = (x + rnd(&seed)) / (float)WIDTH;
                float v = (y + rnd(&seed)) / (float)HEIGHT;
                Vec3 rd = v3_norm(v3_add(v3_add(cam_lower, v3_mul(cam_horizontal, u)), v3_mul(cam_vertical, v)));
                rd = v3_sub(rd, cam_origin);
                rd = v3_norm(rd);
                float rad = trace_ray(cam_origin, rd, &seed);
                if (rad > 4.0f) rad = 4.0f; // clamp fireflies
                sum += rad;
            }
            pixels[y * WIDTH + x] = to_bgra(sum / (float)spp);
        }
    }
}

// Full multi-threaded benchmark function
// threads: number of CPU threads (e.g. 1 for single-core, 12 for multi-core)
// spp: samples per pixel (default 512 or 1024)
// progress_callback: called as buckets complete
typedef void (*ProgressCb)(int completed, int total, double elapsed_sec);

double raytracer_run_bench(uint32_t *pixels, int threads, int spp, ProgressCb cb, volatile int *cancel_flag) {
    raytracer_init();
    memset(pixels, 0, WIDTH * HEIGHT * sizeof(uint32_t));

    if (threads <= 0) threads = omp_get_max_threads();
    omp_set_num_threads(threads);

    double start_time = omp_get_wtime();
    int completed = 0;

    #pragma omp parallel for schedule(dynamic, 1)
    for (int i = 0; i < total_buckets; i++) {
        if (cancel_flag && *cancel_flag) continue;
        raytracer_render_bucket(pixels, i, spp, cancel_flag);

        #pragma omp atomic
        completed++;

        if (cb && (completed % 5 == 0 || completed == total_buckets)) {
            double now = omp_get_wtime();
            #pragma omp critical
            {
                cb(completed, total_buckets, now - start_time);
            }
        }
    }

    double elapsed = omp_get_wtime() - start_time;
    // Score formula: total samples / seconds / 10,000 (Cinebench principle)
    int64_t total_samples = (int64_t)WIDTH * HEIGHT * spp;
    double score = elapsed > 0 ? (double)total_samples / elapsed / 10000.0 : 0.0;
    return score;
}
