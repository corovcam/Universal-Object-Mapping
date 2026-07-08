#!/usr/bin/env python3
"""fetch_experiments.py — download LangSmith experiments from "UOM Final Experiments" to local CSVs.

The LangSmith UI shows one experiment at a time and exports one CSV at a time. This pulls a whole
SET of experiments (selected by ``--run-tag``) down to disk in the SAME CSV schema the manual UI
export produces, so ``aggregate_results.py`` / ``plot_results.py`` consume them unchanged. READ-ONLY:
it only lists/reads runs + feedback; it never writes to the dataset.

For each experiment it writes ``<out>/<experiment-name>.csv`` with one row per root run (= one
repetition of one dataset example), columns = the deterministic metrics from the run's ``outputs``
plus the LLM-judge feedback scores, and ``id`` = the dataset ``reference_example_id`` (so pass@k can
group repetitions of the same example). Point the aggregator at ``<out>`` with ``--pair-from-name``.

Usage:
  uv run --project evaluation python evaluation/scripts/fetch_experiments.py \
      --run-tag 20260705-231626 --out evaluation/traces/final-experiments/B --env ../.env
  # list what's in the dataset (no download):
  uv run --project evaluation python evaluation/scripts/fetch_experiments.py --list --env ../.env
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

DATASET_ID = "56708f08-2697-4af2-b3b7-9172c0e68b4b"  # "UOM Final Experiments"

# Deterministic metric fields we lift out of each run's ``outputs`` into flat CSV columns (the same
# names the manual export uses). ``query_verdicts`` etc. stay inside the JSON ``outputs`` column.
_DET_FIELDS = [
    "accepted", "passed", "compile_pass", "schema_validated", "pass_at_1",
    "queries_expected", "queries_claimed", "queries_accepted", "queries_equivalent",
    "queries_total", "query_accuracy", "query_precision", "query_recall",
    "translation_loops", "wall_clock_s", "generate_model", "pair",
]
# LLM-judge feedback keys (both the legacy boolean judges and the rewritten graded ones).
_JUDGE_FIELDS = [
    "code_correctness", "conciseness", "faithfulness", "hallucination", "translation_equivalence",
]
_COLUMNS = ["id", "session_name", "repetition", *_DET_FIELDS, *_JUDGE_FIELDS, "error", "outputs"]


def _experiments(client, run_tags: set[str] | None):
    """All experiments (projects) for the dataset, optionally filtered to the given run_tags."""
    out = []
    for p in client.list_projects(reference_dataset_id=DATASET_ID):
        md = getattr(p, "metadata", None) or {}
        if run_tags and md.get("run_tag") not in run_tags:
            continue
        out.append((p, md))
    out.sort(key=lambda pm: str(getattr(pm[0], "start_time", None)))
    return out


def _rows_for_experiment(client, project) -> list[dict[str, Any]]:
    """One CSV row per root run: deterministic ``outputs`` fields + judge feedback + example id."""
    runs = list(client.list_runs(project_name=project.name, is_root=True))
    if not runs:
        return []
    # bulk-fetch feedback for all runs in this experiment (one query, not one-per-run)
    fb_by_run: dict[str, dict[str, Any]] = {}
    for f in client.list_feedback(run_ids=[r.id for r in runs]):
        fb_by_run.setdefault(str(f.run_id), {})[f.key] = f.score
    rows = []
    for i, r in enumerate(sorted(runs, key=lambda x: str(x.start_time))):
        out = r.outputs or {}
        fb = fb_by_run.get(str(r.id), {})
        row: dict[str, Any] = {
            "id": str(getattr(r, "reference_example_id", "") or ""),
            "session_name": project.name,
            "repetition": i,
            "error": (out.get("error") or getattr(r, "error", "") or ""),
            # keep the full outputs dict (query_verdicts etc.) as a JSON column, minus the bulky code
            "outputs": json.dumps({k: v for k, v in out.items()
                                   if k not in ("translated_schema_code", "translated_query_code",
                                                "target_validation_harness_code", "predictions")}),
        }
        for k in _DET_FIELDS:
            v = out.get(k)
            row[k] = 1.0 if v is True else 0.0 if v is False else ("" if v is None else v)
        for k in _JUDGE_FIELDS:
            row[k] = "" if fb.get(k) is None else fb.get(k)
        rows.append(row)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-tag", action="append", default=[],
                    help="only fetch experiments with this metadata.run_tag (repeatable)")
    ap.add_argument("--out", default=None, help="output dir for the per-experiment CSVs")
    ap.add_argument("--list", action="store_true", help="just list experiments + run counts, no download")
    ap.add_argument("--env", default="../.env", help=".env with LANGSMITH_* keys")
    args = ap.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv(args.env)
    except Exception:
        pass
    from langsmith import Client

    client = Client()
    run_tags = set(args.run_tag) or None
    exps = _experiments(client, run_tags)
    if not exps:
        raise SystemExit(f"no experiments found (run_tags={run_tags})")

    if args.list:
        print(f"{'start':<12} {'run_tag':<18} {'var':<8} {'gen':<20} {'judge':<20} reps  experiment")
        for p, md in exps:
            print(f"{str(p.start_time)[:10]:<12} {str(md.get('run_tag')):<18} "
                  f"{str(md.get('variant')):<8} {str(md.get('generate_model')):<20} "
                  f"{str(md.get('judge_model')):<20} {str(md.get('num_repetitions')):<5} {p.name}")
        return

    if not args.out:
        raise SystemExit("--out is required unless --list")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for p, _md in exps:
        rows = _rows_for_experiment(client, p)
        with (out_dir / f"{p.name}.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=_COLUMNS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        total += len(rows)
        flag = "  <-- EMPTY" if not rows else ""
        print(f"  {len(rows):>3} runs  {p.name}{flag}", file=sys.stderr)
    print(f"\nwrote {len(exps)} experiment CSV(s), {total} runs total -> {out_dir}")


if __name__ == "__main__":
    main()
