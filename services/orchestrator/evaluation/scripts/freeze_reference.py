#!/usr/bin/env python3
"""freeze_reference.py — freeze per-VARIANT harness-form CodeBLEU references from a verified run.

Why: the legacy references under reference/wwi/<pair>/ are production-style ``Queries.queryN()``
methods from the pre-harness era. Every current arm (our pipeline, claude_code, antigravity)
emits the harness contract instead (``final class QueryN { static ... query(); static Map<...>
harness(template); }``), so scoring those predictions against the legacy references measures the
contract mismatch, not translation similarity. The fix (user decision 2026-07-10): references
live in per-variant folders whose content IS the harness form:

    reference/wwi/<variant>/<pair_slug>/{schema,queries}.java   + PROVENANCE.md
    reference/wwi/<variant>/provenance.json                     (machine-readable, incl. the
                                                                 source run id so scorers can
                                                                 exclude it from its own arm)

There is no human-written Java gold, so the reference for each pair is the first repetition of
the given run whose FINAL deterministic equivalence check was perfect (all queries strictly
``Equivalent`` against the live WWI stores) — the strongest correctness evidence available.
The winning repetition is found from the aimock recordings: each eval prompt embeds
``run_id=<uuid>`` (matching the predictions dir ``our_approach-<uuid[:8]>``) and the final
"[Query Equivalence Results]" JSON.

Usage:
  uv run --project evaluation python evaluation/scripts/freeze_reference.py \
      --tag 20260709-150203 --variant full [--expected 15] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import date
from pathlib import Path

_HERE = Path(__file__).resolve().parent
EVAL_ROOT = _HERE.parent

# aimock short pair names -> prediction/reference pair slugs
SRC = {"dapper": "net-dapper", "efcore": "net-entity-framework-core", "nhib": "net-nhibernate"}
DST = {"mongo": "java-spring-data-mongodb", "neo4j": "java-spring-data-neo4j"}

_NONCE = re.compile(r"eval-run-nonce run_id=([0-9a-f-]{36})")
_EQ_BLOCK = re.compile(r"Query Equivalence Results\]\\n```json\\n(.*?)\\n```", re.S)


def pair_slug(short: str) -> str | None:
    try:
        s, d = short.split("-", 1)
        return f"{SRC[s]}__{DST[d]}"
    except (ValueError, KeyError):
        return None


def final_equivalence(rec_dir: Path) -> tuple[str | None, dict[str, str]]:
    """Return (run_uuid, {query_id: status}) from the LAST eval prompt in the recording."""
    run_id: str | None = None
    statuses: dict[str, str] = {}
    for f in sorted((rec_dir / "recorded").glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for fx in data.get("fixtures", []):
            um = (fx.get("match") or {}).get("userMessage") or ""
            if "Query Equivalence Results" not in um:
                continue
            m = _NONCE.search(um)
            if m:
                run_id = m.group(1)
            # the block sits inside a repr'd ToolMessage, so \n is the 2-char sequence
            blocks = _EQ_BLOCK.findall(um.replace("\\\\n", "\\n"))
            if not blocks:
                continue
            raw = blocks[-1].replace("\\n", "\n").replace('\\"', '"')
            try:
                parsed = json.loads(raw)
                statuses = {str(q): str(v.get("status") if isinstance(v, dict) else v)
                            for q, v in parsed.items()}
            except Exception:
                continue
    return run_id, statuses


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", required=True, help="run tag, e.g. 20260709-150203")
    ap.add_argument("--variant", required=True, help="experiment variant (small/full/extended/batchN/xl)")
    ap.add_argument("--dataset", default="wwi")
    ap.add_argument("--expected", type=int, default=15, help="queries expected per bundle")
    ap.add_argument("--aimock-root", default=str(EVAL_ROOT / "aimock"))
    ap.add_argument("--pred-root", default=str(EVAL_ROOT / "predictions"))
    ap.add_argument("--ref-root", default=str(EVAL_ROOT / "reference"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tag_dir = Path(args.aimock_root) / args.dataset / args.tag
    if not tag_dir.exists():
        raise SystemExit(f"no aimock recordings under {tag_dir}")

    ref_variant_dir = Path(args.ref_root) / args.dataset / args.variant
    provenance: dict[str, dict] = {}
    prov_path = ref_variant_dir / "provenance.json"
    if prov_path.exists():
        provenance = json.loads(prov_path.read_text(encoding="utf-8"))

    for pair_dir in sorted(p for p in tag_dir.iterdir() if p.is_dir()):
        slug = pair_slug(pair_dir.name)
        if not slug:
            print(f"[skip] unrecognized pair dir {pair_dir.name}")
            continue
        winner: tuple[str, Path] | None = None
        for model_dir in sorted(p for p in pair_dir.iterdir() if p.is_dir()):
            for rec in sorted(model_dir.glob(f"our_approach-{args.variant}-*")):
                run_id, statuses = final_equivalence(rec)
                n_eq = sum(1 for s in statuses.values() if s == "Equivalent")
                perfect = n_eq == args.expected and len(statuses) == args.expected
                print(f"  {pair_dir.name} {rec.name[-8:]}: {n_eq}/{len(statuses) or '?'} equivalent"
                      f"{'  <- PERFECT' if perfect else ''}  run={run_id[:8] if run_id else '?'}")
                if perfect and run_id and winner is None:
                    winner = (run_id, rec)
        if not winner:
            print(f"[warn] {pair_dir.name}: no strictly-perfect repetition found — reference NOT frozen")
            continue
        run_id, rec = winner
        # find the matching predictions dir: .../<tag>/<slug>/<model>/our_approach-<uuid8>/
        pred_base = Path(args.pred_root) / args.dataset / args.tag / slug
        matches = list(pred_base.glob(f"*/our_approach-{run_id[:8]}"))
        if not matches:
            print(f"[warn] {pair_dir.name}: predictions dir our_approach-{run_id[:8]} not found under {pred_base}")
            continue
        src = matches[0]
        dst = ref_variant_dir / slug
        print(f"[freeze] {slug}  <-  {src.relative_to(Path(args.pred_root))}")
        if args.dry_run:
            continue
        dst.mkdir(parents=True, exist_ok=True)
        copied = []
        for f in src.iterdir():
            if f.suffix in (".java", ".cs"):
                shutil.copy2(f, dst / f.name)
                copied.append(f.name)
        (dst / "PROVENANCE.md").write_text(
            f"# Reference provenance\n\n"
            f"- frozen: {date.today().isoformat()}\n"
            f"- source run tag: `{args.tag}` (our pipeline, variant `{args.variant}`)\n"
            f"- source run id: `{run_id}` (predictions dir `{src.parent.name}/{src.name}`)\n"
            f"- evidence: final deterministic equivalence check = {args.expected}/{args.expected}\n"
            f"  strictly `Equivalent` against the live WWI stores (count + first/last-sample\n"
            f"  DeepDiff), reconstructed from the aimock recording `{rec.name}`.\n"
            f"- files: {', '.join(copied)}\n\n"
            f"No human-written Java gold exists for this pair; this execution-verified translation\n"
            f"is the frozen structural-similarity reference. When comparing arms with CodeBLEU,\n"
            f"exclude this run id from its own arm's aggregate (see provenance.json).\n",
            encoding="utf-8")
        provenance[slug] = {"tag": args.tag, "variant": args.variant, "run_id": run_id,
                            "pred_dir": f"{src.parent.name}/{src.name}",
                            "recording": rec.name, "frozen": date.today().isoformat()}

    if not args.dry_run and provenance:
        ref_variant_dir.mkdir(parents=True, exist_ok=True)
        prov_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {prov_path}")


if __name__ == "__main__":
    main()
