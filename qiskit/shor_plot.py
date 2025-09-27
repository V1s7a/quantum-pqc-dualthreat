"""
shor_plot.py — Clean histogram for Shor's algorithm (N=15).
Shows only the top measurement outcomes and annotates phase, order, and factors.
"""

import matplotlib.pyplot as plt
from fractions import Fraction
from math import gcd
from qiskit import transpile
from qiskit_aer import AerSimulator
from shor_toy import shor_order_finding_circuit  # uses your circuit builder

def run_and_plot(a=2, n_count=8, shots=8192, top_k=10,
                 png_path="reports/shor_measurements.png"):

    # Build and simulate the QPE circuit
    qc = shor_order_finding_circuit(a=a, n_count=n_count)
    sim = AerSimulator()
    result = sim.run(transpile(qc, sim), shots=shots).result()
    counts = result.get_counts()

    # Take only the top-k measurement outcomes
    top_items = sorted(counts.items(), key=lambda x: -x[1])[:top_k]
    labels, values = zip(*top_items)

    # Infer phase and order from the most frequent outcome
    top_bits = labels[0]
    s = int(top_bits, 2)
    phase = s / (2 ** n_count)
    r = Fraction(phase).limit_denominator(15).denominator

    # Classical post-processing to compute factors of N=15
    N = 15
    factors = None
    if r % 2 == 0:
        x = pow(a, r // 2, N)
        p = gcd(x - 1, N)
        q = gcd(x + 1, N)
        if 1 < p < N and 1 < q < N:
            factors = sorted([p, q])

    # --- Plot ---
    plt.figure(figsize=(8, 4))
    plt.bar(labels, values, color="steelblue")
    plt.xlabel("Measurement (top outcomes)")
    plt.ylabel("Counts")
    title = f"Shor QPE N=15, a={a} — phase≈{phase:.3f}, r={r}"
    if factors:
        title += f", factors={factors}"
    plt.title(title)
    plt.tight_layout()
    plt.savefig(png_path, dpi=200)
    print(f"Saved {png_path}")
    print("Top outcomes:", top_items)
    print("Inferred order r =", r, "factors =", factors)

if __name__ == "__main__":
    run_and_plot()
