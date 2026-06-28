#!/usr/bin/env python3
"""score_predictions.py — E3 step 2: score harvested predictions against the frozen reference.

For every prediction set written by extract_predictions.py:

    <pred_root>/<dataset>/<pair>/<model>/<run_id>/{schema,queries}.<ext>

it locates the matching frozen reference:

    <ref_root>/<dataset>/<pair>/{schema,queries}.<ext>

and computes, per artifact (schema, queries):
  - CodeBLEU (structural: syntax + AST + data-flow)  -- SECONDARY, similarity not correctness
  - normalized exact match + token overlap            -- crude surface similarity

CodeBLEU leads NOTHING here: the headline functional metric is computational accuracy
(execution-equivalence pass@1) from aggregate_traces.py. CodeBLEU is reported only as a
well-caveated structural similarity number (it penalises equivalent-but-restructured code).

Usage:
  pip install codebleu tree-sitter tree-sitter-java tree-sitter-c-sharp   # see eval-requirements.txt
  python score_predictions.py --pred-root ../predictions --ref-root ../reference --out ./out
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import normalized_exact_match, token_overlap  # noqa: E402

ARTIFACTS = ["schema", "queries"]


def lang_for_pair(pair_slug: str) -> str:
    d = pair_slug.split("__")[-1] if "__" in pair_slug else pair_slug
    if any(t in d for t in ("java", "spring", "neo4j", "mongodb")):
        return "java"
    if any(t in d for t in ("net", "csharp", "dapper", "nhibernate", "entity-framework")):
        return "c_sharp"
    return "java"


def find_reference(ref_root: Path, dataset: str, pair: str, artifact: str) -> Path | None:
    for ext in ("java", "cs"):
        p = ref_root / dataset / pair / f"{artifact}.{ext}"
        if p.exists():
            return p
    return None


def _codebleu(ref: str, hyp: str, lang: str) -> dict[str, float] | None:
    """Full CodeBLEU breakdown. Returns the aggregate + its 4 components so the data-flow/ngram
    degeneracy is visible: on some inputs CodeBLEU scores even an IDENTICAL file well below 1.0
    (data-flow match degenerates to 0), which is precisely why it is reported as a secondary,
    structural-similarity signal and never as a correctness measure."""
    try:
        from codebleu import calc_codebleu  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        r = calc_codebleu([ref], [hyp], lang=lang, weights=(0.25, 0.25, 0.25, 0.25))
        return {k: round(float(r[k]), 4) for k in
                ("codebleu", "ngram_match_score", "weighted_ngram_match_score",
                 "syntax_match_score", "dataflow_match_score")}
    except Exception as e:
        print(f"[warn] codebleu failed ({lang}): {e}")
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pred-root", default="../predictions")
    ap.add_argument("--ref-root", default="../reference")
    ap.add_argument("--dataset", default="wwi")
    ap.add_argument("--out", default="./out")
    args = ap.parse_args()

    pred_root, ref_root = Path(args.pred_root), Path(args.ref_root)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    codebleu_available = True
    base = pred_root / args.dataset
    if not base.exists():
        raise SystemExit(f"no predictions under {base}")

    for pair_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        pair = pair_dir.name
        lang = lang_for_pair(pair)
        run_dirs = [p for p in pair_dir.rglob("*")
                    if p.is_dir() and (any(p.glob("*.java")) or any(p.glob("*.cs")))]
        for run_dir in sorted(run_dirs):
            for artifact in ARTIFACTS:
                pred = next(iter(run_dir.glob(f"{artifact}.*")), None)
                if not pred:
                    continue
                ref = find_reference(ref_root, args.dataset, pair, artifact)
                if not ref:
                    rows.append({"pair": pair, "model": run_dir.parent.name, "run": run_dir.name,
                                 "artifact": artifact, "lang": lang, "codebleu": None, "ngram": None,
                                 "syntax": None, "dataflow": None, "exact": None,
                                 "token_overlap": None, "note": "no reference"})
                    continue
                rt, ht = ref.read_text(encoding="utf-8"), pred.read_text(encoding="utf-8")
                cb = _codebleu(rt, ht, lang)
                if cb is None:
                    codebleu_available = False
                rows.append({"pair": pair, "model": run_dir.parent.name, "run": run_dir.name,
                             "artifact": artifact, "lang": lang,
                             "codebleu": cb["codebleu"] if cb else None,
                             "ngram": cb["ngram_match_score"] if cb else None,
                             "syntax": cb["syntax_match_score"] if cb else None,
                             "dataflow": cb["dataflow_match_score"] if cb else None,
                             "exact": normalized_exact_match(rt, ht),
                             "token_overlap": round(token_overlap(rt, ht), 4), "note": ""})

    if not rows:
        print("no prediction/reference pairs found")
        return

    fields = ["pair", "model", "run", "artifact", "lang", "codebleu", "ngram", "syntax",
              "dataflow", "exact", "token_overlap", "note"]
    with (out_dir / "codebleu.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"scored {len(rows)} artifact(s)  (codebleu {'OK' if codebleu_available else 'UNAVAILABLE — pip install -r eval-requirements.txt'})")
    print(f"{'pair':<40}{'artifact':<9}{'codebleu':>9}{'ngram':>7}{'syntax':>7}{'dflow':>7}{'tok':>6}  run")
    for r in rows:
        print(f"{r['pair'][:39]:<40}{r['artifact']:<9}{str(r['codebleu']):>9}{str(r['ngram']):>7}"
              f"{str(r['syntax']):>7}{str(r['dataflow']):>7}{str(r['token_overlap']):>6}  {r['run'][:8]} {r['note']}")
    print(f"\nwrote {out_dir / 'codebleu.csv'}")


if __name__ == "__main__":
    main()
