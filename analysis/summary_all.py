#!/usr/bin/env python3
"""
Generate a single, publication-ready PNG with three aligned panels:
(A) T-count, (B) Physical Qubits (log), (C) Runtime (log).

Inputs (first found is used):
  - reports/qsharp_clip_summary.tsv        (preferred)
  - reports/qsharp_from_clip.tsv
  - reports/qsharp_from_clip.json

Output:
  - reports/qsharp_clip_summary_all.png
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import json

# ---------- locate repo root & paths ----------
THIS = Path(__file__).resolve()
ROOT = THIS.parents[1]  # repo root = parent of analysis/
RPT = ROOT / "reports"

CANDIDATE_TSVS = [
    RPT / "qsharp_clip_summary.tsv",
    RPT / "qsharp_from_clip.tsv",
]
CANDIDATE_JSONS = [
    RPT / "qsharp_from_clip.json",
]

OUT_PNG = RPT / "qsharp_clip_summary_all.png"

NUM_COLS = [
    "error_budget",
    "logical_qubits",
    "t_factories",
    "t_depth",
    "measurements",
    "code_distance",
    "factory_fraction",
    "t_count",
    "runtime_seconds",
    "physical_qubits",
]

# ---------- load data ----------
def load_df() -> pd.DataFrame:
    # Try TSVs
    for p in CANDIDATE_TSVS:
        if p.exists():
            df = pd.read_csv(p, sep="\t")
            print(f"[ok] loaded {p}")
            return df
    # Try JSONs
    for p in CANDIDATE_JSONS:
        if p.exists():
            rows = json.loads(p.read_text())
            df = pd.DataFrame(rows)
            print(f"[ok] loaded {p}")
            return df
    print("[error] No input found. Expected one of:")
    for p in CANDIDATE_TSVS + CANDIDATE_JSONS:
        print("  -", p)
    sys.exit(1)

def coerce_numerics(df: pd.DataFrame) -> pd.DataFrame:
    for c in NUM_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def build_xlabels(df: pd.DataFrame) -> pd.Series:
    tgt = df["target"].astype(str) if "target" in df.columns else pd.Series([f"row{i}" for i in range(len(df))])
    eb  = df["error_budget"].astype(str) if "error_budget" in df.columns else pd.Series([""] * len(df))
    # Use ε=... only if present
    suffix = eb.apply(lambda s: f"\nε={s}" if s else "")
    return tgt + suffix

# ---------- plotting helpers ----------
def rotate_and_align_xticks(ax, angle=45, ha="right"):
    # rotation via tick_params; alignment via label objects
    ax.tick_params(axis="x", labelrotation=angle)
    for lab in ax.get_xticklabels():
        try:
            lab.set_ha(ha)
        except Exception:
            pass

def safe_bar(ax, xlabels, series, title, ylabel, logy=False):
    ax.bar(xlabels, series)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    if logy:
        ax.set_yscale("log")
    rotate_and_align_xticks(ax)

def main():
    df = load_df()
    df = coerce_numerics(df)

    # Stable ordering if both present
    if "target" in df.columns and "error_budget" in df.columns:
        df = df.sort_values(["target", "error_budget"], kind="mergesort").reset_index(drop=True)

    xlabels = build_xlabels(df)

    # Create figure with 3 subplots
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # Panel A: T-count
    if "t_count" in df.columns:
        safe_bar(axes[0], xlabels, df["t_count"], "T-count", "Count", logy=False)
    else:
        axes[0].text(0.5, 0.5, "No t_count column", ha="center", va="center")
        axes[0].set_title("T-count")

    # Panel B: Physical Qubits (log)
    if "physical_qubits" in df.columns:
        safe_bar(axes[1], xlabels, df["physical_qubits"], "Physical Qubits", "Qubits (log scale)", logy=True)
    else:
        axes[1].text(0.5, 0.5, "No physical_qubits column", ha="center", va="center")
        axes[1].set_title("Physical Qubits")

    # Panel C: Runtime (log)
    if "runtime_seconds" in df.columns:
        safe_bar(axes[2], xlabels, df["runtime_seconds"], "Runtime", "Seconds (log scale)", logy=True)
    else:
        axes[2].text(0.5, 0.5, "No runtime_seconds column", ha="center", va="center")
        axes[2].set_title("Runtime")

    plt.tight_layout()
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT_PNG, dpi=300)
    print(f"[ok] wrote {OUT_PNG}")

if __name__ == "__main__":
    main()
