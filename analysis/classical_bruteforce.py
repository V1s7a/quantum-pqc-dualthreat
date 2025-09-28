#!/usr/bin/env python3
"""
Classical brute-force baseline (toy).
Usage:
  python analysis/classical_bruteforce.py --n 3 --trials 20
"""
import argparse, time, statistics
import numpy as np
from pathlib import Path

OUTDIR = Path("reports"); OUTDIR.mkdir(parents=True, exist_ok=True)
CSV = OUTDIR / "classical_bruteforce_results.csv"

def time_one(n: int, secret_bin: str) -> float:
    start = time.time()
    target = int(secret_bin, 2)
    for k in range(2**n):
        if k == target:
            break
    return time.time() - start

def run(n: int, trials: int):
    times = []
    for _ in range(trials):
        sec = format(np.random.randint(0, 2**n), f"0{n}b")
        times.append(time_one(n, sec))
    mean = statistics.mean(times); median = statistics.median(times)
    write_header = not CSV.exists() or CSV.stat().st_size == 0
    with open(CSV, "a") as f:
        if write_header:
            f.write("n_bits,trials,mean_time_s,median_time_s\n")
        f.write(f"{n},{trials},{mean:.6f},{median:.6f}\n")
    print(f"[ok] n={n} trials={trials} mean={mean:.6f}s median={median:.6f}s -> {CSV}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--trials", type=int, default=20)
    args = ap.parse_args()
    run(args.n, args.trials)
