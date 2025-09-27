// decap_harness.c
// Minimal timing harness around Kyber decapsulation via liboqs.
// Collects N timing samples (in nanoseconds) to CSV.
//
// Build example (from liboqs/build/):
//   gcc -O2 -I../include -L. -loqs -o decap_harness ../decap_harness.c
// Run example (from liboqs/build/):
//   LD_LIBRARY_PATH=. ./decap_harness 20000 kyber512 > ../traces_kyber512.csv



#define _GNU_SOURCE
#include <stdio.h>      // printf, fprintf
#include <stdint.h>     // uint64_t
#include <time.h>       // clock_gettime
#include <stdlib.h>     // malloc, free, atoi
#include <string.h>     // memcpy
#include "oqs/oqs.h"    // liboqs API

// Return a monotonic timestamp in nanoseconds.
// CLOCK_MONOTONIC_RAW: avoids NTP/time adjustments; good for timing deltas.
static inline uint64_t now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "Usage: %s <n-traces> <kyber-mode>\n", argv[0]);
        fprintf(stderr, "Example: %s 20000 kyber512\n", argv[0]);
        return 1;
    }

    // 1) Parse CLI arguments
    const int n_traces = atoi(argv[1]);
    const char *kem_name = argv[2];

    // 2) Check algorithm availability in this liboqs build
    if (!OQS_KEM_is_enabled(kem_name)) {
        fprintf(stderr, "Kyber mode '%s' not enabled in this liboqs build.\n", kem_name);
        return 1;
    }

    // 3) Allocate a KEM object and its buffers
    OQS_KEM *kem = OQS_KEM_new(kem_name);
    if (kem == NULL) {
        fprintf(stderr, "OQS_KEM_new failed for '%s'\n", kem_name);
        return 1;
    }

    // Allocate message buffers according to chosen KEM parameters
    unsigned char *ct  = (unsigned char *) malloc(kem->length_ciphertext);     // ciphertext
    unsigned char *ss  = (unsigned char *) malloc(kem->length_shared_secret);  // shared secret (encap output)
    unsigned char *ss2 = (unsigned char *) malloc(kem->length_shared_secret);  // shared secret (decap output)
    unsigned char *pk  = (unsigned char *) malloc(kem->length_public_key);     // public key
    unsigned char *sk  = (unsigned char *) malloc(kem->length_secret_key);     // secret key

    if (!ct || !ss || !ss2 || !pk || !sk) {
        fprintf(stderr, "malloc failed\n");
        return 1;
    }

    // 4) Generate a Kyber keypair (pk, sk)
    if (OQS_SUCCESS != OQS_KEM_keypair(kem, pk, sk)) {
        fprintf(stderr, "Keypair generation failed\n");
        return 1;
    }

    // 5) Create a single valid ciphertext by encapsulating to pk
    //    We’ll re-use `ct` for repeated decapsulation to measure timing.
    if (OQS_SUCCESS != OQS_KEM_encaps(kem, ct, ss, pk)) {
        fprintf(stderr, "Encapsulation failed\n");
        return 1;
    }

    // 6) CSV header: add columns for ID and elapsed timing in ns
    //    You can add a label column later (e.g., valid/malformed) if you generate multiple classes.
    printf("trace_id,elapsed_ns\n");

    // 7) (Optional) Warm-up: run a few decapsulations to prime caches/branches
    for (int w = 0; w < 100; w++) {
        (void) OQS_KEM_decaps(kem, ss2, ct, sk);
    }

    // 8) Measure N decapsulations back-to-back
    for (int i = 0; i < n_traces; i++) {
        // Time just the decapsulation call
        uint64_t t0 = now_ns();
        (void) OQS_KEM_decaps(kem, ss2, ct, sk);
        uint64_t t1 = now_ns();

        uint64_t elapsed = t1 - t0;
        // Write a CSV row (flush to reduce buffering if you want live updates)
        printf("%d,%lu\n", i, (unsigned long) elapsed);
    }

    // 9) Cleanup
    free(ct); free(ss); free(ss2); free(pk); free(sk);
    OQS_KEM_free(kem);
    return 0;
}
