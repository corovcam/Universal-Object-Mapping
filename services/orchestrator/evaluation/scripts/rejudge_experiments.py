#!/usr/bin/env python3
"""rejudge_experiments.py — re-run ONLY the LLM-as-a-judge evaluators on finished experiments.

The full pipeline (graph + Daytona sandboxes + live WWI stores) is expensive and slow; the four
graded judges (translation_equivalence, code_correctness, conciseness, faithfulness) need none of
it — just the source request and the translated harness, both of which every exported experiment
CSV already carries (columns ``inputs`` and ``outputs``). This script replays exactly the judge
step of run_langsmith_eval.py over those CSVs:

  * same prompts, same scaffold note, same judge fallback chain (--judge-model), same robust
    structured→plain-JSON→next-model call path (imported, not copied);
  * PLUS the 2026-07-10 reference-aware context: when a frozen execution-verified reference
    exists for the row's (pair, variant) (evaluation/reference/<dataset>/<variant>/<pair>/ —
    see freeze_reference.py), it is appended to the judge prompt as authoritative ground truth
    in the same harness form. Rows without a frozen reference grade reference-free, as before.

Results land in a NEW CSV next to the originals (old scores preserved side-by-side), and can
optionally be pushed back to LangSmith as feedback on the original runs under suffixed keys
(``--push``, keys like ``code_correctness_ref``) so the original verdicts are never overwritten.

⚠ The judges run on the shared e-INFRA endpoint. If a live experiment is running, keep
``--judge-concurrency`` low (default 2) or wait — judge traffic competes with the generator.

Usage:
    uv run python evaluation/scripts/rejudge_experiments.py \
        --csv 'evaluation/traces/10-7-2026/uom-*.csv' --env .env.dev
    # push feedback to the original LangSmith runs under *_ref keys:
    #   ... --push
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import glob
import json
import re
import sys
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

csv.field_size_limit(10**9)

JUDGE_KEYS = ["code_correctness", "conciseness", "faithfulness", "translation_equivalence"]

# session_name short pair tokens -> example-metadata slugs (load_reference_context input form)
_SHORT_SRC = {"dapper": "dotnet_dapper", "efcore": "dotnet_efcore", "nhib": "dotnet_nhibernate"}
_SHORT_DST = {"mongo": "java_spring_data_mongodb", "neo4j": "java_spring_data_neo4j"}
_SESSION_RE = re.compile(
    r"(?:^|-)(dapper|efcore|nhib)-(mongo|neo4j)-(small|full|xl|batch\d+|extended)(?:-|$)")
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def _pair_variant(row: dict) -> tuple[str | None, str | None]:
    """(metadata-form pair, variant) for a CSV row — from outputs.pair when present, else the
    session name (…-dapper-mongo-full-…)."""
    pair = None
    try:
        pair = (json.loads(row.get("outputs") or "{}") or {}).get("pair")
    except Exception:
        pass
    m = _SESSION_RE.search(row.get("session_name") or "")
    variant = m.group(3) if m else None
    if not pair and m:
        pair = f"{_SHORT_SRC[m.group(1)]}->{_SHORT_DST[m.group(2)]}"
    return pair, variant


def _loads(s: str | None) -> dict:
    if not s:
        return {}
    try:
        parsed = json.loads(s)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


async def main_async(args: argparse.Namespace) -> None:
    if args.env:
        from dotenv import load_dotenv
        load_dotenv(args.env, override=True)

    # Reuse the judge machinery verbatim — prompts, chain, robust call path, reference loader.
    import run_langsmith_eval as rle

    chain = await rle._build_judge_chain(args.judge_model)
    sem = asyncio.Semaphore(max(1, args.judge_concurrency))
    prompts = {
        "code_correctness": rle.CODE_CORRECTNESS_PROMPT,
        "conciseness": rle.CONCISENESS_PROMPT,
        "faithfulness": rle.FAITHFULNESS_PROMPT,
        "translation_equivalence": rle.TRANSLATION_EQUIVALENCE_PROMPT,
    }

    files = sorted({f for pat in args.csv for f in glob.glob(pat)})
    if not files:
        raise SystemExit(f"no CSVs match {args.csv}")
    print(f"re-judging {len(files)} CSV(s) with chain {args.judge_model} "
          f"(concurrency {args.judge_concurrency}, reference-aware where frozen refs exist)")

    ls_client = None
    if args.push:
        from langsmith import Client
        ls_client = Client()

    out_rows: list[dict] = []

    async def judge_row(src_file: str, row: dict) -> None:
        inputs, outputs = _loads(row.get("inputs")), _loads(row.get("outputs"))
        src_prompt = rle._source_prompt(inputs)
        tgt_text = rle._translation_text(outputs)
        if not src_prompt or not tgt_text:
            return
        pair, variant = _pair_variant(row)
        ref = rle.load_reference_context(pair, variant, dataset=args.dataset)
        rec: dict = {
            "source_csv": Path(src_file).name, "row_id": row.get("id"),
            "session_name": row.get("session_name"), "repetition": row.get("repetition"),
            "pair": pair, "variant": variant, "reference_used": bool(ref),
        }
        run_id = None
        m = _UUID_RE.search(row.get("run") or "")
        if m:
            run_id = m.group(0)
        rec["run_id"] = run_id
        for key in JUDGE_KEYS:
            full = prompts[key].format(inputs=src_prompt, outputs=tgt_text)
            if ref:
                full += rle._REFERENCE_BLOCK.format(reference=ref)
            verdict = await rle._judge_call(chain, full, key, args.timeout, sem)
            rec[f"{key}_old"] = row.get(key)
            rec[f"{key}{args.key_suffix}"] = verdict.get("score")
            rec[f"{key}{args.key_suffix}_comment"] = verdict.get("comment")
            if ls_client and run_id and verdict.get("score") is not None:
                try:
                    ls_client.create_feedback(run_id=run_id, key=f"{key}{args.key_suffix}",
                                              score=verdict["score"],
                                              comment=verdict.get("comment"))
                except Exception as e:  # noqa: BLE001 — pushing is best-effort
                    print(f"[warn] feedback push failed for {run_id}: {e}")
        out_rows.append(rec)
        done = len(out_rows)
        print(f"  [{done}] {rec['session_name']} rep={rec['repetition']} "
              f"ref={'Y' if ref else 'n'} " +
              " ".join(f"{k}={rec.get(f'{k}{args.key_suffix}')}" for k in JUDGE_KEYS))

    tasks = []
    for f in files:
        for row in csv.DictReader(open(f, encoding="utf-8")):
            if args.limit and len(tasks) >= args.limit:
                break
            tasks.append(judge_row(f, row))
    await asyncio.gather(*tasks)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"rejudge-{ts}.csv"
    if out_rows:
        fields = list(out_rows[0].keys())
        with out_path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(sorted(out_rows, key=lambda r: (str(r["session_name"]),
                                                        str(r["repetition"]))))
    print(f"\njudge model usage: {rle.JUDGE_MODEL_USAGE}")
    print(f"wrote {out_path} ({len(out_rows)} rows)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", nargs="+", required=True,
                    help="experiment CSV(s)/glob(s) exported from LangSmith "
                         "(need inputs/outputs/session_name columns)")
    ap.add_argument("--judge-model", default=None,
                    help="judge fallback chain (default: run_langsmith_eval's default)")
    ap.add_argument("--judge-concurrency", type=int, default=2,
                    help="global judge semaphore — keep LOW while a live experiment runs (default 2)")
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--dataset", default="wwi")
    ap.add_argument("--key-suffix", default="_ref",
                    help="suffix for the new scores/feedback keys so originals are never "
                         "overwritten (default _ref)")
    ap.add_argument("--push", action="store_true",
                    help="also push the new scores to LangSmith as feedback on the original runs")
    ap.add_argument("--limit", type=int, default=0, help="max rows (0 = all) — for smoke tests")
    ap.add_argument("--out", default="evaluation/out/rejudge")
    ap.add_argument("--env", default=".env.dev", help="dotenv with OPENAI_*/LANGSMITH_* keys")
    args = ap.parse_args()
    if args.judge_model is None:
        sys.path.insert(0, str(_HERE))
        import run_langsmith_eval as rle
        args.judge_model = rle.DEFAULT_JUDGE_MODEL
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
