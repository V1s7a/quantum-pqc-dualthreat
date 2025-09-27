"""
grover_demo.py — Simple Grover's algorithm demo in Qiskit

Purpose:
- Demonstrates Grover's algorithm on a small 3-qubit search space (8 possible answers).
- Marks one secret "winner" state using an oracle.
- Uses Grover's diffuser to amplify the probability of measuring that secret.
- Plots the histogram of outcomes.

Takeaway:
The secret state (e.g., '101') appears with much higher probability
than all other states after running Grover’s algorithm.
"""

import os
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator


# ---------- Oracle ----------
def grover_oracle(secret: str) -> QuantumCircuit:
    """
    Oracle: the part of Grover's algorithm that 'marks' the secret state.
    - Input: secret string like '101'
    - It flips the phase (like multiplying by -1) of just that secret state.
    - The rest of the states are unchanged.
    """
    n = len(secret)
    qc = QuantumCircuit(n)

    # Step 1: flip qubits for secret '0' bits
    # This ensures the multi-controlled gate below only triggers on the exact secret pattern
    for i, bit in enumerate(reversed(secret)):
        if bit == "0":
            qc.x(i)

    # Step 2: apply a multi-controlled Z (done as H + MCX + H)
    qc.h(n - 1)                          # put last qubit into X-basis
    qc.mcx(list(range(n - 1)), n - 1)    # flip phase if all controls = 1
    qc.h(n - 1)                          # return last qubit to Z-basis

    # Step 3: undo the X flips from Step 1
    for i, bit in enumerate(reversed(secret)):
        if bit == "0":
            qc.x(i)

    qc.name = f"Oracle({secret})"
    return qc


# ---------- Diffuser ----------
def grover_diffuser(n: int) -> QuantumCircuit:
    """
    Diffuser: the part of Grover’s algorithm that amplifies the marked state.
    - Think of it as 'inverting about the average probability.'
    - After the oracle marks the secret, the diffuser boosts its amplitude.
    """
    qc = QuantumCircuit(n)

    # Step 1: put all qubits into X-basis
    qc.h(range(n))
    qc.x(range(n))

    # Step 2: perform multi-controlled Z
    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1)
    qc.h(n - 1)

    # Step 3: undo Step 1
    qc.x(range(n))
    qc.h(range(n))

    qc.name = "Diffuser"
    return qc


# ---------- Main Runner ----------
def run_grover(n: int = 3, secret: str = "101",
               shots: int = 1024,
               png_path: str = "reports/grover_measurements.png"):
    """
    Runs Grover’s algorithm on n qubits to find the secret string.
    - n = number of qubits (search space size = 2^n)
    - secret = the hidden solution we want Grover to find
    - shots = number of times we repeat the experiment
    - png_path = where to save the histogram figure
    """
    os.makedirs(os.path.dirname(png_path) or ".", exist_ok=True)

    # Step 1: Start in uniform superposition (all answers equally likely)
    qc = QuantumCircuit(n, n)
    qc.h(range(n))

    # Step 2: Build oracle and diffuser
    oracle = grover_oracle(secret)
    diffuser = grover_diffuser(n)

    # Step 3: Apply Grover iteration(s)
    # Rule of thumb: ~ pi/4 * sqrt(N) iterations (here N=2^n)
    iterations = 1
    for _ in range(iterations):
        qc.compose(oracle, inplace=True)
        qc.compose(diffuser, inplace=True)

    # Step 4: Measure all qubits
    qc.measure(range(n), range(n))

    # Step 5: Run on simulator
    sim = AerSimulator()
    result = sim.run(transpile(qc, sim), shots=shots).result()
    counts = result.get_counts()

    # Step 6: Plot histogram
    labels, values = zip(*sorted(counts.items(), key=lambda x: -x[1]))
    plt.figure(figsize=(7, 4))
    plt.bar(labels, values)
    plt.xlabel("Measurement outcome")
    plt.ylabel("Counts")
    plt.title(f"Grover’s Algorithm (secret={secret})")
    plt.tight_layout()
    plt.savefig(png_path, dpi=200)

    print(f"Saved {png_path}")
    print("Top outcomes:", counts)


# ---------- Script entry point ----------
if __name__ == "__main__":
    run_grover()
