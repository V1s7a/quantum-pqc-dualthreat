#!/usr/bin/env python3
"""
grover_demo.py — Grover's algorithm demo (Qiskit + AerSimulator)

Examples:
  python qiskit/grover_demo.py --n 3 --secret 101
  python qiskit/grover_demo.py --n 4 --secret 1011 --shots 2048
  python qiskit/grover_demo.py --n 5 --secret 11010 --iters 3
"""
import time, argparse
import matplotlib.pyplot as plt
from pathlib import Path
from math import pi, floor

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

# --- Resolve repo-root-aware output paths ---
# This file lives in <repo>/qiskit/grover_demo.py, so parents[1] == <repo>
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTDIR = REPO_ROOT / "reports"
OUTDIR.mkdir(parents=True, exist_ok=True)
CSV = OUTDIR / "grover_lab_results.csv"

def grover_oracle(secret: str) -> QuantumCircuit:
    n = len(secret)
    qc = QuantumCircuit(n)
    # Flip zeros so MCX triggers exactly on |secret>
    for i, bit in enumerate(reversed(secret)):
        if bit == "0":
            qc.x(i)
    qc.h(n - 1)
    if n == 1:
        qc.z(0)
    else:
        qc.mcx(list(range(n - 1)), n - 1)
    qc.h(n - 1)
    for i, bit in enumerate(reversed(secret)):
        if bit == "0":
            qc.x(i)
    qc.name = f"Oracle({secret})"
    return qc

def grover_diffuser(n: int) -> QuantumCircuit:
    qc = QuantumCircuit(n)
    qc.h(range(n)); qc.x(range(n))
    qc.h(n - 1)
    if n == 1:
        qc.z(0)
    else:
        qc.mcx(list(range(n - 1)), n - 1)
    qc.h(n - 1)
    qc.x(range(n)); qc.h(range(n))
    qc.name = "Diffuser"
    return qc

def run(n: int, secret: str, shots: int, iters: int | None, png_path: Path | None):
    if len(secret) != n or any(c not in "01" for c in secret):
        raise ValueError(f"--secret must be a {n}-bit string of 0/1")
    if iters is None:
        # Optimal Grover iterations ≈ floor((π/4)·2^{n/2})
        iters = max(1, floor((pi / 4) * (2 ** (n / 2))))

    # Default PNG path under <repo>/reports/ if not given
    if png_path is None:
        png_path = OUTDIR / f"grover_n{n}_secret{secret}.png"
    else:
        png_path = Path(png_path)

    # Build circuit
    qc = QuantumCircuit(n, n)
    qc.h(range(n))
    oracle = grover_oracle(secret)
    diffuser = grover_diffuser(n)
    for _ in range(iters):
        qc.compose(oracle, inplace=True)
        qc.compose(diffuser, inplace=True)
    qc.measure(range(n), range(n))

    # Simulate
    backend = AerSimulator()
    t0 = time.time()
    result = backend.run(transpile(qc, backend), shots=shots).result()
    elapsed = time.time() - t0
    counts = result.get_counts()
    success = counts.get(secret, 0)
    success_prob = success / shots

    # Plot histogram
    labels, values = zip(*sorted(counts.items(), key=lambda x: -x[1]))
    plt.figure(figsize=(7, 4))
    plt.bar(labels, values)
    plt.xlabel("Measurement outcome"); plt.ylabel("Counts")
    plt.title(f"Grover (n={n}, secret={secret}, iters={iters})  success={success_prob:.3f}")
    plt.xticks(rotation=45); plt.tight_layout()
    png_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(png_path, dpi=200); plt.close()
    print(f"[ok] saved PNG: {png_path}")

    # Append CSV (always under <repo>/reports/)
    write_header = not CSV.exists() or CSV.stat().st_size == 0
    with open(CSV, "a") as f:
        if write_header:
            f.write("n_bits,secret,iterations,shots,success_prob,elapsed_s\n")
        f.write(f"{n},{secret},{iters},{shots},{success_prob:.6f},{elapsed:.6f}\n")
    print(f"[ok] appended CSV: {CSV}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--secret", type=str, default="101")
    ap.add_argument("--shots", type=int, default=1024)
    ap.add_argument("--iters", type=int, default=None)
    ap.add_argument("--png", type=str, default=None, help="Optional custom PNG path")
    args = ap.parse_args()
    run(args.n, args.secret, args.shots, args.iters, Path(args.png) if args.png else None)
