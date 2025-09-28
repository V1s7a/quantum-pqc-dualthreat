#!/usr/bin/env python3
"""
Compare asymptotic cost of integer factoring:
- Classical GNFS (sub-exponential L_N[1/3, c]) in terms of k = log2(N)
- Shor's algorithm ~ O(k^3)

We plot *relative* cost curves (log scale). Constants are illustrative.
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse
from math import log

def gnfs_cost_bits(k_bits: np.ndarray, c: float = (64.0/9.0)**(1.0/3.0)) -> np.ndarray:
    # k = log2 N; ln N = k * ln 2
    lnN = k_bits * np.log(2.0)
    # L_N[1/3, c] = exp( (c + o(1)) * (ln N)^{1/3} (ln ln N)^{2/3} )
    term = (lnN**(1.0/3.0)) * (np.log(lnN)**(2.0/3.0))
    return np.exp(c * term)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kmin", type=int, default=256, help="min modulus bits (log2 N)")
    ap.add_argument("--kmax", type=int, default=4096, help="max modulus bits")
    ap.add_argument("--c_gnfs", type=float, default=(64.0/9.0)**(1.0/3.0), help="GNFS constant (illustrative)")
    ap.add_argument("--c_shor", type=float, default=1.0, help="constant factor for Shor (illustrative)")
    ap.add_argument("--out", type=str, default="reports/shor_vs_gnfs_asymptotic.png")
    args = ap.parse_args()

    k = np.arange(args.kmin, args.kmax+1)
    gnfs = gnfs_cost_bits(k, c=args.c_gnfs)
    shor = args.c_shor * (k**3)

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(k, gnfs, label="Classical GNFS (sub-exponential)")
    ax.plot(k, shor, label="Shor (≈ k³)")
    ax.set_yscale("log")
    ax.set_xlabel("Modulus size k = log₂ N (bits)")
    ax.set_ylabel("Relative cost (log scale)")
    ax.set_title("Factoring asymptotics: GNFS vs Shor (illustrative)")
    ax.grid(True, which="both", ls="--", alpha=0.4)
    ax.legend()

    # Mark common RSA sizes
    for bits in (1024, 2048, 3072, 4096):
        ax.axvline(bits, color="gray", ls=":", alpha=0.6)
        ax.text(bits+10, ax.get_ylim()[0]*1.5, f"RSA-{bits}", rotation=90, va="bottom", color="gray")

    Path("reports").mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(args.out, dpi=200)
    print(f"[ok] wrote {args.out}")

if __name__ == "__main__":
    main()
