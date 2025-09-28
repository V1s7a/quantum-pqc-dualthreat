#!/usr/bin/env python3
"""
Generate two separate figures:
  1) Theoretical operation counts (Grover vs Classical)
  2) Measured wall-clock times (Grover vs Classical)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from math import pi

OUTDIR = Path("reports")
OUTDIR.mkdir(parents=True, exist_ok=True)

# choose n values to plot
ns = [3, 4, 5, 6]

# theoretical operation counts
classic_ops = [2**n / 2 for n in ns]                # avg classical tries
grover_iters = [(pi/4) * (2**(n/2)) for n in ns]    # optimal Grover iterations

# ---------- FIGURE 1: Theoretical ----------
fig1, ax1 = plt.subplots(figsize=(6, 4))
ax1.plot(ns, classic_ops, marker="o", label="Classical ~ 2^{n-1}")
ax1.plot(ns, grover_iters, marker="s", label="Grover ~ (π/4)·2^{n/2}")
ax1.set_yscale("log")
ax1.set_xlabel("Key bits n")
ax1.set_ylabel("Operations (log scale)")
ax1.set_title("Theoretical Operation Counts")
ax1.grid(True, which="both", ls="--", alpha=0.4)
ax1.legend()
f1_path = OUTDIR / "grover_vs_classical_theoretical.png"
plt.tight_layout()
plt.savefig(f1_path, dpi=200)
print(f"[ok] wrote {f1_path}")
plt.close(fig1)

# ---------- FIGURE 2: Measured runtimes ----------
fig2, ax2 = plt.subplots(figsize=(6, 4))
plotted = False

gcsv = OUTDIR / "grover_lab_results.csv"
if gcsv.exists():
    gdf = pd.read_csv(gcsv)
    gmeans = gdf.groupby("n_bits")["elapsed_s"].mean().reindex(ns)
    ax2.plot(ns, gmeans.values, marker="s", label="Grover (sim elapsed s)")
    plotted = True

ccsv = OUTDIR / "classical_bruteforce_results.csv"
if ccsv.exists():
    cdf = pd.read_csv(ccsv)
    cmeans = cdf.set_index("n_bits").reindex(ns)["mean_time_s"]
    ax2.plot(ns, cmeans.values, marker="o", label="Classical (mean s)")
    plotted = True

if plotted:
    ax2.set_yscale("log")
    ax2.set_xlabel("Key bits n")
    ax2.set_ylabel("Wall-clock (s, log)")
    ax2.set_title("Measured runtimes (local CPU vs simulator)")
    ax2.grid(True, which="both", ls="--", alpha=0.4)
    ax2.legend()
else:
    ax2.text(0.5, 0.5, "No CSVs found.\nRun grover_demo.py and classical_bruteforce.py first.",
             ha="center", va="center")

f2_path = OUTDIR / "grover_vs_classical_measured.png"
plt.tight_layout()
plt.savefig(f2_path, dpi=200)
print(f"[ok] wrote {f2_path}")
plt.close(fig2)
