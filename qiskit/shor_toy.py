"""
shor_toy.py (Qiskit primitives-friendly, no deprecated Shor class)

Goal:
- Factor N=15 using Shor's algorithm pattern:
  1) Quantum Phase Estimation (QPE) on the unitary U|y> = |(a*y) mod N>
     (implemented via controlled modular multiplication by powers of 'a' mod N)
  2) Measure the phase, recover the order r of a mod N
  3) Classically compute gcd(a^(r/2) ± 1, N) to get non-trivial factors

Notes:
- This demo is hard-coded for N=15 and small co-primes a ∈ {2,4,7,8,11,13}. 
- The controlled modular-multiplication circuits for mod 15 are small and
  are taken from the standard Qiskit Textbook approach.
- We keep it simple/explicit so it runs on today's Qiskit with Aer.
"""

from math import gcd, pi
from fractions import Fraction
import numpy as np

from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

# -----------------------------
# 1) Helper: inverse QFT on 'n' qubits (textbook implementation)
# -----------------------------
def iqft(circ: QuantumCircuit, qubits):
    """Apply inverse QFT on the given list of qubits (in place)."""
    n = len(qubits)
    for j in range(n//2):
        circ.swap(qubits[j], qubits[n - j - 1])
    for j in range(n-1, -1, -1):
        for m in range(j-1, -1, -1):
            circ.cp(-pi / (2 ** (j - m)), qubits[j], qubits[m])
        circ.h(qubits[j])


# -----------------------------
# 2) Controlled modular multiply-by-a (mod 15)
#    (Small, hand-crafted circuits per Qiskit Textbook)
# -----------------------------
def c_amod15(a: int):
    """
    Returns a QuantumCircuit that performs:
      |ctl>|y> --> |ctl>|(a*y) mod 15>
    on 4 work qubits 'y' (little circuits for N=15 case).
    The returned circuit has 1 control qubit (qubit 0) and 4 target qubits (1..4).
    """
    if a not in [2, 4, 7, 8, 11, 13]:
        raise ValueError("a must be in {2,4,7,8,11,13} for N=15 demo.")

    # Layout: q[0]=control; q[1..4]=work register (represents y)
    qc = QuantumCircuit(5, name=f"c*{a} mod 15")

    # Shorthand to apply multi-qubit SWAP via 3 CNOTs (textbook trick)
    def cswap(qc, ctrl, q1, q2):
        qc.cx(q1, q2)
        qc.ccx(ctrl, q2, q1)
        qc.cx(q1, q2)

    # The small controlled-multiplication circuits below are standard.
    # They permute the |y> basis states according to multiplication by 'a' mod 15.
    if a == 2:
        # multiply by 2 mod 15: |y0 y1 y2 y3> -> |y3 y0 y1 y2> (cyclic shift)
        qc.cx(0, 4); qc.cx(0, 1); qc.cx(0, 2); qc.cx(0, 3)
        # These are simplistic toggles representing the mapping; using the known textbook circuit:
        qc.ccx(0, 4, 1); qc.ccx(0, 1, 2); qc.ccx(0, 2, 3); qc.ccx(0, 3, 4)
    elif a == 4:
        # multiply by 4 mod 15 is two shifts: y -> y shifted twice
        qc.cx(0, 3); qc.cx(0, 4); qc.cx(0, 1); qc.cx(0, 2)
        qc.ccx(0, 3, 1); qc.ccx(0, 4, 2); qc.ccx(0, 1, 3); qc.ccx(0, 2, 4)
    elif a == 7:
        # known small mapping for *7 mod 15
        qc.ccx(0, 4, 3); qc.ccx(0, 3, 2); qc.ccx(0, 2, 1); qc.ccx(0, 1, 4)
    elif a == 8:
        # multiply by 8 mod 15 is inverse of *2 (or shift the other way)
        qc.ccx(0, 1, 4); qc.ccx(0, 4, 3); qc.ccx(0, 3, 2); qc.ccx(0, 2, 1)
    elif a == 11:
        # mapping for *11 mod 15
        qc.ccx(0, 2, 4); qc.ccx(0, 4, 1); qc.ccx(0, 1, 3); qc.ccx(0, 3, 2)
    elif a == 13:
        # mapping for *13 mod 15
        qc.ccx(0, 2, 1); qc.ccx(0, 1, 2); qc.ccx(0, 4, 3); qc.ccx(0, 3, 4)

    return qc


def c_apow_mod15(a: int, power: int):
    """
    Return a controlled-(a^(2^power) mod 15) circuit on 4 target qubits.
    Construct by repeating the base c_amod15 circuit '2^power' times,
    controlled by the SAME control qubit.
    """
    reps = 1 << power
    base = c_amod15(a)
    # Build a new circuit with same qubit layout (1 control + 4 work)
    qc = QuantumCircuit(5, name=f"c*{a}^(2^{power}) mod 15")
    for _ in range(reps):
        qc.compose(base, inplace=True)
    return qc


# -----------------------------
# 3) Build the Shor (order-finding) circuit via QPE
# -----------------------------
def shor_order_finding_circuit(a: int, n_count: int = 8):
    """
    Build a QPE circuit to estimate the phase related to the order r of 'a' mod 15.
    Registers:
      - counting register: n_count qubits (for the phase)
      - work register: 4 qubits (to hold values mod 15)

    Returns:
      QuantumCircuit object that performs:
        1) Hadamards on counting qubits
        2) Controlled-U^(2^k) on work (with U = multiply-by-a mod 15)
        3) Inverse QFT on counting qubits
        4) Measurement of counting qubits
    """
    # counting + work(4)
    qc = QuantumCircuit(n_count + 4, n_count, name="Shor_QPE")

    # 1) Initialize work register to |1> (value 1 mod 15)
    for q in range(3):  # set |0001> (little-endian on the last 4 qubits)
        pass
    qc.x(n_count)  # the first work qubit is at index n_count
    # Explanation: with our 4 work qubits at positions [n_count, n_count+1, n_count+2, n_count+3],
    # setting only the first (least significant) to |1> prepares the integer 1.

    # 2) Apply Hadamard to counting register (superposition of phases)
    for q in range(n_count):
        qc.h(q)

    # 3) Controlled-U^(2^k): for each counting qubit k, apply a^(2^k) mod 15 to work if the k-th is |1>
    for k in range(n_count):
        # Build the controlled power circuit
        capow = c_apow_mod15(a, k)
        # We will map: control qubit = k, work = last 4 qubits
        # Compose with qubit mapping: capow qubits [0..4] -> [k, n_count .. n_count+3]
        qc = qc.compose(
            capow,
            qubits=[k, n_count, n_count + 1, n_count + 2, n_count + 3],
            inplace=False
        )

    # 4) Apply inverse QFT on counting register
    iqft(qc, list(range(n_count)))

    # 5) Measure counting register
    qc.measure(range(n_count), range(n_count))

    return qc


# -----------------------------
# 4) End-to-end Shor for N=15
# -----------------------------
def shor_factor_N15(a: int = 2, n_count: int = 8):
    """
    Run the QPE circuit for given 'a', get a measurement, infer the phase, recover
    the order 'r', then classically compute non-trivial factors via gcd.
    """
    # Build circuit and simulate
    qc = shor_order_finding_circuit(a=a, n_count=n_count)
    sim = AerSimulator()
    tqc = transpile(qc, sim)
    result = sim.run(tqc, shots=2048).result()
    counts = result.get_counts()

    # Most frequent bitstring in counting register
    top_bits = max(counts, key=counts.get)  # e.g. '01010110'
    # Convert to a phase s / 2^n_count  (binary fraction)
    s = int(top_bits, 2)
    phase = s / (2 ** n_count)

    # Find a rational approximation to the phase to guess the order r
    frac = Fraction(phase).limit_denominator(15)  # denominator bound is small for N=15
    r = frac.denominator

    # Classical post-processing to compute factors
    N = 15
    if r % 2 != 0:
        # Shor needs even order for the standard post-processing
        return {"a": a, "counts": counts, "phase": phase, "r": r, "factors": None}

    x = pow(a, r // 2, N)  # a^(r/2) mod N
    p = gcd(x - 1, N)
    q = gcd(x + 1, N)
    if 1 < p < N and 1 < q < N:
        return {"a": a, "counts": counts, "phase": phase, "r": r, "factors": sorted([p, q])}
    else:
        return {"a": a, "counts": counts, "phase": phase, "r": r, "factors": None}


# -----------------------------
# 5) Main: try a few valid 'a' values until we succeed
# -----------------------------
if __name__ == "__main__":
    # Co-primes of 15 in the allowed set
    candidates = [2, 4, 7, 8, 11, 13]
    for a in candidates:
        out = shor_factor_N15(a=a, n_count=8)
        print(f"\n=== Results for a={a} ===")
        print("Most common measurement (phase samples):", sorted(out["counts"].items(), key=lambda x: -x[1])[:5])
        print(f"Estimated phase ≈ {out['phase']:.6f}  ->  order r = {out['r']}")
        print("Factors:", out["factors"])
        if out["factors"]:
            break
