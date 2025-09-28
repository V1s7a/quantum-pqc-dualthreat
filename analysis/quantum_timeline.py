#!/usr/bin/env python3
from math import log2
import csv
from pathlib import Path

# Parameters: change these to match literature or your estimator
baseline_year = 2025
start_devices = [127, 1000]             # current physical qubit counts to start from
targets = [1e6, 1e7]                    # required physical qubits (example)
doubling_months = [12, 18, 24]         # optimistic / baseline / conservative

rows = []
for Qreq in targets:
    for Qstart in start_devices:
        for D in doubling_months:
            years = log2(Qreq/Qstart) * (D/12.0)
            reach_year = baseline_year + years
            rows.append({
                "required_qubits": int(Qreq),
                "start_qubits": Qstart,
                "doubling_months": D,
                "years_to_reach": round(years, 2),
                "reach_year": round(reach_year, 1)
            })

# print table
for r in rows:
    print(r)

# optional: write CSV
Path("reports").mkdir(parents=True, exist_ok=True)
with open("reports/quantum_timeline_scenarios.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
print("Wrote reports/quantum_timeline_scenarios.csv")
