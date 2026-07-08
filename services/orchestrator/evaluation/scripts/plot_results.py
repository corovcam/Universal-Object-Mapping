#!/usr/bin/env python3
"""plot_results.py — matplotlib charts for the UOM evaluation, from experiment CSV exports.

Reuses ``aggregate_results`` to load + summarise the exported LangSmith experiment CSVs (per-pair
subdirs or a flat dir; batched runs are stitched per pair), then renders the thesis figures. Every
chart is "higher is better" and built on the corrected ``pass`` definition (compiled/ran AND every
demanded query validated execution-equivalent), NOT the inflated ``accepted`` flag.

Figures written to ``--out`` (PNG + a combined overview):
  * pass_and_passk      — pass@1/2/3 per pair (translations that succeed on a later retry recovered).
  * funnel              — accepted(raw) → compiled → passed per pair, exposing the accepted-inflation.
  * query_metrics       — per-query accuracy / precision / recall per pair.
  * judge_vs_truth      — each LLM judge's mean score vs its agreement with execution-equivalence;
                          a judge that rejects everything sits near 0 on "agree on real passes".
  * latency             — mean wall-clock seconds per pair.
  * overview            — all of the above in one figure.

NOTE on the hallucination judge: its score is detection-phrased (higher can mean "more faithful" or
"more hallucinated" depending on the prompt); it is plotted but labelled, not assumed higher=better.

Usage:
  uv run --project evaluation python evaluation/scripts/plot_results.py \
      --root evaluation/traces/5-7-2026 --out evaluation/out/charts-5-7
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: write files, never open a window
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aggregate_results import (  # noqa: E402
    JUDGE_KEYS,
    PAIR_ORDER,
    judge_agreement,
    load_rows,
    summarize_pair,
)

# Colour tokens (colour-blind-safe, consistent across figures).
C_PASS = "#2a78d6"     # primary blue (headline pass)
C_GOOD = "#0ca30c"     # green (good/compiled)
C_WARN = "#ec835a"     # amber (partial)
C_BAD = "#d03b3b"      # red (raw/inflated or failure)
C_K = ["#9ecae1", "#4292c6", "#08519c"]  # sequential blues for k=1,2,3


def _ordered_pairs(per_pair: dict) -> list[str]:
    return sorted(per_pair, key=lambda p: PAIR_ORDER.index(p) if p in PAIR_ORDER else 99)


def _bar_labels(ax, bars, fmt="{:.2f}"):
    for b in bars:
        h = b.get_height()
        if h is not None:
            ax.annotate(fmt.format(h), (b.get_x() + b.get_width() / 2, h),
                        ha="center", va="bottom", fontsize=7, xytext=(0, 1),
                        textcoords="offset points")


def _val(d, k):
    v = d.get(k)
    return float(v) if v is not None else 0.0


def plot_pass_and_passk(ax, per_pair: dict) -> None:
    pairs = _ordered_pairs(per_pair)
    x = range(len(pairs))
    w = 0.26
    for i, k in enumerate((1, 2, 3)):
        vals = [_val(per_pair[p], f"pass@{k}") for p in pairs]
        bars = ax.bar([xi + (i - 1) * w for xi in x], vals, w, label=f"pass@{k}", color=C_K[i])
        if i == 2:
            _bar_labels(ax, bars)
    ax.set_title("Pass@k per pair (later retries recover)")
    ax.set_ylabel("pass rate")
    ax.set_ylim(0, 1.05)
    ax.set_xticks(list(x))
    ax.set_xticklabels(pairs, rotation=30, ha="right", fontsize=8)
    ax.legend(fontsize=8)


def plot_funnel(ax, per_pair: dict) -> None:
    pairs = _ordered_pairs(per_pair)
    x = range(len(pairs))
    w = 0.26
    series = [("accept_rate_raw", "accepted (raw flag)", C_BAD),
              ("compile_rate", "compiled/ran", C_WARN),
              ("pass_rate", "passed (equivalent)", C_PASS)]
    for i, (key, label, col) in enumerate(series):
        vals = [_val(per_pair[p], key) for p in pairs]
        ax.bar([xi + (i - 1) * w for xi in x], vals, w, label=label, color=col)
    ax.set_title("Funnel: accepted(raw) → compiled → passed")
    ax.set_ylabel("rate")
    ax.set_ylim(0, 1.05)
    ax.set_xticks(list(x))
    ax.set_xticklabels(pairs, rotation=30, ha="right", fontsize=8)
    ax.legend(fontsize=8)


def plot_query_metrics(ax, per_pair: dict) -> None:
    pairs = _ordered_pairs(per_pair)
    x = range(len(pairs))
    w = 0.26
    # equiv_rate (queries_equivalent/demanded) is uniform across metric eras; accuracy/recall are only
    # populated for the per-query-instrumented runs (empty on the oldest group), so equiv leads.
    series = [("equiv_rate", "equivalence", C_PASS),
              ("query_accuracy", "accuracy", C_GOOD),
              ("query_recall", "recall", C_WARN)]
    for i, (key, label, col) in enumerate(series):
        vals = [_val(per_pair[p], key) for p in pairs]
        ax.bar([xi + (i - 1) * w for xi in x], vals, w, label=label, color=col)
    ax.set_title("Per-query equivalence / accuracy / recall")
    ax.set_ylabel("rate")
    ax.set_ylim(0, 1.05)
    ax.set_xticks(list(x))
    ax.set_xticklabels(pairs, rotation=30, ha="right", fontsize=8)
    ax.legend(fontsize=8)


def plot_judge_vs_truth(ax, overall_judge: dict) -> None:
    # Only judges actually present in this run's CSVs (graded>0); absent ones aren't drawn as fake 0.
    # Graded judges are continuous (0..1): a good judge scores HIGHER on runs the deterministic checker
    # passed than on failed ones — so we plot mean-on-pass vs mean-on-fail (the always-reject bug =
    # mean-on-pass near 0, i.e. no separation).
    keys = [k for k in JUDGE_KEYS if overall_judge.get(k, {}).get("graded")]
    x = range(len(keys))
    w = 0.38
    on_pass = [_val(overall_judge[k], "mean_on_pass") for k in keys]
    on_fail = [_val(overall_judge[k], "mean_on_fail") for k in keys]
    ax.bar([xi - w / 2 for xi in x], on_pass, w, label="mean score on PASSED runs", color=C_PASS)
    ax.bar([xi + w / 2 for xi in x], on_fail, w, label="mean score on FAILED runs", color=C_BAD)
    ax.set_title("LLM judges vs execution-equivalence")
    ax.set_ylabel("mean judge score")
    ax.set_ylim(0, 1.05)
    ax.set_xticks(list(x))
    ax.set_xticklabels([k.replace("_", "\n") for k in keys], fontsize=7)
    ax.legend(fontsize=8)


def plot_latency(ax, per_pair: dict) -> None:
    pairs = _ordered_pairs(per_pair)
    vals = [_val(per_pair[p], "wall_clock_s") for p in pairs]
    x = range(len(pairs))
    bars = ax.bar(list(x), vals, color=C_PASS)
    _bar_labels(ax, bars, fmt="{:.0f}")
    ax.set_title("Mean wall-clock per run")
    ax.set_ylabel("seconds")
    ax.set_xticks(list(x))
    ax.set_xticklabels(pairs, rotation=30, ha="right", fontsize=8)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True, help="dir of experiment CSVs (per-pair subdirs or flat)")
    ap.add_argument("--out", default=None, help="output dir for PNGs (default: <root>/charts)")
    ap.add_argument("--pair-from-name", action="store_true",
                    help="read the pair from each CSV's experiment name instead of the subdir")
    args = ap.parse_args()

    root = Path(args.root)
    out_dir = Path(args.out) if args.out else root / "charts"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = load_rows(root, args.pair_from_name)
    if not rows:
        raise SystemExit(f"no experiment CSVs found under {root}")
    by_pair: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_pair[r["_pair"]].append(r)
    per_pair = {p: summarize_pair(rs) for p, rs in by_pair.items()}
    overall_judge = judge_agreement(rows)

    # individual figures
    singles = [
        ("pass_and_passk", plot_pass_and_passk, per_pair),
        ("funnel", plot_funnel, per_pair),
        ("query_metrics", plot_query_metrics, per_pair),
        ("judge_vs_truth", plot_judge_vs_truth, overall_judge),
        ("latency", plot_latency, per_pair),
    ]
    for name, fn, data in singles:
        fig, ax = plt.subplots(figsize=(7, 4.2))
        fn(ax, data)
        fig.tight_layout()
        fig.savefig(out_dir / f"{name}.png", dpi=130)
        plt.close(fig)

    # combined overview
    fig, axes = plt.subplots(2, 3, figsize=(19, 10))
    plot_pass_and_passk(axes[0][0], per_pair)
    plot_funnel(axes[0][1], per_pair)
    plot_query_metrics(axes[0][2], per_pair)
    plot_judge_vs_truth(axes[1][0], overall_judge)
    plot_latency(axes[1][1], per_pair)
    axes[1][2].axis("off")
    axes[1][2].text(0.0, 0.95,
                    f"UOM evaluation — {root.name}\n"
                    f"{len(rows)} runs, {len(by_pair)} pairs\n\n"
                    "pass = compiled/ran AND every demanded\nquery execution-equivalent.\n"
                    "pass@k over repetitions (Chen et al.).\n\n"
                    "Judges grade against source (graded 0..1).\nLower-left: mean judge score on PASSED\n"
                    "vs FAILED runs — a good judge scores\nhigher on passes; no separation = the\n"
                    "always-reject bug (this run's legacy judges).",
                    fontsize=10, va="top", family="monospace")
    fig.suptitle(f"UOM evaluation results — {root.name}", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out_dir / "overview.png", dpi=130)
    plt.close(fig)

    print(f"wrote {len(singles) + 1} figures to {out_dir}/")
    for name, _, _ in singles:
        print(f"  {out_dir / (name + '.png')}")
    print(f"  {out_dir / 'overview.png'}")


if __name__ == "__main__":
    main()
