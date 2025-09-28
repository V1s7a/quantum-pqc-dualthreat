#!/usr/bin/env python3
"""
Grover vs Classical asymptotics (overflow-safe, log10 plots).

Generates:
  reports/grover_asymptotic_ops.png    # y = log10(operation count)
  reports/grover_asymptotic_time.png   # y = log10(seconds; illustrative constants)

Why log10? 2^n blows up quickly and will overflow float64.
Plotting log10 values sidesteps overflow while keeping the trends clear.
"""

from math import pi, log10
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nmin", type=int, default=32, help="min key bits n")
    ap.add_argument("--nmax", type=int, default=256, help="max key bits n")
    # Illustrative constants — adjust to produce a crossover you like in the time plot
    ap.add_argument("--t_classical_per_try", type=float, default=1e-12,
                    help="seconds per classical key test (illustrative)")
    ap.add_argument("--t_grover_per_iter", type=float, default=1e-6,
                    help="seconds per Grover iteration (illustrative)")
    ap.add_argument("--outdir", type=str, default="reports")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    # Key sizes
    n = np.arange(args.nmin, args.nmax + 1, dtype=np.int64)

    # ---------- LOG10(operation count) ----------
    # classical_ops ~ 2^(n-1)       => log10 = (n-1)*log10(2)
    # grover_iters ~ (pi/4)*2^(n/2) => log10 = log10(pi/4) + (n/2)*log10(2)
    log10_2 = np.log10(2.0)
    log10_class_ops = (n - 1) * log10_2
    log10_grov_ops  = np.log10(pi / 4.0) + (n / 2.0) * log10_2

    # ---- Plot 1: operations in log10 ----
    fig1, ax1 = plt.subplots(figsize=(8.5, 4.5))
    ax1.plot(n, log10_class_ops, label=r"Classical $\sim 2^{\,n-1}$")
    ax1.plot(n, log10_grov_ops,  label=r"Grover $\sim (\pi/4)\,2^{\,n/2}$")
    ax1.set_xlabel("Key size n (bits)")
    ax1.set_ylabel(r"$\log_{10}(\text{operations})$")
    ax1.set_title("Grover vs Classical — Asymptotic Ops (log10)")
    ax1.grid(True, ls="--", alpha=0.35)
    ax1.legend()

    for kline in (128, 192, 256):
        ax1.axvline(kline, color="gray", ls=":", alpha=0.6)
        ymin, ymax = ax1.get_ylim()
        ax1.text(kline + 1, ymin + 0.02*(ymax - ymin), f"{kline}-bit",
                 rotation=90, va="bottom", color="gray")

    f1 = outdir / "grover_asymptotic_ops.png"
    fig1.tight_layout(); fig1.savefig(f1, dpi=200); plt.close(fig1)
    print(f"[ok] wrote {f1}")

    # ---------- LOG10(time) with illustrative constants ----------
    # time_class = ops * t_classical_per_try
    # => log10(time) = log10(ops) + log10(t_per_try)
    log10_t_class = log10_class_ops + log10(args.t_classical_per_try)
    log10_t_grov  = log10_grov_ops  + log10(args.t_grover_per_iter)

    # ---- Plot 2: time in log10 seconds ----
    fig2, ax2 = plt.subplots(figsize=(8.5, 4.5))
    ax2.plot(n, log10_t_class, label="Classical (illustrative)")
    ax2.plot(n, log10_t_grov,  label="Grover (illustrative)")
    ax2.set_xlabel("Key size n (bits)")
    ax2.set_ylabel(r"$\log_{10}(\text{seconds})$")
    ax2.set_title("Grover vs Classical — Illustrative Wall-Clock (log10)")
    ax2.grid(True, ls="--", alpha=0.35)
    ax2.legend()

    for kline in (128, 192, 256):
        ax2.axvline(kline, color="gray", ls=":", alpha=0.6)
        ymin, ymax = ax2.get_ylim()
        ax2.text(kline + 1, ymin + 0.02*(ymax - ymin), f"{kline}-bit",
                 rotation=90, va="bottom", color="gray")

    f2 = outdir / "grover_asymptotic_time.png"
    fig2.tight_layout(); fig2.savefig(f2, dpi=200); plt.close(fig2)
    print(f"[ok] wrote {f2}")

if __name__ == "__main__":
    main()
