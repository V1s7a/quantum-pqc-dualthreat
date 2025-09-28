#!/usr/bin/env python3
import json, pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

IN_TSV = Path("reports/qsharp_from_clip.tsv")
IN_JSON = Path("reports/qsharp_from_clip.json")
OUTDIR = Path("reports"); OUTDIR.mkdir(parents=True, exist_ok=True)

def load():
    if IN_TSV.exists():
        df = pd.read_csv(IN_TSV, sep="\t")
    else:
        rows = json.loads(IN_JSON.read_text())
        df = pd.DataFrame(rows)
    # coerce numerics
    for c in ["error_budget","logical_qubits","t_factories","t_depth","measurements",
              "code_distance","factory_fraction","t_count","runtime_seconds","physical_qubits"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    # tidy target labels a bit
    if "target" in df.columns:
        df["target"] = df["target"].astype(str)
    # stable ordering by target, then budget ascending
    if "error_budget" in df.columns:
        df = df.sort_values(["target","error_budget"])
    return df

def save_bar(df, y, fname, title, ylab):
    plt.figure()
    # build x labels: target + budget
    x = df["target"].astype(str) + " | ε=" + df["error_budget"].astype(str)
    plt.bar(x, df[y])
    plt.xticks(rotation=45, ha="right")
    plt.title(title)
    plt.ylabel(ylab)
    plt.tight_layout()
    plt.savefig(OUTDIR/fname, dpi=180)
    plt.close()

def main():
    df = load()
    print("[ok] loaded rows:", len(df))
    # write a compact summary TSV you can paste into the paper
    keep = ["target","code","error_budget","logical_qubits","t_count","t_depth",
            "code_distance","t_factories","factory_fraction","runtime_seconds","physical_qubits"]
    (OUTDIR/"qsharp_clip_summary.tsv").write_text(df[keep].to_csv(sep="\t", index=False))
    print(f"[ok] wrote {(OUTDIR/'qsharp_clip_summary.tsv')}")
    # plots
    if "t_count" in df:        save_bar(df, "t_count", "qsharp_clip_tcount.png", "T-count by target & ε", "T-count")
    if "physical_qubits" in df:save_bar(df, "physical_qubits", "qsharp_clip_physq.png", "Physical qubits by target & ε", "Physical qubits")
    if "runtime_seconds" in df:save_bar(df, "runtime_seconds", "qsharp_clip_runtime.png", "Runtime by target & ε", "Runtime (s)")
    print("[ok] wrote plots to reports/:",
          "qsharp_clip_tcount.png qsharp_clip_physq.png qsharp_clip_runtime.png")

if __name__ == "__main__":
    main()
