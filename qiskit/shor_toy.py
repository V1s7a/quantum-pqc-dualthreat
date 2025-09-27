"""
shor_toy.py — Shor demo for N=15 using QPE with modern Qiskit.
Builds the counting-register circuit, runs on Aer, infers the order r,
and returns non-trivial factors when possible.

Key improvements:
- Uses stable hand-built circuits for N=15 (no deprecated Shor class).
- Has small helpers you can reuse from other scripts (e.g., shor_plot.py).
- Tries multiple bases (a in {2,4,7,8,11,13}) if desired.
"""

from math import gcd, pi
from fractions import Fraction
from typing import Dict, List, Optional, Tuple

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator


# ---------- inverse QFT on a list of qubits ----------
def iqft(circ: QuantumCircuit, qubits: List[int]) -> None:
    n = len(qubits)
    # reverse order
    for j in range(n // 2):
        circ.swap(qubits[j], qubits[n - 1 - j])
    # controlled phase rotations + H, walking backwards
    for j in range(n - 1, -1, -1):
        for m in range(j - 1, -1, -1):
            circ.cp(-pi / (2 ** (j - m)), qubits[j], qubits[m])
        circ.h(qubits[j])


# ---------- controlled multiply-by-a mod 15 (tiny, N=15-only) ----------
def c_amod15(a: int) -> QuantumCircuit:
    if a not in (2, 4, 7, 8, 11, 13):
        raise ValueError("For N=15 demo, a must be in {2,4,7,8,11,13}.")
    qc = QuantumCircuit(5, name=f"c*{a} mod 15")
    # q0: control  |  q1..q4: 4-bit work register (encodes y)
    # These CCX patterns implement small permutations used in the Qiskit Textbook demo.
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
    """Controlled multiply by a^(2^power) mod 15 (repeat base block)."""
    reps = 1 << power
    base = c_amod15(a)
    qc = QuantumCircuit(5, name=f"c*{a}^(2^{power}) mod 15")
    for _ in range(reps):
        qc.compose(base, inplace=True)
    return qc


# ---------- QPE circuit builder ----------
def shor_order_finding_circuit(a: int, n_count: int = 8) -> QuantumCircuit:
    """
    Returns a circuit with:
      - n_count qubits (counting register),
      - 4 work qubits initialised to |0001> (value 1 mod 15),
      - controlled-U^(2^k) blocks (U = multiply-by-a mod 15),
      - inverse QFT and measurement of the counting register.
    """
    qc = QuantumCircuit(n_count + 4, n_count)

    # Prepare |1> in the work register (least significant work qubit is at index n_count)
    qc.x(n_count)

    # Superposition on counting register
    for q in range(n_count):
        qc.h(q)

    # Controlled-U^(2^k) applications (k from 0 upward)
    for k in range(n_count):
        capow = c_apow_mod15(a, k)
        # Map capow qubits [0..4] -> [control k, work n_count..n_count+3]
        qc = qc.compose(capow, qubits=[k, n_count, n_count + 1, n_count + 2, n_count + 3], inplace=False)

    # Inverse QFT and measure counting register
    iqft(qc, list(range(n_count)))
    qc.measure(range(n_count), range(n_count))
    return qc


# ---------- One-shot run for a chosen base ----------
def shor_factor_N15(a: int = 2, n_count: int = 8, shots: int = 8192) -> Dict:
    qc = shor_order_finding_circuit(a=a, n_count=n_count)
    sim = AerSimulator()
    result = sim.run(transpile(qc, sim), shots=shots).result()
    counts = result.get_counts()

    # Infer phase from most frequent outcome s / 2^n_count
    top_bits = max(counts, key=counts.get)
    s = int(top_bits, 2)
    phase = s / (2 ** n_count)
    r = Fraction(phase).limit_denominator(15).denominator

    # Classical post-processing
    N = 15
    factors = None
    if r % 2 == 0:
        x = pow(a, r // 2, N)
        p = gcd(x - 1, N)
        q = gcd(x + 1, N)
        if 1 < p < N and 1 < q < N:
            factors = sorted([p, q])

    return {"a": a, "phase": phase, "r": r, "factors": factors, "counts": counts}


# ---------- Scan several bases; return first that really factors N=15 ----------
def shor_scan_bases(
    n_count: int = 8,
    shots: int = 16384,
    bases: Tuple[int, ...] = (7, 11, 13, 2, 4, 8),  # more reliable first
) -> Dict:
    """
    Try several bases and (if needed) a couple of stricter settings.
    Return the first result with EVEN r and non-trivial factors.
    Falls back to the best last attempt if nothing succeeds.
    """
    # Escalate a little if the first try is noisy
    n_count_list = (n_count, n_count + 1)          # e.g., 8 -> 9
    shots_list   = (shots, max(shots, 32768))      # e.g., 16k -> 32k

    last = {}
    for a in bases:
        for nc in n_count_list:
            for sh in shots_list:
                out = shor_factor_N15(a=a, n_count=nc, shots=sh)
                last = out
                # accept only if r is even and we got non-trivial factors
                if out.get("factors") and (out.get("r", 1) % 2 == 0):
                    return out
    # If nothing produced factors, return the last attempt for debugging/plotting
    return last



if __name__ == "__main__":
    res = shor_scan_bases()
    print(f"a={res['a']}  phase≈{res['phase']:.6f}  r={res['r']}  factors={res['factors']}")
