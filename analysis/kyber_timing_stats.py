#!/usr/bin/env python3
"""
kyber_timing_stats.py — robust stats on decap_harness CSVs.

Usage:
  python analysis/kyber_timing_stats.py reports/kyber_clean.csv reports/kyber_flip4.csv
  # (you can pass 1+ files; they will be concatenated)

Outputs: prints per-class stats, Welch t-test, Mann–Whitney U,
Cohen's d, Cliff's delta, bootstrap CI for median diff, and AUC.
"""

import sys, numpy as np, pandas as pd
from math import sqrt
from pathlib import Path

# optional deps are guarded
try:
    from scipy import stats
except Exception:
    stats = None
try:
    from sklearn.metrics import roc_auc_score
except Exception:
    roc_auc_score = None

def cohens_d(x, y):
    nx, ny = len(x), len(y)
    if nx < 2 or ny < 2:
        return np.nan
    dof = nx + ny - 2
    pooled = ((nx-1)*np.var(x, ddof=1) + (ny-1)*np.var(y, ddof=1)) / dof
    if pooled <= 0:
        return np.nan
    return (np.mean(x) - np.mean(y)) / np.sqrt(pooled)

def cliffs_delta(a, b):
    na, nb = len(a), len(b)
    if na == 0 or nb == 0:
        return np.nan
    # Efficient approximation via ranks
    A = np.sort(a); B = np.sort(b)
    i = j = gt = lt = 0
    while i < na and j < nb:
        if A[i] > B[j]:
            gt += (na - i)
            j += 1
        elif A[i] < B[j]:
            lt += (nb - j)
            i += 1
        else:
            # equal values: move both
            i += 1; j += 1
    return (gt - lt) / (na * nb)

def bootstrap_median_diff(a, b, iters=2000, seed=12345):
    if len(a) == 0 or len(b) == 0:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(iters):
        ma = rng.choice(a, size=len(a), replace=True)
        mb = rng.choice(b, size=len(b), replace=True)
        diffs.append(np.median(ma) - np.median(mb))
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return (lo, hi)

def main(paths):
    if not paths:
        print("Usage: kyber_timing_stats.py csv1 [csv2 ...]")
        sys.exit(1)

    dfs = []
    for p in paths:
        p = Path(p)
        if not p.exists():
            print(f"[err] file not found: {p}")
            sys.exit(2)
        df = pd.read_csv(p)
        # Ensure expected cols and types
        req = {"trial","class","flips","ns"}
        if not req.issubset(df.columns):
            print(f"[err] {p} missing required columns; found {list(df.columns)}")
            sys.exit(3)
        df["ns"] = pd.to_numeric(df["ns"], errors="coerce")
        df = df.dropna(subset=["ns"])
        dfs.append(df)

    df = pd.concat(dfs, ignore_index=True)

    # Summary by class
    print("\n=== Per-class descriptive stats ===")
    byc = df.groupby("class")["ns"]
    for cls, s in byc:
        print(f"Class={cls:7s}  n={len(s):6d}  mean={s.mean():9.2f} ns  median={s.median():9.2f}  std={s.std():9.2f}")

    # Pull arrays
    a = df[df["class"]=="clean"]["ns"].to_numpy()
    b = df[df["class"]=="flipped"]["ns"].to_numpy()
    na, nb = len(a), len(b)

    if na == 0 or nb == 0:
        print("\n[info] One of the classes is empty; need both 'clean' and 'flipped'.")
        sys.exit(0)

    print("\n=== Statistical tests (clean vs flipped) ===")
    # Welch t-test
    if stats is not None and na >= 2 and nb >= 2:
        tstat, pval = stats.ttest_ind(a, b, equal_var=False)
        print(f"Welch t-test: t={tstat:.3f}, p={pval:.3e}")
    else:
        print("Welch t-test: skipped (scipy missing or too few samples)")

    # Mann–Whitney U
    if stats is not None and na >= 1 and nb >= 1:
        try:
            u, p2 = stats.mannwhitneyu(a, b, alternative="two-sided")
            print(f"Mann–Whitney U: U={u:.0f}, p={p2:.3e}")
        except Exception as e:
            print(f"Mann–Whitney U: skipped ({e})")
    else:
        print("Mann–Whitney U: skipped")

    # Effect sizes
    d = cohens_d(a, b)
    cd = cliffs_delta(a, b)
    print(f"Cohen's d: {d if np.isfinite(d) else np.nan}")
    print(f"Cliff's delta: {cd if np.isfinite(cd) else np.nan}")

    # Bootstrap CI for median difference
    lo, hi = bootstrap_median_diff(a, b)
    print(f"Bootstrap median diff 95% CI (clean - flipped): {lo:.2f} .. {hi:.2f} ns")

        # AUC using timing only
    if roc_auc_score is not None:
        y = (df["class"]=="flipped").astype(int).to_numpy()
        auc = roc_auc_score(y, df["ns"].to_numpy())
        print(f"AUC (ns-only classifier): {auc:.3f}")
    else:
        print("AUC: skipped (sklearn not installed)")


if __name__ == "__main__":
    main(sys.argv[1:])
