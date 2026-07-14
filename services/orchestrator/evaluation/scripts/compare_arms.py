#!/usr/bin/env python3
"""compare_arms.py — the head-to-head table: pipeline arms vs external (Claude Code / …) arms.

Joins per-pair results from any number of arms into one markdown table on the SYMMETRIC strict
metric (`equiv` = queries_equivalent / queries_expected, identical machinery for every arm), with
the pipeline's judge-inclusive accepted-rate (`q_acc`) as a supplementary column where available.

Inputs:
  * pipeline arms: `--pipeline <label>=<summary_by_pair.csv>` (from aggregate_results.py)
  * external arms: `--external <label>=<results.csv>`        (from score_external.py; several rows
    per pair average; batch-variant rows of one pair aggregate by query counts)

An external results.csv accumulates rows from EVERY model run through that arm (the matrix runs
opus/fable/sonnet, or both Gemini tiers). When the file holds more than one distinct `model`,
the arm is automatically SPLIT into one column per model (label `<label>:<model>`); pass
`--external label=csv@<model-substring>` to select a single model's rows instead.

Usage:
  uv run --project evaluation python evaluation/scripts/compare_arms.py \\
      --pipeline our_approach=evaluation/out/agg-9-7/summary_by_pair.csv \\
      --external claude_code=evaluation/out/external/claude_code/results.csv \\
      --out evaluation/out/compare_arms.md
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

# canonical short pair names, in display order
_PAIR_ORDER = ["dapper-mongo", "efcore-mongo", "nhib-mongo",
               "dapper-neo4j", "efcore-neo4j", "nhib-neo4j"]


def _short_pair(s: str) -> str:
    s = (s or "").lower()
    src = "dapper" if "dapper" in s else "efcore" if "efcore" in s or "entity" in s else \
          "nhib" if "nhib" in s else "?"
    tgt = "mongo" if "mongo" in s else "neo4j" if "neo4j" in s else "?"
    return f"{src}-{tgt}"


def _f(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_pipeline(path: Path) -> dict[str, dict]:
    """summary_by_pair.csv → {pair: {equiv, q_acc, pass, n}} (skips the ALL row)."""
    out: dict[str, dict] = {}
    with path.open() as fh:
        for row in csv.DictReader(fh):
            pair = _short_pair(row.get("pair", ""))
            if "?" in pair:
                continue
            out[pair] = {
                "equiv": _f(row.get("equiv_rate") or row.get("equiv")),
                "q_acc": _f(row.get("query_accuracy") or row.get("q_acc")),
                "pass": _f(row.get("pass_rate") or row.get("pass")),
                "n": row.get("n"),
            }
    return out


def load_external(path: Path, model_filter: str | None = None) -> dict[str, dict[str, dict]]:
    """score_external results.csv → {model: {pair: {equiv, pass, n}}} aggregated by query counts.

    Grouped by the `model` column so a matrix results.csv (several models per approach) yields one
    arm per model instead of blurring them together. `model_filter` (substring) selects one model.
    """
    acc: dict[tuple[str, str], dict] = defaultdict(lambda: {"eq": 0, "exp": 0, "passed": 0, "n": 0})
    with path.open() as fh:
        for row in csv.DictReader(fh):
            pair = _short_pair(row.get("pair_slug") or row.get("pair", ""))
            if "?" in pair:
                continue
            model = row.get("model") or "?"
            if model_filter and model_filter not in model:
                continue
            a = acc[(model, pair)]
            a["eq"] += int(_f(row.get("queries_equivalent")) or 0)
            a["exp"] += int(_f(row.get("queries_expected")) or 0)
            a["passed"] += 1 if str(row.get("passed")).lower() in ("true", "1", "1.0") else 0
            a["n"] += 1
    out: dict[str, dict[str, dict]] = defaultdict(dict)
    for (model, p), a in acc.items():
        out[model][p] = {"equiv": (a["eq"] / a["exp"]) if a["exp"] else None,
                         "q_acc": None, "pass": a["passed"] / a["n"] if a["n"] else None,
                         "n": a["n"]}
    return dict(out)


def _fmt(v: float | None) -> str:
    return "—" if v is None else f"{v:.2f}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pipeline", action="append", default=[], metavar="LABEL=CSV")
    ap.add_argument("--external", action="append", default=[], metavar="LABEL=CSV")
    ap.add_argument("--out", default=None, help="write markdown here (default: stdout)")
    args = ap.parse_args()

    arms: list[tuple[str, dict[str, dict]]] = []
    for spec in args.pipeline:
        label, _, path = spec.partition("=")
        arms.append((label, load_pipeline(Path(path))))
    for spec in args.external:
        label, _, path = spec.partition("=")
        path, _, model_filter = path.partition("@")
        by_model = load_external(Path(path), model_filter or None)
        if len(by_model) == 1:
            arms.append((label, next(iter(by_model.values()))))
        else:
            for model, data in sorted(by_model.items()):
                arms.append((f"{label}:{model}", data))
    if not arms:
        raise SystemExit("give at least one --pipeline or --external arm")

    pairs = [p for p in _PAIR_ORDER if any(p in data for _, data in arms)]
    pairs += sorted({p for _, d in arms for p in d} - set(pairs))

    lines = ["# Arms head-to-head — strict execution equivalence (`equiv`)", ""]
    header = "| pair | " + " | ".join(f"{lbl} equiv (pass, n)" for lbl, _ in arms) + " |"
    lines += [header, "|" + "---|" * (len(arms) + 1)]
    for p in pairs:
        cells = []
        for _, data in arms:
            d = data.get(p)
            cells.append("—" if not d else f"{_fmt(d['equiv'])} ({_fmt(d['pass'])}, {d['n']})")
        lines.append(f"| {p} | " + " | ".join(cells) + " |")
    # overall = mean of per-pair equiv over pairs the arm ran
    overall = []
    for _, data in arms:
        vals = [d["equiv"] for d in data.values() if d["equiv"] is not None]
        overall.append(_fmt(sum(vals) / len(vals)) if vals else "—")
    lines.append("| **mean** | " + " | ".join(f"**{v}**" for v in overall) + " |")
    lines += ["", "`equiv` = queries execution-equivalent / expected (final snapshot, identical "
              "machinery for every arm). `pass` = all-queries-pass rate. Pipeline arms' "
              "judge-inclusive `q_acc` intentionally NOT the headline — see "
              "out/challenging-claude-code.md (metric symmetry).", ""]

    text = "\n".join(lines)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
