"""
shor_plot.py — robust Shor visualization for N=15.

Tries bases a in {2,4,7,8,11,13} until one yields valid factors.
Plots top measurement outcomes and annotates phase, order, and factors.
"""

import os
import matplotlib.pyplot as plt
from shor_toy import shor_scan_bases

def run_and_plot(n_count=8, shots=16384, top_k=10,
                 bases=(2, 4, 7, 8, 11, 13),
                 png_path="reports/shor_measurements.png"):
    os.makedirs(os.path.dirname(png_path) or ".", exist_ok=True)

    # Scan bases until one produces non-trivial factors
    res = shor_scan_bases(n_count=n_count, shots=shots, bases=bases)
    counts = res["counts"]

    # Take top-K outcomes
    top_items = sorted(counts.items(), key=lambda x: -x[1])[:top_k]
    labels, values = zip(*top_items)

    # Build title with factors if found
    title = f"Shor QPE N=15, a={res['a']} — phase≈{res['phase']:.3f}, r={res['r']}"
    if res.get("factors"):
        title += f", factors={res['factors']}"

    # Plot
    plt.figure(figsize=(9, 4))
    plt.bar(labels, values)
    plt.xlabel("Measurement (top outcomes)")
    plt.ylabel("Counts")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(png_path, dpi=200)

    print(f"Saved {png_path}")
    print("Top outcomes:", top_items)
    print(f"phase≈{res['phase']:.6f}, r={res['r']}, factors={res['factors']}")

if __name__ == "__main__":
    run_and_plot()
