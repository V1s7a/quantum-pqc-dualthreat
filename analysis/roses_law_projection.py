#!/usr/bin/env python3
"""
Build a Rose's Law figure using YOUR timeline CSV.

Reads:
  reports/quantum_timeline_scenarios.csv
  (columns: required_qubits, start_qubits, doubling_months, years_to_reach, reach_year)

Outputs:
  reports/roses_law_from_timeline.png
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------- paths ----------
ROOT = Path(__file__).resolve().parents[1]
RPT  = ROOT / "reports"
CSV  = RPT / "quantum_timeline_scenarios.csv"
OUT  = RPT / "roses_law_from_timeline.png"

# ---------- load & sanity ----------
if not CSV.exists():
    raise SystemExit(f"[error] {CSV} not found. Run your timeline generator first.")

df = pd.read_csv(CSV)
req_cols = {"required_qubits","start_qubits","doubling_months","years_to_reach","reach_year"}
missing = req_cols - set(df.columns)
if missing:
    raise SystemExit(f"[error] CSV missing columns: {sorted(missing)}")

# numeric coercion
for c in req_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")
if df.isnull().any().any():
    print("[warn] NaNs found; check your CSV rows.")

# ---------- parameters inferred from your CSV ----------
baseline_year = 2025  # set to the year you used in the generator
starts   = sorted(df["start_qubits"].unique())
doubs    = sorted(df["doubling_months"].unique())
targets  = sorted(df["required_qubits"].unique())  # qubit breakpoints from your scenarios
year_max = int(np.floor(df["reach_year"].max())) + 5

# Optional human-friendly labels for common targets (fallback to raw number)
label_map = {
    1e7: "ECC-256 (~10M)",
    2e7: "RSA-2048 (low ~20M)",
    1e8: "RSA-2048 (high ~100M)",
}
def tgt_label(q):
    return label_map.get(float(q), f"Target: {int(q):,} qubits")

# ---------- plot ----------
years = np.arange(baseline_year, year_max + 1)

plt.figure(figsize=(10, 6))
palette = {12: "#1f77b4", 18: "#2ca02c", 24: "#ff7f0e"}  # by doubling rate

# growth curves
for q0 in starts:
    for D in doubs:
        growth = q0 * (2.0 ** ((years - baseline_year) * 12.0 / D))
        style  = "-" if q0 == max(starts) else "--"
        color  = palette.get(int(D), None)
        label  = f"Start {int(q0)} qubits, double {int(D)}m"
        plt.plot(years, growth, style, lw=2, color=color, alpha=0.9, label=label)

# horizontal target lines
for q in targets:
    plt.axhline(q, ls=":", lw=2, color="#444", label=tgt_label(q))

# mark crossover years from your CSV
for _, r in df.iterrows():
    x = r["reach_year"]
    y = r["required_qubits"]
    D = int(r["doubling_months"])
    q0 = int(r["start_qubits"])
    color = palette.get(D, "#555")
    plt.plot([x], [y], marker="o", color=color, markersize=5)
    # small label near the marker
    plt.text(x+0.2, y*1.05, f"{q0}→{D}m", fontsize=8, color=color)

# axes, legend, save
plt.yscale("log")
plt.xlabel("Year")
plt.ylabel("Physical qubits (log scale)")
plt.title("Quantum Rose's Law Projection (from timeline CSV) vs Crypto Breakpoints")
plt.grid(True, which="both", ls="--", alpha=0.4)
plt.legend(ncol=2, fontsize=9, frameon=True, framealpha=0.9)
plt.tight_layout()
OUT.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(OUT, dpi=300)
print(f"[ok] wrote {OUT}")
