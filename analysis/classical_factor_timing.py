#!/usr/bin/env python3
"""
Measure classical factoring time for small N (sympy.factorint).
Writes reports/classical_factor_timing.csv with safe columns:
  N,time_s,factors_json
"""
import time, json
from pathlib import Path
import sympy as sp

OUTDIR = Path(__file__).resolve().parents[1] / "reports"
OUTDIR.mkdir(parents=True, exist_ok=True)
CSV = OUTDIR / "classical_factor_timing.csv"

Ns = [15, 21, 33, 35, 77, 143, 221, 299]

with open(CSV, "w", encoding="utf-8") as f:
    f.write("N,time_s,factors_json\n")
    for N in Ns:
        t0 = time.time()
        fac = sp.factorint(N)  # dict
        dt = time.time() - t0
        f.write(f"{N},{dt:.6f},{json.dumps(fac, ensure_ascii=False)}\n")

print(f"[ok] wrote {CSV}")
