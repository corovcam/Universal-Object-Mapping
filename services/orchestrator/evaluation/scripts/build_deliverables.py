#!/usr/bin/env python3
"""build_deliverables.py — assemble the single thesis-attachment folder with every
experimental deliverable: results, charts, analysis markdown, LangSmith trace exports,
exported prompts, external-arm conversations/captures, predictions, frozen references,
aimock fixtures, and a README that maps + provenances all of it.

The script only COPIES existing artifacts (idempotent; re-run any time — e.g. after the
extended/xl experiment finishes, add its tag with --tag). Nothing is recomputed here;
regeneration commands are documented in the README it writes.

Usage (from services/orchestrator):
  uv run python evaluation/scripts/build_deliverables.py \
      --out evaluation/out/deliverables --tag 20260709-150203 [--tag <xl-tag>] [--no-aimock]
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", ".pytest_cache")


def copy(src: Path, dst: Path) -> None:
    if not src.exists():
        print(f"  [skip] {src} (missing)")
        return
    if src.is_dir():
        shutil.copytree(src, dst, ignore=IGNORE, dirs_exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    print(f"  {src} -> {dst}")


def sizeof(path: Path) -> tuple[int, int]:
    files = [p for p in path.rglob("*") if p.is_file()]
    return len(files), sum(p.stat().st_size for p in files)


README = """\
# UOM evaluation — experimental deliverables

Generated {date} by `evaluation/scripts/build_deliverables.py` (services/orchestrator of the
Universal-Object-Mapping repository). Canonical experiment tag(s): {tags}.
Generator model: einfra/kimi-k2.7 (10 repetitions x 6 framework pairs x 15-query full bundle
unless a folder says otherwise). Headline metric everywhere: STRICT execution equivalence —
per-query result-set fingerprints (count + first/last sample, DeepDiff) checked against the
live source database by a deterministic checker; LLM-as-a-judge scores are secondary and
always labelled as such.

## Folder map

| folder | contents |
|---|---|
| `charts/` | Final thesis figures (PNG 300dpi + PDF) + `summary.md` + tidy `per_rep.csv`. Regenerate: `uv run python evaluation/scripts/plot_final.py`. |
| `results/codebleu.csv` | CodeBLEU + components per run/artifact vs the frozen execution-verified references (`make eval_codebleu`). |
| `results/node_tokens.csv` | Per-node LLM token/time attribution per run, harvested from LangSmith traces (`harvest_node_tokens.py`); `loop_tokens` = translation loop only (generate_translation_node onward) — the fair-comparison token number used against the SOTA arms. Also carries per-run final per-query equivalence. |
| `results/aggregates-10-7/` | Cross-run aggregation of the canonical run (pass@k, per-pair rates; `aggregate_results.py`). |
| `results/final-report/` | FINAL-REPORT.md + the three canonical experiment sets (A: qwen3.5/small/15rep baseline, B: kimi/full/10rep main, C: kimi/batched/1rep) as fetched experiment CSVs. |
| `results/external-arms/` | SOTA arm scoring: one dir per scored run (result.json, sandbox logs, assembled harnesses) + `results.csv` per arm. `selftest/` = the harness scored against our own pipeline's output (sanity 15/15). |
| `results/experiments-summary-*.json` | Raw run-summary JSON emitted by `run_experiment.py` per experiment launch. |
| `results/rejudge/` | Judge-only re-runs over finished experiments (`rejudge_experiments.py`, reference-aware prompts). |
| `traces/` | LangSmith experiment exports (one CSV per experiment; inputs/outputs/feedback per repetition) via `fetch_experiments.py`. `10-7-2026/` = canonical 10-rep run. |
| `prompts/` | The exact prompts exported for the external arms (`export_manual_prompts.py`): `system.txt`, `user.txt`, `adaptation.txt`, combined `prompt.md` — byte-identical to what the pipeline's own generation stage receives. |
| `conversations/` | Full external-arm conversations: `conversation-claude_code-*.jsonl` (Claude Code session transcript, one JSON event per line incl. API-reported usage), `capture-*.md` (the arm's final answer), `usage-claude_code-*.json` (deduplicated API token usage + wall clock). The Antigravity CLI exposes no usage; its capture + combined prompt are the whole record. |
| `predictions/` | Extracted translated schema/queries per run (the artifacts CodeBLEU scores). |
| `reference/` | Frozen CodeBLEU ground truth: per variant/pair, the first execution-verified (15/15) repetition, harness form, with PROVENANCE.md + provenance.json (`freeze_reference.py`). |
| `aimock-fixtures/` | aimock recording fixtures of the canonical run — the raw LLM request/response pairs per repetition (reproduction: replay against the recorded fixtures instead of a live model). |
| `analysis/` | Dated analysis notes written during the evaluation campaign (run post-mortems, SOTA-arm comparison, harness/reference design doc). |

## Provenance / honesty notes

* **External-arm usage is API-reported or absent — never estimated.** Claude Code
  (claude-opus-4-8, effort high): usage from its own session transcript (single call:
  input 4, cache_write 109,929, cache_read 54,784, output 87,972 incl. extended thinking;
  wall 1,309 s), priced at verified 2026-07-10 list prices ($5/$25 per MTok, cache write
  1.25x, cache read 0.1x). Antigravity CLI exposes no usage counters, so its tokens/price
  are shown as "not reported"; only wall clocks measurable from file timestamps are given.
* **gemini-3.5-flash was scored twice** (2026-07-09: 14/15; 2026-07-10 re-generation: 4/15).
  The re-run overwrote the first capture file in place, so rep1's raw capture markdown is
  gone (its extracted predictions and scores survive); rep2's generation wall clock is
  unrecoverable. Charts aggregate both runs (n=2) and mark unmeasurable resources.
* **CodeBLEU references are execution-verified pipeline outputs**, not human gold: no human
  Java reference exists for this task, so per pair the first strictly 15/15 repetition is
  frozen as reference (provenance recorded); that repetition is excluded from its own arm's
  aggregates (it scores 1.0 against itself by construction).
* The per-run `tokens`/`total_cost` in trace exports cover the WHOLE pipeline run; the
  SOTA-arm token comparison uses `results/node_tokens.csv:loop_tokens` (translation loop
  only) for symmetry, and says so on the figure.

## Reproduction pointers (in the repository)

* Experiment driver: `evaluation/scripts/run_experiment.py` (`make eval_full`, `eval_extended`, ...).
* External arms: `evaluation/scripts/claude_arm.sh`, `agy_arm.sh`, `external_arms_matrix.sh`
  (export prompt -> run arm -> score with `score_external.py` on the same checker).
* Scoring/aggregation: `score_predictions.py` (CodeBLEU), `aggregate_results.py`,
  `fetch_experiments.py` (LangSmith -> CSV), `harvest_node_tokens.py`, `rejudge_experiments.py`.
* Charts: `evaluation/scripts/plot_final.py`.

{manifest_table}
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="evaluation/out/deliverables")
    ap.add_argument("--tag", action="append", default=[],
                    help="experiment tag(s) whose predictions + aimock fixtures to bundle "
                         "(default: 20260709-150203)")
    ap.add_argument("--no-aimock", action="store_true",
                    help="skip the (large) aimock fixture recordings")
    args = ap.parse_args()
    tags = args.tag or ["20260709-150203"]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print("== charts")
    copy(Path("evaluation/out/charts-final"), out / "charts")

    print("== results")
    res = out / "results"
    copy(Path("evaluation/out/codebleu.csv"), res / "codebleu.csv")
    copy(Path("evaluation/out/node_tokens.csv"), res / "node_tokens.csv")
    copy(Path("evaluation/out/agg-10-7"), res / "aggregates-10-7")
    copy(Path("evaluation/out/final"), res / "final-report")
    copy(Path("evaluation/out/external"), res / "external-arms")
    copy(Path("evaluation/out/rejudge"), res / "rejudge")
    for f in sorted(Path("out").glob("experiments-summary-*.json")):
        copy(f, res / f.name)

    print("== traces (LangSmith experiment exports)")
    copy(Path("evaluation/traces/10-7-2026"), out / "traces" / "10-7-2026")
    copy(Path("evaluation/traces/final-experiments"), out / "traces" / "final-experiments")

    print("== prompts + conversations (external arms)")
    for exp in sorted(Path("evaluation/manual-eval/wwi").iterdir()):
        if not exp.is_dir():
            continue
        pdst = out / "prompts" / exp.name
        for f in ("system.txt", "user.txt", "adaptation.txt", "prompt.md"):
            copy(exp / f, pdst / f)
        cdst = out / "conversations" / exp.name
        for f in sorted(exp.iterdir()):
            if (f.name.startswith(("capture", "conversation-", "usage-"))
                    and not f.name.startswith(".")):
                copy(f, cdst / f.name)

    print("== predictions + reference")
    for tag in tags:
        copy(Path(f"evaluation/predictions/wwi/{tag}"), out / "predictions" / tag)
    for ext in ("external-claude_code", "external-antigravity"):
        copy(Path(f"evaluation/predictions/wwi/{ext}"), out / "predictions" / ext)
    copy(Path("evaluation/reference/wwi"), out / "reference" / "wwi")

    if not args.no_aimock:
        print("== aimock fixtures")
        for tag in tags:
            copy(Path(f"evaluation/aimock/wwi/{tag}"), out / "aimock-fixtures" / tag)

    print("== analysis markdown")
    for f in sorted(Path("out").glob("*.md")):
        copy(f, out / "analysis" / f.name)

    # ---- manifest + README
    rows = ["| folder | files | size |", "|---|---:|---:|"]
    total_f = total_b = 0
    for d in sorted(p for p in out.iterdir() if p.is_dir()):
        nf, nb = sizeof(d)
        total_f += nf
        total_b += nb
        rows.append(f"| `{d.name}/` | {nf} | {nb / 1e6:,.1f} MB |")
    rows.append(f"| **total** | **{total_f}** | **{total_b / 1e6:,.1f} MB** |")
    (out / "MANIFEST.json").write_text(json.dumps(
        {d.name: {"files": sizeof(d)[0], "bytes": sizeof(d)[1]}
         for d in sorted(out.iterdir()) if d.is_dir()}, indent=2), encoding="utf-8")
    (out / "README.md").write_text(
        README.format(date=time.strftime("%Y-%m-%d"), tags=", ".join(tags),
                      manifest_table="## Bundle contents\n\n" + "\n".join(rows)),
        encoding="utf-8")
    print(f"\n== deliverables ready: {out}  ({total_f} files, {total_b / 1e6:,.1f} MB)")


if __name__ == "__main__":
    main()
