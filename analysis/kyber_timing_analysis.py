#!/usr/bin/env python3
"""
kyber_timing_analysis.py — analyze harness CSV output.

Usage:
    python analysis/kyber_timing_analysis.py reports/kyber_clean.csv reports/kyber_flip4.csv

Produces:
    reports/kyber_timing_summary.tsv
    reports/kyber_timing_violin.png
    reports/kyber_timing_hist.png
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def load_csv(path):
    df = pd.read_csv(path)
    df["source_file"] = path
    return df

def main(argv):
    if len(argv) < 2:
        print("Usage: kyber_timing_analysis.py csv1 [csv2 ...]")
        sys.exit(1)

    dfs = []
    for path in argv:
        p = Path(path)
        if not p.exists():
            print(f"[err] missing {p}")
            sys.exit(2)
        dfs.append(load_csv(p))

    df = pd.concat(dfs, ignore_index=True)

    # summary stats
    summary = (
        df.groupby(["class", "flips", "kem"])
        .agg(trials=("trial", "count"),
             mean_ns=("ns", "mean"),
             std_ns=("ns", "std"),
             median_ns=("ns", "median"),
             min_ns=("ns", "min"),
             max_ns=("ns", "max"))
        .reset_index()
    )

    outdir = Path("reports")
    outdir.mkdir(exist_ok=True)

    summary_path = outdir / "kyber_timing_summary.tsv"
    summary.to_csv(summary_path, sep="\t", index=False)
    print(f"[ok] wrote {summary_path}")

    # violin plot
    plt.figure(figsize=(8,5))
    sns.violinplot(data=df, x="class", y="ns", hue="kem", split=True, inner="quart")
    plt.title("Kyber decapsulation timing distribution")
    plt.ylabel("nanoseconds")
    plt.tight_layout()
    violin_path = outdir / "kyber_timing_violin.png"
    plt.savefig(violin_path, dpi=150)
    print(f"[ok] wrote {violin_path}")

    # histogram plot
    plt.figure(figsize=(8,5))
    sns.histplot(data=df, x="ns", hue="class", bins=50, kde=True)
    plt.title("Kyber decapsulation timing histogram")
    plt.xlabel("nanoseconds")
    plt.tight_layout()
    hist_path = outdir / "kyber_timing_hist.png"
    plt.savefig(hist_path, dpi=150)
    print(f"[ok] wrote {hist_path}")

        # boxplot zoomed
    plt.figure(figsize=(6,5))
    sns.boxplot(data=df[df["ns"] < 50000], x="class", y="ns")
    plt.title("Kyber decapsulation timing (<50k ns)")
    plt.ylabel("nanoseconds")
    plt.tight_layout()
    plt.savefig(outdir / "kyber_timing_boxplot_zoom.png", dpi=150)

    # histogram zoomed
    plt.figure(figsize=(8,5))
    sns.histplot(data=df[df["ns"] < 50000], x="ns", hue="class", bins=100, kde=True)
    plt.title("Histogram (<50k ns)")
    plt.xlabel("nanoseconds")
    plt.tight_layout()
    plt.savefig(outdir / "kyber_timing_hist_zoom.png", dpi=150)

if __name__ == "__main__":
    main(sys.argv[1:])
