#!/usr/bin/env python3
"""
Generate Shor figures from CSVs:
  - reports/shor_success_by_base.png
  - reports/shor_quantum_elapsed_by_base.png  (requires elapsed_s in CSV)
  - reports/shor_classical_vs_quantum_N15.png (requires classical CSV)
"""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
R = REPO / "reports"
R.mkdir(exist_ok=True)

QCSV = R / "shor_lab_results.csv"
CCSV = R / "classical_factor_timing.csv"

if not QCSV.exists():
    raise SystemExit(f"Missing {QCSV}. Run qiskit/shor_lab.py first.")

df = pd.read_csv(QCSV)

# -------- Figure 1: success by base --------
fig1, ax1 = plt.subplots(figsize=(6, 4))
sr = df.groupby("a")["success"].mean().sort_index()
sr.plot(kind="bar", ax=ax1)
ax1.set_ylim(0, 1)
ax1.set_ylabel("Success rate")
ax1.set_xlabel("Base a")
ax1.set_title("Shor N=15 — success by base")
plt.tight_layout()
out1 = R / "shor_success_by_base.png"
fig1.savefig(out1, dpi=200); plt.close(fig1)
print(f"[ok] wrote {out1}")

# -------- Figure 2: quantum elapsed by base (if available) --------
if "elapsed_s" in df.columns:
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    em = df.groupby("a")["elapsed_s"].mean().sort_index()
    em.plot(kind="bar", ax=ax2)
    ax2.set_ylabel("Elapsed (s)")
    ax2.set_xlabel("Base a")
    ax2.set_title("Shor N=15 — simulator elapsed time by base")
    plt.tight_layout()
    out2 = R / "shor_quantum_elapsed_by_base.png"
    fig2.savefig(out2, dpi=200); plt.close(fig2)
    print(f"[ok] wrote {out2}")
else:
    print("[warn] 'elapsed_s' missing in shor CSV; re-run qiskit/shor_lab.py to enable elapsed plots.")

# -------- Figure 3: classical vs quantum (N=15) --------
def _read_classical_rows(path):
    Ns, times = [], []
    with open(path, "r", encoding="utf-8") as f:
        header = f.readline()  # N,time_s,factors_json
        for line in f:
            # split at the first two commas only: N, time_s, (rest = JSON)
            parts = line.strip()
            if not parts:
                continue
            a, b, *_ = parts.split(",", 2)
            try:
                N_val = int(a.strip())
                t_val = float(b.strip())
            except Exception:
                continue
            Ns.append(N_val); times.append(t_val)
    return Ns, times

if CCSV.exists() and "elapsed_s" in df.columns:
    Ns_list, Ts_list = _read_classical_rows(CCSV)
    print("[debug] classical Ns (manual parse):", sorted(set(Ns_list)))
    classical_s = None
    for N_val, t_val in zip(Ns_list, Ts_list):
        if N_val == 15:
            classical_s = t_val
            break

    if classical_s is not None:
        quantum_avg = float(pd.to_numeric(df.get("elapsed_s"), errors="coerce").dropna().mean())
        fig3, ax3 = plt.subplots(figsize=(6, 4))
        ax3.bar(["Classical (N=15)", "Quantum sim (avg)"], [classical_s, quantum_avg])
        ax3.set_ylabel("Time (s)")
        ax3.set_title("N=15 factorization: classical vs quantum simulator")
        for i, v in enumerate([classical_s, quantum_avg]):
            ax3.text(i, v, f"{v:.6f}s", ha="center", va="bottom")
        plt.tight_layout()
        out3 = R / "shor_classical_vs_quantum_N15.png"
        fig3.savefig(out3, dpi=200); plt.close(fig3)
        print(f"[ok] wrote {out3}")
    else:
        print("[info] No N=15 row found in classical CSV (manual parse).")
else:
    print("[info] Skipping classical vs quantum figure (missing classical CSV or elapsed_s).")
