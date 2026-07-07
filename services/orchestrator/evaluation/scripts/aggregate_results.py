#!/usr/bin/env python3
"""aggregate_results.py — combine LangSmith experiment CSV exports into the thesis result tables.

LangSmith's UI only shows ONE experiment (one pair, one variant) at a time. When the 15-query
workload is run as three 5-query batches (``eval_full``), each pair produces THREE separate
experiments/CSVs, and the UI never shows the pair's aggregate. This script stitches them back
together: point it at a directory of exported experiment CSVs and it produces the per-pair and
overall numbers the thesis reports, on a corrected, defensible ``pass`` definition.

Input layout (either works):
  * ``<root>/<pair>/<*.csv>``  — the traces/<date>/ layout (one subdir per pair; 1 CSV for a
    ``full`` run, or 3 batch CSVs per pair for an ``eval_full`` batched run).
  * ``<root>/<*.csv>``         — a flat directory of exported CSVs (pair read from each CSV's
    ``session_name`` / experiment-name column, or --pair-from-name).

Why not just read ``accepted``: the pipeline's ``accepted`` flag only means "finalized SOME clean
code" — it is True even on a schema-only degenerate finalize that validated zero queries (observed
in the 5-07 efcore-mongo runs: accepted=1 with queries_total=0, compile_pass=0). Every metric here
is built on ``passed`` instead — the canonical functional success, derived per row as::

    passed = compile_pass AND queries_expected > 0 AND queries_accepted >= queries_expected

i.e. the harness compiled/ran AND every query the task demanded was validated execution-equivalent.
This is batch-size agnostic (a batch's ``queries_expected`` is 5, the full variant's is 15), so
batch and full runs aggregate on the same rule. ``run_experiment.run_one`` now emits this same
``passed`` field, so future LangSmith CSVs carry it directly; when absent we derive it from columns.

pass@k (Chen et al. 2021, unbiased estimator): translations often succeed only on a later
repetition, so pass@1 understates the system. For each example we take n = repetitions run and
c = repetitions that passed, and report the probability that a random size-k sample of the reps
contains at least one pass, averaged over examples::

    pass@k = mean_examples( 1 - C(n-c, k) / C(n, k) )

Reported at BOTH the run level (whole-translation success per example) and, when ``query_verdicts``
is present in the row's ``outputs`` JSON, the per-query level (a query passing in ≥1 of k reps).

Judge-vs-equivalence agreement: cross-tabulates each LLM judge score against ``passed`` (the
deterministic execution-equivalence ground truth), so a judge that rejects everything (or accepts
everything) is visible as near-zero agreement — the diagnostic that surfaced the always-reject bug.

Usage:
  python aggregate_results.py --root ../traces/5-7-2026 --out ../out/agg-5-7
  python aggregate_results.py --root ../traces/some-batched-run   # 3 batch CSVs/pair -> per-pair agg
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import os
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

# ------------------------------------------------------------------ pair naming
_PAIR_ABBR = {
    "dotnet_efcore": "efcore", "dotnet_dapper": "dapper", "dotnet_nhibernate": "nhib",
    "net-entity-framework": "efcore", "net-dapper": "dapper", "net-nhibernate": "nhib",
    "java_spring_data_mongodb": "mongo", "java_spring_data_neo4j": "neo4j",
    "java-spring-data-mongodb": "mongo", "java-spring-data-neo4j": "neo4j",
}
# Fixed order so the table/plots are stable regardless of filesystem ordering.
PAIR_ORDER = [
    "dapper-mongo", "efcore-mongo", "nhib-mongo",
    "dapper-neo4j", "efcore-neo4j", "nhib-neo4j",
]

# Union of judge feedback keys across the old and rewritten judge sets, so this aggregates both
# legacy CSVs (with ``hallucination``) and new scaffold-aware runs (with ``faithfulness``). Judges
# absent from a given run are simply skipped (graded=0), never plotted as a fake 0.
JUDGE_KEYS = ["code_correctness", "conciseness", "faithfulness", "translation_equivalence",
              "hallucination"]


def _short_pair(name: str) -> str:
    """Normalise a raw pair/dir/experiment name to a canonical short slug (e.g. 'efcore-mongo')."""
    n = name.lower()
    for raw, ab in _PAIR_ABBR.items():
        n = n.replace(raw, ab)
    # collapse an experiment prefix like 'uom-our_approach-efcore-mongo-full-kimi_k27'
    for p in PAIR_ORDER:
        if p in n:
            return p
    # last resort: strip to the src-tgt tokens we recognise
    toks = [t for t in n.replace("->", "-").replace("__", "-").split("-") if t in
            {"efcore", "dapper", "nhib", "mongo", "neo4j"}]
    if len(toks) >= 2:
        return f"{toks[0]}-{toks[-1]}"
    return name


# ------------------------------------------------------------------ row parsing
def _f(row: dict, key: str) -> float | None:
    v = (row.get(key) or "").strip()
    if v in ("", "None", "nan"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _passed(row: dict) -> bool:
    """Canonical functional success, derived from CSV columns (see module docstring).

    Prefer an explicit ``passed`` column (emitted by newer run_experiment runs); otherwise derive
    it from compile_pass + queries_accepted/queries_expected, with query_accuracy as a fallback.
    """
    p = _f(row, "passed")
    if p is not None:
        return p >= 1.0
    compile_ok = (_f(row, "compile_pass") or 0.0) >= 1.0
    exp = _f(row, "queries_expected")
    acc = _f(row, "queries_accepted")
    if exp is not None and acc is not None and exp > 0:
        return compile_ok and acc >= exp
    qa = _f(row, "query_accuracy")
    return compile_ok and qa is not None and qa >= 1.0


def _outputs(row: dict) -> dict[str, Any]:
    raw = row.get("outputs")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


# ------------------------------------------------------------------ pass@k
def pass_at_k(n: int, c: int, k: int) -> float | None:
    """Unbiased pass@k (Chen et al. 2021), numerically stable. n=reps, c=passing reps.

    Returns None when k > n (can't sample k reps from fewer than k).
    """
    if k > n:
        return None
    if c <= 0:
        return 0.0
    if n - c < k:
        return 1.0
    return 1.0 - math.prod((n - c - i) / (n - i) for i in range(k))


def _mean(xs: Sequence[float | None]) -> float | None:
    vals = [x for x in xs if x is not None]
    return round(sum(vals) / len(vals), 4) if vals else None


# ------------------------------------------------------------------ aggregation
def load_rows(root: Path, pair_from_name: bool) -> list[dict]:
    """Load every experiment CSV under ``root`` into rows tagged with a canonical ``_pair`` and the
    source CSV. Handles both the per-pair-subdir layout and a flat directory of CSVs.
    """
    csv_files = sorted(glob.glob(str(root / "*" / "*.csv"))) + sorted(glob.glob(str(root / "*.csv")))
    csv_files = sorted(set(csv_files))
    rows: list[dict] = []
    for cf in csv_files:
        subdir = os.path.basename(os.path.dirname(cf))
        with open(cf, newline="") as fh:
            for r in csv.DictReader(fh):
                if pair_from_name or subdir == os.path.basename(str(root)):
                    pair = _short_pair(r.get("session_name") or os.path.basename(cf))
                else:
                    pair = _short_pair(subdir)
                r["_pair"] = pair
                r["_csv"] = os.path.basename(cf)
                rows.append(r)
    return rows


def summarize_pair(rows: list[dict]) -> dict[str, Any]:
    """Per-pair aggregate over all its rows (all batches, all repetitions)."""
    n = len(rows)
    passed = [1.0 if _passed(r) else 0.0 for r in rows]
    # run-level pass@k: group reps by example id, average the estimator over examples.
    by_example: dict[str, list[bool]] = defaultdict(list)
    for r in rows:
        by_example[r.get("id") or r.get("_csv", "?")].append(_passed(r))
    passk: dict[str, float | None] = {}
    for k in (1, 2, 3):
        passk[f"pass@{k}"] = _mean([pass_at_k(len(v), sum(v), k) for v in by_example.values()])

    # Per-query pass@k from query_verdicts. Denominator = the union of query ids the example ever
    # produced a verdict for (its query set); a rep that produced NO verdict for a query counts as a
    # fail for that query (not omitted), so a rep that saved nothing lowers the metric honestly
    # instead of vanishing from it.
    reps_by_example: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        eid = r.get("id") or r.get("_csv", "?")
        reps_by_example[eid].append({str(q): str(v) for q, v in
                                     (_outputs(r).get("query_verdicts") or {}).items()})
    q_by: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for eid, reps in reps_by_example.items():
        qids = {q for rep in reps for q in rep}
        for qid in qids:
            for rep in reps:
                q_by[(eid, qid)].append(rep.get(qid, "").lower().startswith("pass"))
    q_passk: dict[str, float | None] = {}
    if q_by:
        for k in (1, 2, 3):
            q_passk[f"query_pass@{k}"] = _mean([pass_at_k(len(v), sum(v), k) for v in q_by.values()])

    return {
        "runs": n,
        "pass_rate": _mean(passed),
        "accept_rate_raw": _mean([_f(r, "accepted") for r in rows]),
        "compile_rate": _mean([_f(r, "compile_pass") for r in rows]),
        "query_accuracy": _mean([_f(r, "query_accuracy") for r in rows]),
        "query_precision": _mean([_f(r, "query_precision") for r in rows]),
        "query_recall": _mean([_f(r, "query_recall") for r in rows]),
        "queries_equivalent": _mean([_f(r, "queries_equivalent") for r in rows]),
        "queries_expected": _mean([_f(r, "queries_expected") for r in rows]),
        "translation_loops": _mean([_f(r, "translation_loops") for r in rows]),
        "wall_clock_s": _mean([_f(r, "wall_clock_s") for r in rows]),
        **passk,
        **q_passk,
        "errors": sum(1 for r in rows if (r.get("error") or "").strip() not in ("", "None")),
    }


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    """Pearson correlation, or None if undefined (fewer than 2 points or a constant series)."""
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    return round(sxy / math.sqrt(sxx * syy), 4)


def judge_agreement(rows: list[dict]) -> dict[str, dict[str, Any]]:
    """Per-judge agreement with the deterministic ground truth, for GRADED (continuous 0..1) judges.

    The judges score the FRACTION of the translation satisfying a criterion, so they should TRACK the
    deterministic per-query accuracy rather than match a single boolean. We report, per judge:
      * ``mean_score``     — average judge score.
      * ``mean_on_pass`` / ``mean_on_fail`` — average judge score on runs the deterministic checker
        passed vs failed; a discriminating judge scores clearly higher on passes (the old always-reject
        bug shows up as mean_on_pass≈0).
      * ``corr_equivalence`` — Pearson correlation of the judge score with the deterministic
        execution-equivalence fraction (``queries_equivalent / queries_expected``) across runs — the
        headline: does the graded judge move with REAL execution-equivalence? We correlate against
        queries_equivalent, NOT query_accuracy: query_accuracy is queries_accepted/queries_expected and
        the accepted-count folds in the pipeline's own "accepted in an earlier loop" decisions, so
        correlating against it partly measures the judge against the pipeline's self-assessment rather
        than against ground-truth equivalence.
      * ``agree_on_pass`` / ``agree_on_fail`` / ``accuracy`` — a thresholded (score≥0.5) view kept for
        continuity with the boolean-era tables.
    """
    out: dict[str, dict[str, Any]] = {}
    for key in JUDGE_KEYS:
        tp = tn = fp = fn = graded = 0
        js_on_pass: list[float] = []
        js_on_fail: list[float] = []
        js_vals: list[float] = []
        eq_vals: list[float] = []
        for r in rows:
            js = _f(r, key)
            if js is None:
                continue
            graded += 1
            truth = _passed(r)
            (js_on_pass if truth else js_on_fail).append(js)
            # ground truth = execution-equivalence fraction (queries_equivalent / queries_expected)
            qe, qx = _f(r, "queries_equivalent"), _f(r, "queries_expected")
            if qe is not None and qx and qx > 0:
                js_vals.append(js)
                eq_vals.append(min(1.0, qe / qx))
            judge_pos = js >= 0.5
            if truth and judge_pos:
                tp += 1
            elif truth and not judge_pos:
                fn += 1
            elif not truth and judge_pos:
                fp += 1
            else:
                tn += 1
        pos, neg = tp + fn, tn + fp
        out[key] = {
            "graded": graded,
            "mean_score": _mean(js_vals or [_f(r, key) for r in rows]),
            "mean_on_pass": round(sum(js_on_pass) / len(js_on_pass), 4) if js_on_pass else None,
            "mean_on_fail": round(sum(js_on_fail) / len(js_on_fail), 4) if js_on_fail else None,
            "corr_equivalence": _pearson(js_vals, eq_vals),
            "agree_on_pass": round(tp / pos, 4) if pos else None,
            "agree_on_fail": round(tn / neg, 4) if neg else None,
            "accuracy": round((tp + tn) / graded, 4) if graded else None,
        }
    return out


# ------------------------------------------------------------------ table rendering
def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.3f}".rstrip("0").rstrip(".") if v != int(v) else str(int(v))
    return str(v)


def render_table(per_pair: dict[str, dict], overall: dict) -> str:
    cols = [
        ("pair", "pair"), ("runs", "n"), ("pass_rate", "pass"),
        ("pass@1", "p@1"), ("pass@2", "p@2"), ("pass@3", "p@3"),
        ("compile_rate", "compile"), ("query_accuracy", "q_acc"),
        ("query_precision", "q_prec"), ("query_recall", "q_rec"),
        ("translation_loops", "loops"), ("wall_clock_s", "wall_s"), ("errors", "err"),
    ]
    header = "| " + " | ".join(h for _, h in cols) + " |"
    sep = "|" + "|".join("---" for _ in cols) + "|"
    lines = [header, sep]
    for pair in sorted(per_pair, key=lambda p: PAIR_ORDER.index(p) if p in PAIR_ORDER else 99):
        s = per_pair[pair]
        cells = [pair] + [_fmt(s.get(key)) for key, _ in cols[1:]]
        lines.append("| " + " | ".join(cells) + " |")
    overall_cells = ["**ALL**"] + [_fmt(overall.get(key)) for key, _ in cols[1:]]
    lines.append("| " + " | ".join(overall_cells) + " |")
    return "\n".join(lines)


def render_judge_table(agree: dict[str, dict]) -> str:
    lines = ["| judge | graded | mean | mean_on_pass | mean_on_fail | corr_equiv | accuracy |",
             "|---|---|---|---|---|---|---|"]
    for key, s in agree.items():
        if not s.get("graded"):
            continue
        lines.append(f"| {key} | {_fmt(s['graded'])} | {_fmt(s['mean_score'])} | "
                     f"{_fmt(s['mean_on_pass'])} | {_fmt(s['mean_on_fail'])} | "
                     f"{_fmt(s['corr_equivalence'])} | {_fmt(s['accuracy'])} |")
    return "\n".join(lines)


# ------------------------------------------------------------------ main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True, help="dir of experiment CSVs (per-pair subdirs or flat)")
    ap.add_argument("--out", default=None, help="output dir (default: <root>/aggregate)")
    ap.add_argument("--pair-from-name", action="store_true",
                    help="read the pair from each CSV's experiment name instead of the subdir")
    args = ap.parse_args()

    root = Path(args.root)
    out_dir = Path(args.out) if args.out else root / "aggregate"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = load_rows(root, args.pair_from_name)
    if not rows:
        raise SystemExit(f"no experiment CSVs found under {root}")

    by_pair: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_pair[r["_pair"]].append(r)

    per_pair = {pair: summarize_pair(rs) for pair, rs in by_pair.items()}
    per_pair_judge = {pair: judge_agreement(rs) for pair, rs in by_pair.items()}
    overall = summarize_pair(rows)
    overall_judge = judge_agreement(rows)

    # ---- per-pair summary CSV
    summary_csv = out_dir / "summary_by_pair.csv"
    metric_keys = sorted({k for s in per_pair.values() for k in s})
    with summary_csv.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["pair", *metric_keys])
        for pair in sorted(per_pair, key=lambda p: PAIR_ORDER.index(p) if p in PAIR_ORDER else 99):
            w.writerow([pair, *[per_pair[pair].get(k) for k in metric_keys]])
        w.writerow(["ALL", *[overall.get(k) for k in metric_keys]])

    # ---- combined per-row CSV with derived passed (feeds the plot script)
    rows_csv = out_dir / "rows.csv"
    flat_keys = ["_pair", "_csv", "id", "repetition", "accepted", "passed_derived", "compile_pass",
                 "queries_expected", "queries_accepted", "query_accuracy", "query_precision",
                 "query_recall", "queries_equivalent", "translation_loops", "wall_clock_s",
                 *JUDGE_KEYS, "error"]
    with rows_csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=flat_keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({**r, "passed_derived": int(_passed(r)),
                        "error": (r.get("error") or "").strip()[:80]})

    # ---- machine-readable full aggregate
    agg_json = out_dir / "aggregate.json"
    agg_json.write_text(json.dumps({
        "root": str(root), "total_runs": len(rows),
        "per_pair": per_pair, "overall": overall,
        "judge_agreement_per_pair": per_pair_judge, "judge_agreement_overall": overall_judge,
    }, indent=2))

    # ---- human-readable results table (markdown)
    table_md = out_dir / "results_table.md"
    md = [
        f"# UOM evaluation results — {root.name}",
        "",
        f"Aggregated over **{len(rows)} runs** across {len(by_pair)} pair(s). "
        "`pass` = compiled/ran AND every demanded query validated execution-equivalent "
        "(not the inflated `accept_rate_raw`). pass@k over repetitions (Chen et al. unbiased).",
        "",
        "> **Batch granularity note:** each row is one repetition of one dataset EXAMPLE. When the "
        "15-query workload was run as three 5-query batches (`eval_full`), the three batch CSVs are "
        "stitched into the pair here, but each batch is a distinct example — so `pass`/`pass@k` are "
        "per-batch (a batch passes when its 5 queries all pass), averaged across the batches, NOT a "
        "reconstructed all-15-in-one-task number (that is the `full` variant / `eval_full_bundled`). "
        "The two are different denominators by design.",
        "",
        "## Per-pair results",
        "",
        render_table(per_pair, overall),
        "",
        "## LLM-judge agreement with deterministic execution-equivalence",
        "",
        "Graded judges score a fraction [0,1]. `mean_on_pass` / `mean_on_fail` = mean judge score on "
        "runs the deterministic checker passed vs failed (a good judge scores clearly higher on "
        "passes; an always-reject judge shows no separation). `corr_equiv` = Pearson correlation with "
        "the deterministic execution-equivalence fraction (queries_equivalent/queries_expected; "
        "negative = inverted polarity, e.g. the legacy hallucination judge).",
        "",
        render_judge_table(overall_judge),
        "",
    ]
    # per-query pass@k line if available
    if any("query_pass@1" in s for s in per_pair.values()):
        md += ["## Per-query pass@k", "",
               "| pair | query_pass@1 | query_pass@2 | query_pass@3 |", "|---|---|---|---|"]
        for pair in sorted(per_pair, key=lambda p: PAIR_ORDER.index(p) if p in PAIR_ORDER else 99):
            s = per_pair[pair]
            md.append(f"| {pair} | {_fmt(s.get('query_pass@1'))} | {_fmt(s.get('query_pass@2'))} | "
                      f"{_fmt(s.get('query_pass@3'))} |")
        md.append("")
    table_md.write_text("\n".join(md))

    # ---- console
    print(render_table(per_pair, overall))
    print("\nLLM-judge agreement with deterministic pass:")
    print(render_judge_table(overall_judge))
    print(f"\nwrote:\n  {summary_csv}\n  {rows_csv}\n  {agg_json}\n  {table_md}")


if __name__ == "__main__":
    main()
