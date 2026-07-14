#!/usr/bin/env python3
import argparse
import csv
import os
import re
import statistics

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# --- units -----------------------------------------------------------------
TIME_UNIT = {"ns": 1.0, "us": 1e3, "µs": 1e3, "μs": 1e3, "ms": 1e6, "s": 1e9}
SIZE_UNIT = {"B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}


def to_ns(s):
    """Parse a BenchmarkDotNet time cell (e.g. '15,994.2 ns', '750.2 us') to ns."""
    if not s or s.strip() in ("NA", ""):
        return None
    s = s.replace('"', "").replace(",", "").strip()
    m = re.match(r"([\d.]+)\s*([a-zµμ]+)", s)
    return float(m.group(1)) * TIME_UNIT.get(m.group(2), 1.0) if m else None


def to_bytes(s):
    """Parse a BenchmarkDotNet allocation cell (e.g. '10960 B', '6.24 KB') to bytes."""
    if not s or s.strip() in ("NA", ""):
        return None
    s = s.replace('"', "").replace(",", "").strip()
    m = re.match(r"([\d.]+)\s*([KMG]?B)", s)
    return float(m.group(1)) * SIZE_UNIT[m.group(2)] if m else None


def load(path):
    """Read a joined report into {method: {framework: {'mean_ns', 'alloc_b'}}}."""
    rows = {}
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            fw = row["Namespace"].replace("Performance", "")
            rows.setdefault(row["Method"], {})[fw] = {
                "mean_ns": to_ns(row.get("Mean")),
                "alloc_b": to_bytes(row.get("Allocated")),
            }
    return rows


# Canonical query order and the frameworks compared in this thesis.
ORDER = [
    "A1_EntityIdenticalToTable", "A2_LimitedEntity", "A3_MultipleEntitiesFromOneResult",
    "A4_StoredProcedureToEntity", "B1_SelectionOverIndexedColumn",
    "B2_SelectionOverNonIndexedColumn", "B3_RangeQuery", "B4_InQuery", "B5_TextSearch",
    "B6_PagingQuery", "C1_AggregationCount", "C2_AggregationMax", "C3_AggregationSum",
    "D1_OneToManyRelationship", "D2_ManyToManyRelationship", "D3_OptionalRelationship",
    "E1_ColumnSorting", "E2_Distinct", "F1_JSONObjectQuery", "F2_JSONArrayQuery",
    "G1_Union", "G2_Intersection", "H1_Metadata",
]
ORMS = ["Dapper", "EFCore", "NHibernate"]
COLORS = {"Dapper": "#4C72B0", "EFCore": "#DD8452", "NHibernate": "#55A868"}

plt.rcParams.update({
    "font.size": 11, "font.family": "serif", "axes.grid": True,
    "grid.alpha": 0.3, "grid.linestyle": "--", "axes.axisbelow": True,
})


def fig_time_memory(ovh, out):
    labels = [q.split("_")[0] for q in ORDER]

    def grouped(ax, key, ylabel, title):
        x = np.arange(len(ORDER)); w = 0.26
        for i, orm in enumerate(ORMS):
            vals = [ovh[q].get(orm, {}).get(key) or np.nan for q in ORDER]
            ax.bar(x + (i - 1) * w, vals, w, label=orm,
                   color=COLORS[orm], edgecolor="black", linewidth=0.3)
        ax.set_yscale("log")
        ax.set_xticks(x); ax.set_xticklabels(labels, rotation=90, fontsize=8)
        ax.set_ylabel(ylabel); ax.set_title(title, fontsize=12)
        ax.legend(frameon=False, fontsize=12, ncol=3, loc="upper left")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 11))
    grouped(ax1, "mean_ns", "Mean overhead (ns, log scale)", "(a) Per-query time overhead")
    grouped(ax2, "alloc_b", "Allocated memory (bytes, log scale)", "(b) Per-query memory overhead")
    fig.tight_layout()
    path = os.path.join(out, "overhead_time_memory.pdf")
    fig.savefig(path, bbox_inches="tight"); plt.close(fig)
    return path


def fig_vs_fulldb(ovh, full, out):
    # Cheap queries where end-to-end wall-clock is dominated by fixed costs,
    # so the ORMs look near-identical against a live DB but diverge once mocked.
    sel = ["A1_EntityIdenticalToTable", "B1_SelectionOverIndexedColumn",
           "C2_AggregationMax", "E2_Distinct", "H1_Metadata"]
    lab = ["A1", "B1", "C2", "E2", "H1"]
    x = np.arange(len(sel)); w = 0.26

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(10, 4.0))
    for i, orm in enumerate(ORMS):
        axL.bar(x + (i - 1) * w, [full[q][orm]["mean_ns"] / 1e3 for q in sel], w,
                label=orm, color=COLORS[orm], edgecolor="black", linewidth=0.3)
    axL.set_xticks(x); axL.set_xticklabels(lab)
    axL.set_ylabel("Mean wall-clock time (µs)")
    axL.set_title("(a) Full query against live DB\n(Abrahám's setup)", fontsize=12)
    axL.legend(frameon=False, fontsize=12)

    for i, orm in enumerate(ORMS):
        axR.bar(x + (i - 1) * w, [ovh[q][orm]["mean_ns"] for q in sel], w,
                label=orm, color=COLORS[orm], edgecolor="black", linewidth=0.3)
    axR.set_xticks(x); axR.set_xticklabels(lab)
    axR.set_ylabel("Mean overhead (ns)")
    axR.set_title("(b) Mocked DBMS: pure ORM overhead\n(this thesis)", fontsize=12)
    axR.legend(frameon=False, fontsize=12)

    fig.tight_layout()
    path = os.path.join(out, "overhead_vs_fulldb.pdf")
    fig.savefig(path, bbox_inches="tight"); plt.close(fig)
    return path


def print_summary(ovh, full):
    def ratio(q, a, b):
        va, vb = ovh[q].get(a, {}).get("mean_ns"), ovh[q].get(b, {}).get("mean_ns")
        return va / vb if va and vb else None
    ef = [r for q in ORDER if (r := ratio(q, "EFCore", "Dapper")) is not None]
    nh = [r for q in ORDER if (r := ratio(q, "NHibernate", "Dapper")) is not None]
    print("median EFCore/Dapper time ratio:", round(statistics.median(ef), 1))
    print("median NHibernate/Dapper time ratio:", round(statistics.median(nh), 1))
    print("A1 alloc (B) Dapper/EFCore/NHib:",
          {o: ovh["A1_EntityIdenticalToTable"][o]["alloc_b"] for o in ORMS})


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--overhead", default=os.path.join(
        here, "joined", "results",
        "BenchmarkRun-joined-2026-03-08-15-21-56-report.csv"),
        help="overhead (mocked-DBMS) joined report.csv")
    ap.add_argument("--fulldb", default=os.path.join(
        here, "..", "full-db-query", "joined",
        "BenchmarkRun-joined-2025-03-06-16-10-18-report.csv"),
        help="Abraham's full-db-query joined report.csv")
    ap.add_argument("--out", default=os.path.join(here, "figures"),
                    help="output directory for the PDF figures "
                         "(thesis figures were generated with the thesis img/ folder)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    ovh = load(args.overhead)
    full = load(args.fulldb)
    print(f"Loaded {len(ovh)} overhead methods, {len(full)} full-db methods.")
    print("Wrote:", fig_time_memory(ovh, args.out))
    print("Wrote:", fig_vs_fulldb(ovh, full, args.out))
    print_summary(ovh, full)


if __name__ == "__main__":
    main()
