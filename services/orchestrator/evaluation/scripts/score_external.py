#!/usr/bin/env python3
"""score_external.py — validate an EXTERNAL agent's translation with the pipeline's own gauntlet.

The "vs SOTA harness" comparison arm (Claude Code, Claude.ai, Gemini, ...): the external agent
receives the byte-identical translation prompt (`export_manual_prompts.py`), produces the schema +
per-query fragments in a CAPTURE file, and this script scores that capture with EXACTLY the same
machinery the pipeline applies to its own model — `assemble_query_harness` → compile+run BOTH
sandboxes → per-query execution equivalence — and emits the same metrics row (`passed`,
`compile_pass`, `queries_expected/claimed/accepted`, `query_accuracy`, verdicts). No LLM judge is
involved: deterministic execution equivalence IS acceptance here, which is the *stricter* standard
(the pipeline's own `passed` is also deterministic-only).

Capture format (what the exported prompt tells the model to emit — fenced blocks whose info string
names the piece; see `export_manual_prompts.py`):

    ```source_schema_body
    ...C# entity classes...
    ```
    ```target_schema_body
    ...Java mapping classes...
    ```
    ```source_query_body id=1
    public static class Query1 { ... }
    ```
    ```target_query_body id=1
    final class Query1 { ... }
    ```
    ... one source/target pair per query id ...

Needs the LIVE stack (Daytona sandboxes + WWI DBs) and the ORCHESTRATOR venv (imports react_agent):

  uv run python evaluation/scripts/score_external.py \\
      --capture evaluation/manual-eval/wwi/dapper-mongodb__full__<ts>/capture.md \\
      --pair dapper-mongodb --variant full --approach claude_code --model-label claude-opus-4.8

Outputs, per run:
  * <out>/<approach>/<pair>__<variant>__<ts>/result.json   — the full metrics row + verdicts
  * <out>/<approach>/results.csv                            — one appended row per scored capture
  * <pred-root>/wwi/external-<approach>/<pair_slug>/<model-label>/<runid>/  — predictions tree
    (schema.<ext> + queries.<ext>, CodeBLEU-comparable with the pipeline's predictions)
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import re
import sys
import time
import uuid
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parents[1] / "src"))  # services/orchestrator/src

from build_eval_dataset import SOURCES, TARGETS, VARIANT_SLICES  # noqa: E402
from extract_predictions import _write_artifacts, pair_slug, target_lang  # noqa: E402

# ---------------------------------------------------------------------------- capture parsing

# ``` <kind> [id=N]   ...body...   ```   — the info string names the piece.
_BLOCK_RE = re.compile(
    r"```(source_schema_body|target_schema_body|source_query_body|target_query_body)"
    r"(?:\s+id=(\d+))?\s*\n(.*?)```",
    re.S,
)


def parse_capture(text: str) -> tuple[dict[str, str], dict[str, dict[str, str]], list[str]]:
    """Extract schema bodies + per-query fragments from a capture file.

    Returns (schema_bodies{source,target}, fragments{qid: {source,target}}, problems).
    Later duplicate blocks overwrite earlier ones (models sometimes revise in the same reply —
    take their final answer, like the pipeline's re-save semantics).
    """
    schema: dict[str, str] = {}
    fragments: dict[str, dict[str, str]] = {}
    problems: list[str] = []
    for kind, qid, body in _BLOCK_RE.findall(text):
        body = body.strip()
        if not body:
            problems.append(f"empty block: {kind}{f' id={qid}' if qid else ''}")
            continue
        if kind.endswith("schema_body"):
            schema[kind.split("_", 1)[0]] = body
        else:
            if not qid:
                problems.append(f"{kind} without id= — skipped")
                continue
            fragments.setdefault(qid, {})[kind.split("_", 1)[0]] = body
    return schema, fragments, problems


# ---------------------------------------------------------------------------- scoring


async def score(args: argparse.Namespace) -> dict:
    from react_agent.constants import (
        DotnetFramework,
        FrameworkEnum,
        JavaFramework,
        TranslationType,
    )
    from react_agent.context import Context
    from react_agent.custom_tools.dotnet_validator import compile_and_run_dotnet
    from react_agent.custom_tools.draft_validator import build_sandbox_runtime
    from react_agent.custom_tools.java_validator import compile_and_run_java
    from react_agent.custom_tools.query_validator import compute_equivalence_results
    from react_agent.state import State
    from react_agent.utils.harness_assembler import assemble_query_harness

    src_key, tgt_key = args.pair.split("-", 1)
    # dataset slugs (dotnet_dapper, java_spring_data_neo4j) are the FrameworkEnum member NAMES
    source_fw = FrameworkEnum[SOURCES[src_key]["slug"].upper()]
    target_fw = FrameworkEnum[TARGETS[tgt_key]["slug"].upper()]
    dotnet_fw = DotnetFramework(source_fw.value)
    java_fw = JavaFramework(target_fw.value)
    start, end = VARIANT_SLICES[args.variant]
    expected_ids = list(range(start + 1, end + 1))

    capture_text = Path(args.capture).read_text(encoding="utf-8")
    schema, fragments, problems = parse_capture(capture_text)
    for p in problems:
        print(f"  capture warning: {p}", file=sys.stderr)

    if not schema.get("source") or not schema.get("target"):
        raise SystemExit(
            "capture is missing the source_schema_body / target_schema_body blocks — nothing to score"
        )

    complete_ids = sorted(
        int(k) for k, sides in fragments.items()
        if sides.get("source") and sides.get("target") and int(k) in set(expected_ids)
    )
    if not complete_ids:
        raise SystemExit("capture has no complete (source+target) query fragment for the expected ids")
    missing_ids = [q for q in expected_ids if q not in complete_ids]
    if missing_ids:
        print(f"  capture is missing query ids {missing_ids} — they score as failed", file=sys.stderr)

    # Minimal real State + Context: the compile helpers read runtime.state.translation_type and
    # runtime.context.<connection strings / Daytona>; Context self-populates from the env.
    state = State(
        messages=[],
        translation_type=TranslationType.BOTH,
        source_target=source_fw,
        destination_target=target_fw,
    )
    run_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": run_id}, "run_id": run_id}
    runtime = build_sandbox_runtime(state, Context(), config)

    source_code, _src_entry = await assemble_query_harness(
        source_fw, schema["source"], {q: fragments[str(q)]["source"] for q in complete_ids}
    )
    target_code, tgt_entry = await assemble_query_harness(
        target_fw, schema["target"], {q: fragments[str(q)]["target"] for q in complete_ids}
    )

    t0 = time.perf_counter()
    src_out, tgt_out = await asyncio.gather(
        compile_and_run_dotnet(source_code, dotnet_fw, runtime),
        compile_and_run_java(target_code, java_fw, tgt_entry, runtime),
        return_exceptions=True,
    )
    wall = round(time.perf_counter() - t0, 1)

    import orjson

    sides: dict[str, dict | None] = {}
    logs: dict[str, str] = {}
    for label, res in (("source", src_out), ("target", tgt_out)):
        if isinstance(res, BaseException):
            logs[label] = f"sandbox execution error: {res}"
            sides[label] = None
            continue
        output, json_part = res
        logs[label] = str(output)
        if "Validation Failed" in str(output) or json_part is None:
            sides[label] = None
            continue
        try:
            sides[label] = orjson.loads(json_part)
        except orjson.JSONDecodeError:
            sides[label] = None

    diffs: dict[str, dict] = {}
    if sides["source"] is not None and sides["target"] is not None:
        diffs = await compute_equivalence_results(
            sides["source"], sides["target"],
            mapping_labels=(source_fw.value, target_fw.value),
        )

    # ---- Metrics: SAME definitions as run_experiment.run_one. compile_pass mirrors "both query
    # validation results present"; accepted = deterministic Equivalent (no judge in this arm).
    equivalent_ids = sorted(
        int(q.removeprefix("query")) for q, v in diffs.items()
        if isinstance(v, dict) and v.get("status") == "Equivalent"
    )
    compile_pass = sides["source"] is not None and sides["target"] is not None
    queries_expected = len(expected_ids)
    queries_accepted = len(equivalent_ids)
    passed = bool(compile_pass and queries_expected > 0 and queries_accepted >= queries_expected)

    row = {
        "approach": args.approach,
        "model": args.model_label,
        "pair": f"{source_fw.value} -> {target_fw.value}",
        "pair_slug": pair_slug(source_fw.value, target_fw.value),
        "variant": args.variant,
        "capture": str(args.capture),
        "run_id": run_id,
        "wall_clock_validation_s": wall,
        "passed": passed,
        "compile_pass": compile_pass,
        "queries_expected": queries_expected,
        "queries_claimed": len(complete_ids),
        "queries_accepted": queries_accepted,
        "queries_equivalent": queries_accepted,
        "query_accuracy": round(queries_accepted / queries_expected, 4) if queries_expected else None,
        "query_precision": round(queries_accepted / len(complete_ids), 4) if complete_ids else None,
        "query_recall": round(queries_accepted / queries_expected, 4) if queries_expected else None,
        "missing_query_ids": missing_ids or None,
        "equivalent_query_ids": equivalent_ids,
        "query_verdicts": {q: (v.get("status") if isinstance(v, dict) else str(v)) for q, v in diffs.items()},
        "error": None if compile_pass else "compile/run failed (see logs)",
    }

    # ---- Persist: per-run dir + one aggregate CSV per approach + predictions tree.
    ts = time.strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out) / args.approach / f"{args.pair}__{args.variant}__{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "result.json").write_text(json.dumps(row, indent=2), encoding="utf-8")
    (out_dir / "assembled_source" ).with_suffix(".txt").write_text(source_code, encoding="utf-8")
    (out_dir / "assembled_target").with_suffix(".txt").write_text(target_code, encoding="utf-8")
    for label, log in logs.items():
        (out_dir / f"sandbox_{label}.log").write_text(log, encoding="utf-8")

    csv_path = Path(args.out) / args.approach / "results.csv"
    csv_cols = [k for k in row if k not in ("query_verdicts", "equivalent_query_ids")]
    new_file = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=csv_cols, extrasaction="ignore")
        if new_file:
            w.writeheader()
        w.writerow(row)

    _lang, ext = target_lang(target_fw.value)
    pred_base = (
        Path(args.pred_root) / "wwi" / f"external-{args.approach}"
        / row["pair_slug"] / args.model_label / run_id[:8]
    )
    queries_clean = "\n\n".join(fragments[str(q)]["target"] for q in complete_ids)
    _write_artifacts(pred_base, schema.get("target"), queries_clean, ext)

    print(f"\n=== {args.approach} ({args.model_label}) — {args.pair} [{args.variant}] ===")
    print(f"  passed={passed} compile={compile_pass} "
          f"accuracy={row['query_accuracy']} ({queries_accepted}/{queries_expected})"
          f"{f' missing={missing_ids}' if missing_ids else ''}")
    if diffs:
        for q in sorted(diffs, key=lambda s: int(s.removeprefix('query'))):
            v = diffs[q]
            print(f"    {q}: {(v.get('status') if isinstance(v, dict) else v)}")
    print(f"  result: {out_dir}/result.json  (+ sandbox logs, assembled harnesses)")
    print(f"  csv:    {csv_path}")
    return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--capture", required=True, help="capture file with the fenced fragment blocks")
    ap.add_argument("--pair", required=True,
                    choices=[f"{s}-{t}" for s in SOURCES for t in TARGETS],
                    help="source-target short pair, e.g. dapper-mongodb")
    ap.add_argument("--variant", default="full", choices=sorted(VARIANT_SLICES),
                    help="which query slice the capture answers (default: full = Query1-15)")
    ap.add_argument("--approach", default="claude_code",
                    help="label for the external harness (claude_code, claude_ai, gemini, ...)")
    ap.add_argument("--model-label", default="unknown",
                    help="model that produced the capture (for the predictions tree + CSV)")
    ap.add_argument("--out", default="evaluation/out/external")
    ap.add_argument("--pred-root", default="evaluation/predictions")
    ap.add_argument("--env", default=".env")
    args = ap.parse_args()

    try:
        from dotenv import load_dotenv
        # override=True: an explicit --env must WIN over inherited shell exports — a profile-level
        # MONGODB_URI pointing at the docker-compose-internal hostname silently redirected the
        # whole target-side validation to an unreachable host (every query "Execution Error").
        load_dotenv(args.env, override=True)
    except Exception:
        pass

    asyncio.run(score(args))


if __name__ == "__main__":
    main()
