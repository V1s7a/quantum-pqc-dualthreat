/*
 * decap_harness.c — Kyber decapsulation timing harness (educational)
 *
 * Measures OQS_KEM_decaps() time for clean vs. bit-flipped ciphertexts.
 * Outputs CSV to stdout:
 *   trial,class,flips,ns,seed,kem,decap_rc
 *
 * Build (static lib example):
 *   gcc -O2 -std=c11 \
 *     -I kyber_side-channel_poc/liboqs/build/include \
 *     -I kyber_side-channel_poc/liboqs/include \
 *     kyber_side-channel_poc/decap_harness.c \
 *     kyber_side-channel_poc/liboqs/build/lib/liboqs.a -lm \
 *     -o kyber_side-channel_poc/decap_harness
 *
 * Build (shared lib example):
 *   gcc -O2 -std=c11 \
 *     -I kyber_side-channel_poc/liboqs/build/include \
 *     -I kyber_side-channel_poc/liboqs/include \
 *     kyber_side-channel_poc/decap_harness.c \
 *     -L kyber_side-channel_poc/liboqs/build/lib -loqs -lm \
 *     -Wl,-rpath,${PWD}/kyber_side-channel_poc/liboqs/build/lib \
 *     -o kyber_side-channel_poc/decap_harness
 *
 * Usage:
 *   ./kyber_side-channel_poc/decap_harness --trials 20000 --flips 0 --seed 42 --kem kyber1024 > reports/kyber_clean.csv
 *   ./kyber_side-channel_poc/decap_harness --trials 20000 --flips 4 --seed 42 --kem kyber1024 > reports/kyber_flip4.csv
 *
 * Notes:
 * - This PoC is for timing methodology only; it is NOT an attack and does not
 *   claim a vulnerability. Modern Kyber implementations strive for constant time.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <inttypes.h>
#include <errno.h>
#include <time.h>
#include <getopt.h>

#if defined(__APPLE__)
  #include <mach/mach_time.h>
#elif defined(__unix__) || defined(__linux__)
  #include <time.h>
#else
  #include <sys/time.h>
#endif

#include <oqs/oqs.h>  /* brings in KEM APIs and algorithm name constants */

/* ---------- portable high-resolution timer → nanoseconds ---------- */
static uint64_t now_ns(void) {
#if defined(__APPLE__)
    static mach_timebase_info_data_t tb = {0,0};
    if (tb.denom == 0) mach_timebase_info(&tb);
    uint64_t t = mach_absolute_time();
    return (t * tb.numer) / tb.denom;
#elif defined(CLOCK_MONOTONIC_RAW)
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC_RAW, &ts) == 0) {
        return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
    }
    struct timespec ts2;
    clock_gettime(CLOCK_MONOTONIC, &ts2);
    return (uint64_t)ts2.tv_sec * 1000000000ULL + (uint64_t)ts2.tv_nsec;
#else
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (uint64_t)tv.tv_sec * 1000000000ULL + (uint64_t)tv.tv_usec * 1000ULL;
#endif
}

/* ---------- tiny deterministic RNG (xorshift64*) ---------- */
static uint64_t rng_state = 0xdeadbeefcafebabeULL;
static void rng_seed(uint64_t s) { rng_state = s ? s : 0xdeadbeefcafebabeULL; }
static uint64_t rng_next(void) {
    uint64_t x = rng_state;
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    rng_state = x;
    return x * 2685821657736338717ULL;
}

/* Flip k randomly chosen single bits (with replacement) in buf[0..len) */
static int flip_bits(uint8_t *buf, size_t len, int k) {
    if (k <= 0 || len == 0) return 0;
    int flipped = 0;
    for (int i = 0; i < k; i++) {
        uint64_t r = rng_next();
        size_t idx = (size_t)(r % len);
        uint8_t bit = (uint8_t)(r & 7u);   /* 0..7 */
        buf[idx] ^= (uint8_t)(1u << bit);
        flipped++;
    }
    return flipped;
}

/* ---------- CLI ---------- */
static void usage(const char *prog) {
    fprintf(stderr,
      "Usage: %s [--trials N] [--flips F] [--seed S] [--kem kyber1024|kyber768]\n"
      "CSV columns: trial,class,flips,ns,seed,kem,decap_rc\n", prog);
}

int main(int argc, char **argv) {
    size_t trials = 10000;
    int flips = 0;
    uint64_t seed = (uint64_t)time(NULL);
    const char *kem_cli = "kyber1024";
    const char *kem_name = OQS_KEM_alg_kyber_1024; /* API string constant */

    static struct option longopts[] = {
        {"trials", required_argument, NULL, 't'},
        {"flips",  required_argument, NULL, 'f'},
        {"seed",   required_argument, NULL, 's'},
        {"kem",    required_argument, NULL, 'k'},
        {"help",   no_argument,       NULL, 'h'},
        {0,0,0,0}
    };
    int opt;
    while ((opt = getopt_long(argc, argv, "t:f:s:k:h", longopts, NULL)) != -1) {
        switch (opt) {
            case 't': trials = (size_t)strtoull(optarg, NULL, 10); break;
            case 'f': flips  = atoi(optarg); break;
            case 's': seed   = (uint64_t)strtoull(optarg, NULL, 10); break;
            case 'k':
                kem_cli = optarg;
                if (strcmp(optarg, "kyber1024") == 0) {
                    kem_name = OQS_KEM_alg_kyber_1024;
                } else if (strcmp(optarg, "kyber768") == 0) {
                    kem_name = OQS_KEM_alg_kyber_768;
                } else {
                    fprintf(stderr, "Unknown --kem '%s' (use kyber1024 or kyber768)\n", optarg);
                    return 2;
                }
                break;
            case 'h':
            default: usage(argv[0]); return 1;
        }
    }

    /* liboqs modern builds do not require explicit init. Create KEM instance. */
    OQS_KEM *kem = OQS_KEM_new(kem_name);
    if (kem == NULL) {
        fprintf(stderr, "[err] OQS_KEM_new failed for %s\n", kem_cli);
        return 3;
    }

    /* Allocate buffers */
    uint8_t *pk   = (uint8_t*)malloc(kem->length_public_key);
    uint8_t *sk   = (uint8_t*)malloc(kem->length_secret_key);
    uint8_t *ct0  = (uint8_t*)malloc(kem->length_ciphertext);     /* base ciphertext */
    uint8_t *ss   = (uint8_t*)malloc(kem->length_shared_secret);
    uint8_t *ss2  = (uint8_t*)malloc(kem->length_shared_secret);
    if (!pk || !sk || !ct0 || !ss || !ss2) {
        fprintf(stderr, "[err] allocation failed\n");
        OQS_KEM_free(kem);
        free(pk); free(sk); free(ct0); free(ss); free(ss2);
        return 4;
    }

    /* One keypair + one encaps to produce a base ciphertext we will mutate */
    if (OQS_SUCCESS != OQS_KEM_keypair(kem, pk, sk)) {
        fprintf(stderr, "[err] keypair failed\n");
        OQS_KEM_free(kem); free(pk); free(sk); free(ct0); free(ss); free(ss2);
        return 5;
    }
    if (OQS_SUCCESS != OQS_KEM_encaps(kem, ct0, ss, pk)) {
        fprintf(stderr, "[err] encaps failed\n");
        OQS_KEM_free(kem); free(pk); free(sk); free(ct0); free(ss); free(ss2);
        return 6;
    }

    /* CSV header */
    printf("trial,class,flips,ns,seed,kem,decap_rc\n");
    fflush(stdout);

    rng_seed(seed);

    for (size_t i = 0; i < trials; i++) {
        /* copy base ciphertext for this trial */
        uint8_t *ct = (uint8_t*)malloc(kem->length_ciphertext);
        if (!ct) { fprintf(stderr, "[err] ct alloc\n"); break; }
        memcpy(ct, ct0, kem->length_ciphertext);

        const char *cls = "clean";
        int flipped = 0;
        if (flips > 0) {
            flipped = flip_bits(ct, kem->length_ciphertext, flips);
            cls = "flipped";
        }

        uint64_t t0 = now_ns();
        OQS_STATUS rc = OQS_KEM_decaps(kem, ss2, ct, sk);
        uint64_t t1 = now_ns();
        uint64_t elapsed = t1 - t0;

        /* CSV row (report rc so you can see if flips caused failure) */
        printf("%zu,%s,%d,%" PRIu64 ",%" PRIu64 ",%s,%d\n",
               i, cls, flipped, elapsed, seed, kem_cli, (int)rc);
        fflush(stdout);

        free(ct);
    }

    /* Cleanup */
    OQS_KEM_free(kem);
    free(pk); free(sk); free(ct0); free(ss); free(ss2);
    return 0;
}
