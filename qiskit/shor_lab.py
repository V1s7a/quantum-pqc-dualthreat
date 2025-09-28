#!/usr/bin/env python3
"""
shor_lab.py — Shor order-finding demo for N=15 (educational) with CSV/PNG outputs.

Outputs under <repo>/reports/:
  - shor_counts_N15_a{a}.png
  - shor_lab_results.csv  (N,a,n_count,shots,top_bits,phase,r,p,q,success,elapsed_s)

Usage:
  python qiskit/shor_lab.py
  python qiskit/shor_lab.py --bases 7,11,13 --ncount 8 --shots 16384
"""
from math import gcd, pi
from fractions import Fraction
from typing import Dict, List, Tuple
from pathlib import Path
import time

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

# ---------- repo-root aware outputs ----------
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTDIR = REPO_ROOT / "reports"
OUTDIR.mkdir(parents=True, exist_ok=True)
CSV = OUTDIR / "shor_lab_results.csv"

# ---------- inverse QFT ----------
def iqft(circ: QuantumCircuit, qubits: List[int]) -> None:
    n = len(qubits)
    for j in range(n // 2):
        circ.swap(qubits[j], qubits[n - 1 - j])
    for j in range(n - 1, -1, -1):
        for m in range(j - 1, -1, -1):
            circ.cp(-pi / (2 ** (j - m)), qubits[j], qubits[m])
        circ.h(qubits[j])

# ---------- controlled multiply-by-a mod 15 ----------
def c_amod15(a: int) -> QuantumCircuit:
    if a not in (2, 4, 7, 8, 11, 13):
        raise ValueError("For N=15 demo, a must be in {2,4,7,8,11,13}.")
    qc = QuantumCircuit(5, name=f"c*{a} mod 15")
    if a == 2:
        qc.ccx(0, 4, 1); qc.ccx(0, 1, 2); qc.ccx(0, 2, 3); qc.ccx(0, 3, 4)
    elif a == 4:
        qc.ccx(0, 3, 1); qc.ccx(0, 4, 2); qc.ccx(0, 1, 3); qc.ccx(0, 2, 4)
    elif a == 7:
        qc.ccx(0, 4, 3); qc.ccx(0, 3, 2); qc.ccx(0, 2, 1); qc.ccx(0, 1, 4)
    elif a == 8:
        qc.ccx(0, 1, 4); qc.ccx(0, 4, 3); qc.ccx(0, 3, 2); qc.ccx(0, 2, 1)
    elif a == 11:
        qc.ccx(0, 2, 4); qc.ccx(0, 4, 1); qc.ccx(0, 1, 3); qc.ccx(0, 3, 2)
    elif a == 13:
        qc.ccx(0, 2, 1); qc.ccx(0, 1, 2); qc.ccx(0, 4, 3); qc.ccx(0, 3, 4)
    return qc

def c_apow_mod15(a: int, power: int) -> QuantumCircuit:
    reps = 1 << power
    base = c_amod15(a)
    qc = QuantumCircuit(5, name=f"c*{a}^(2^{power}) mod 15")
    for _ in range(reps):
        qc.compose(base, inplace=True)
    return qc

# ---------- order-finding circuit ----------
def shor_order_finding_circuit(a: int, n_count: int = 8) -> QuantumCircuit:
    qc = QuantumCircuit(n_count + 4, n_count)
    qc.x(n_count)  # |0001> work register (value 1 mod 15)
    for q in range(n_count):
        qc.h(q)
    for k in range(n_count):
        capow = c_apow_mod15(a, k)
        qc = qc.compose(capow, qubits=[k, n_count, n_count + 1, n_count + 2, n_count + 3], inplace=False)
    iqft(qc, list(range(n_count)))
    qc.measure(range(n_count), range(n_count))
    return qc

# ---------- one attempt ----------
def shor_factor_N15(a: int = 2, n_count: int = 8, shots: int = 8192) -> Dict:
    qc = shor_order_finding_circuit(a=a, n_count=n_count)
    sim = AerSimulator()
    t0 = time.time()
    result = sim.run(transpile(qc, sim), shots=shots).result()
    elapsed = time.time() - t0
    counts = result.get_counts()

    top_bits = max(counts, key=counts.get)
    s = int(top_bits, 2)
    phase = s / (2 ** n_count)
    r = Fraction(phase).limit_denominator(15).denominator

    N = 15
    p = q = None
    success = False
    if r % 2 == 0 and r != 0:
        x = pow(a, r // 2, N)
        p = gcd(x - 1, N); q = gcd(x + 1, N)
        if 1 < p < N and 1 < q < N:
            success = True
            p, q = sorted([p, q])

    # save histogram
    import matplotlib.pyplot as plt
    labels = sorted(counts, key=counts.get, reverse=True)[:16]
    values = [counts[k] for k in labels]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(labels, values)
    ax.set_xlabel("Counting register outcome")
    ax.set_ylabel("Counts")
    ax.set_title(f"Shor N=15, a={a}  r={r}  factors={None if not success else (p,q)}")
    plt.xticks(rotation=45)
    plt.tight_layout()
    png_path = OUTDIR / f"shor_counts_N15_a{a}.png"
    fig.savefig(png_path, dpi=200)
    plt.close(fig)
    print(f"[ok] saved PNG: {png_path}")

    # append CSV
    write_header = not CSV.exists() or CSV.stat().st_size == 0
    with open(CSV, "a") as f:
        if write_header:
            f.write("N,a,n_count,shots,top_bits,phase,r,p,q,success,elapsed_s\n")
        f.write(f"15,{a},{n_count},{shots},{top_bits},{phase:.8f},{r},{p},{q},{int(success)},{elapsed:.6f}\n")
    print(f"[ok] appended CSV: {CSV}")

    return {"a": a, "phase": phase, "r": r, "p": p, "q": q, "success": success, "counts": counts, "elapsed": elapsed}

# ---------- scan ----------
def shor_scan_bases(n_count: int = 8,
                    shots: int = 16384,
                    bases: Tuple[int, ...] = (7, 11, 13, 2, 4, 8)) -> Dict:
    last = {}
    for a in bases:
        out = shor_factor_N15(a=a, n_count=n_count, shots=shots)
        last = out
        if out.get("success"):
            return out
    return last

# ---------- CLI ----------
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--bases", type=str, default="7,11,13,2,4,8", help="comma-separated bases a")
    ap.add_argument("--ncount", type=int, default=8, help="counting-register size")
    ap.add_argument("--shots", type=int, default=16384)
    args = ap.parse_args()

    bases = tuple(int(x) for x in args.bases.split(",") if x.strip())
    res = shor_scan_bases(n_count=args.ncount, shots=args.shots, bases=bases)
    print(f"a={res.get('a')}  r={res.get('r')}  p={res.get('p')}  q={res.get('q')}  success={res.get('success')}  elapsed_s={res.get('elapsed')}")
