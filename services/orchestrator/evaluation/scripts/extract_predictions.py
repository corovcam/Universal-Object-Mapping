#!/usr/bin/env python3
"""extract_predictions.py — E3 step 1: harvest finalize artifacts into a predictions tree.

The finalize-split was built precisely so the clean, user-facing translated code is a stable
projection of *validated* code — a fixed reference for CodeBLEU. This script pulls
`translated_schema_code` / `translated_query_code` from accepted runs and lays them out as:

    <root>/<dataset>/<pair_slug>/<model_slug>/<run_id>/{schema,queries}.<ext>

Use `--reference` to instead write the FROZEN baseline (your first, manually-reviewed accepted
translation per (dataset, pair)) to:

    <root>/<dataset>/<pair_slug>/{schema,queries}.<ext>

Two sources:
  * live LangSmith (default): derives pair/model from the trace, only emits accepted runs.
  * `--from-export run-*.json`: a LangGraph run export (outputs + metadata). It lacks the pair,
    so pass --pair / --lang explicitly for offline extraction.

Usage:
  python extract_predictions.py --limit 50 --root ../predictions
  python extract_predictions.py --from-export ../../run-*.json --pair "efcore->mongo" --lang java \
         --reference --root ../reference
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re

# reuse the validated LangSmith ingestion + scrapers
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aggregate_traces import (  # noqa: E402
    _outputs_dict,
    fetch_root_runs,
    iter_child_runs,
)


# target framework string -> (codebleu lang, file extension)
def target_lang(destination_target: str | None) -> tuple[str, str]:
    d = (destination_target or "").lower()
    if "java" in d or "spring" in d:
        return "java", "java"
    if ".net" in d or "c#" in d or "csharp" in d or "entity framework" in d or "dapper" in d or "nhibernate" in d:
        return "c_sharp", "cs"
    return "java", "java"  # default to the most common target store language


def slug(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "unknown").lower()).strip("-") or "unknown"


def pair_slug(source: str | None, dest: str | None) -> str:
    return f"{slug(source)}__{slug(dest)}"


def _write_artifacts(base: Path, schema: str | None, queries: str | None, ext: str) -> list[str]:
    base.mkdir(parents=True, exist_ok=True)
    written = []
    if schema:
        (base / f"schema.{ext}").write_text(schema, encoding="utf-8")
        written.append(f"schema.{ext}")
    if queries:
        (base / f"queries.{ext}").write_text(queries, encoding="utf-8")
        written.append(f"queries.{ext}")
    return written


def _live_roots(args: argparse.Namespace):
    """Yield (root_run, client). When --run-id is given, pin exactly that run so a frozen
    reference is reproducible (the user's manually-reviewed first-accepted baseline) rather than
    whatever recency happens to return.
    """
    if args.run_id:
        from langsmith import Client
        client = Client()
        yield client.read_run(args.run_id), client
        return
    yield from fetch_root_runs(args.project, args.limit, args.graph_name or None)


def from_live(args: argparse.Namespace, root_dir: Path) -> int:
    n = 0
    for root, client in _live_roots(args):
        out = _outputs_dict(root)
        schema = out.get("translated_schema_code")
        queries = out.get("translated_query_code")
        if not schema and not queries:
            continue  # not an accepted/finalized run — nothing clean to harvest
        children = iter_child_runs(client, str(getattr(root, "trace_id", root.id)))
        ei = next((c for c in children if c.name == "extract_input"), None)
        eo = _outputs_dict(ei) if ei else {}
        src, dst = eo.get("source_target"), eo.get("destination_target")
        meta = (getattr(root, "extra", {}) or {}).get("metadata", {}) or {}
        model = meta.get("model", "unknown")
        lang, ext = target_lang(dst)
        if args.reference:
            base = root_dir / args.dataset / pair_slug(src, dst)
        else:
            base = root_dir / args.dataset / pair_slug(src, dst) / slug(model) / str(root.id)
        w = _write_artifacts(base, schema, queries, ext)
        if w:
            n += 1
            print(f"[{lang}] {pair_slug(src, dst)} {slug(model)} {str(root.id)[:8]} -> {w}")
    return n


def from_predictions(args: argparse.Namespace, root_dir: Path) -> int:
    """OFFLINE reference bootstrap: build the frozen per-pair reference from the predictions tree the
    experiments already wrote (no LangSmith needed). For each pair (the path component containing
    '__') it picks the FIRST run dir that has BOTH schema and queries artifacts and copies them to the
    reference layout ``<root>/<dataset>/<pair>/{schema,queries}.<ext>``.

    NOTE: the reference is meant to be a reviewed, known-good baseline. 'first accepted run' is a
    reasonable automatic default so ``make eval_codebleu`` works out of the box; replace a pair's
    reference files by hand if you want a specific baseline. Idempotent unless --overwrite: existing
    references are kept.
    """
    src = Path(args.from_predictions) / args.dataset
    if not src.exists():
        raise SystemExit(f"no predictions under {src}")

    def _pair_of(p: Path) -> str | None:
        return next((part for part in p.parts if "__" in part), None)

    run_dirs = sorted({p for p in src.rglob("*")
                       if p.is_dir() and any(p.glob("schema.*")) and any(p.glob("queries.*"))})
    seen: dict[str, Path] = {}
    for rd in run_dirs:
        pair = _pair_of(rd)
        if pair and pair not in seen:
            seen[pair] = rd
    n = 0
    for pair, rd in sorted(seen.items()):
        dest = root_dir / args.dataset / pair
        if dest.exists() and any(dest.glob("schema.*")) and not args.overwrite:
            print(f"[keep] {pair} (reference exists; --overwrite to replace)")
            continue
        dest.mkdir(parents=True, exist_ok=True)
        written = []
        for artifact in ("schema", "queries"):
            f = next(iter(rd.glob(f"{artifact}.*")), None)
            if f:
                (dest / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
                written.append(f.name)
        if written:
            n += 1
            print(f"[ref] {pair} <- {rd.name[:8]} -> {written}")
    return n


def from_export(args: argparse.Namespace, root_dir: Path) -> int:
    n = 0
    for path in sorted(glob.glob(args.from_export)):
        d = json.load(open(path))
        out = d.get("outputs", {}) or {}
        schema = out.get("translated_schema_code")
        queries = out.get("translated_query_code")
        if not schema and not queries:
            print(f"[skip] {os.path.basename(path)}: no finalize artifacts")
            continue
        model = (d.get("metadata", {}) or {}).get("model", "unknown")
        lang = args.lang or "java"
        ext = {"c_sharp": "cs", "java": "java"}.get(lang, lang)
        pair = slug(args.pair) if args.pair else "unknown"
        run_id = (d.get("metadata", {}) or {}).get("run_id") or Path(path).stem
        if args.reference:
            base = root_dir / args.dataset / pair
        else:
            base = root_dir / args.dataset / pair / slug(model) / run_id
        w = _write_artifacts(base, schema, queries, ext)
        if w:
            n += 1
            print(f"[{lang}] {pair} {slug(model)} {run_id[:8] if len(run_id) >= 8 else run_id} -> {w}")
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=None, help="LangSmith project (default: $LANGSMITH_PROJECT)")
    ap.add_argument("--graph-name", default="Universal Object Mapping Translator")
    ap.add_argument("--dataset", default="wwi")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--env", default="../.env")
    ap.add_argument("--root", default="../predictions", help="output root dir")
    ap.add_argument("--reference", action="store_true",
                    help="write the frozen baseline layout (<root>/<dataset>/<pair>/...) instead")
    ap.add_argument("--run-id", default=None,
                    help="pin a specific run (the manually-reviewed baseline); recommended with "
                         "--reference so the frozen ground truth is reproducible")
    ap.add_argument("--from-export", default=None,
                    help="glob of LangGraph run-*.json exports for OFFLINE extraction")
    ap.add_argument("--from-predictions", default=None,
                    help="OFFLINE reference bootstrap: build the frozen per-pair reference from an "
                         "existing predictions tree (implies --reference). No LangSmith needed.")
    ap.add_argument("--overwrite", action="store_true",
                    help="with --from-predictions, replace existing per-pair reference files")
    ap.add_argument("--pair", default=None, help="pair label for offline export mode")
    ap.add_argument("--lang", default=None, choices=["java", "c_sharp"], help="lang for offline mode")
    args = ap.parse_args()

    root_dir = Path(args.root)
    if args.from_predictions:
        args.reference = True
        n = from_predictions(args, root_dir)
    elif args.from_export:
        n = from_export(args, root_dir)
    else:
        try:
            from dotenv import load_dotenv
            load_dotenv(args.env)
        except Exception:
            pass
        args.project = args.project or os.environ.get("LANGSMITH_PROJECT")
        if not args.project:
            raise SystemExit("set --project or LANGSMITH_PROJECT (or use --from-export)")
        n = from_live(args, root_dir)

    print(f"\nwrote {n} {'reference' if args.reference else 'prediction'} set(s) under {root_dir}")


if __name__ == "__main__":
    main()
