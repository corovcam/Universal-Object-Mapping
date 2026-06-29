#!/usr/bin/env python3
"""run_experiment.py — drive the pipeline for our-approach vs the single-pass baseline (E7 / 2a).

Runs the SAME graph on the same WWI fixture twice:
  * our_approach : the full agentic loop (research tools + bounded self-repair).
  * baseline     : `single_pass=True` — one direct model call (system + human prompt, save tool
                   only, no docs MCP, no retry loop, no human hand-off), then the SAME
                   deterministic assemble → validate → finalize.

The only difference is the agentic loop, so the comparison isolates its value. Both arms emit the
same finalize artifacts (clean translated code) and per-query execution-equivalence, so they are
scored identically downstream (extract_predictions.py / score_predictions.py / aggregate_traces.py).

This needs the LIVE stack (e-INFRA model endpoint, Daytona sandboxes, WWI DBs) and the orchestrator
venv (it imports react_agent), NOT the eval venv:

  .venv/bin/python evaluation/scripts/run_experiment.py --fixture efcore-mongodb-q1 \
      --approaches baseline our_approach --pred-root evaluation/predictions --out evaluation/out

Token/funnel/per-node cost come from aggregate_traces.py over the LangSmith traces these runs emit
(joined by the `experiment`/`approach` metadata stamped here); this runner records what is only
knowable at run time: wall-clock latency, loop count, acceptance, compile pass, and pass@1.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path

# orchestrator src on path + reuse the predictions layout helpers
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parents[1] / "src"))  # services/orchestrator/src
from aimock_recorder import DEFAULT_UPSTREAM, record_fixtures  # noqa: E402
from extract_predictions import pair_slug, slug, target_lang, _write_artifacts  # noqa: E402

# Fixture name -> path under tests/fixtures. All WideWorldImporters.
FIXTURE_DIR = _HERE.parents[1] / "tests" / "fixtures"
FIXTURES = {
    "dapper-mongodb": "input-dapper-mongodb.txt",
    "efcore-mongodb": "input-efcore-mongodb.txt",
    "efcore-mongodb-q1": "input-efcore-mongodb-q1.txt",
    "efcore-neo4j": "input-efcore-neo4j.txt",
    "nhibernate-mongodb": "input-nhibernate-mongodb.txt",
}

_EQUIV_BLOCK_RE = re.compile(r"\[Query Equivalence Results\]\s*```json\s*(\{.*?\})\s*```", re.S)


def _load_fixture(name_or_path: str) -> str:
    p = Path(name_or_path)
    if p.exists():
        return p.read_text(encoding="utf-8")
    fname = FIXTURES.get(name_or_path)
    if not fname:
        raise SystemExit(f"unknown fixture '{name_or_path}'; choices: {', '.join(FIXTURES)} or a path")
    return (FIXTURE_DIR / fname).read_text(encoding="utf-8")


def _scrape_equivalence(messages: list) -> dict[str, bool]:
    """Per-query equivalence from the [Query Equivalence Results] message (last one wins) — the same
    authoritative signal aggregate_traces.py reads from the trace, here read from final state."""
    out: dict[str, bool] = {}
    for m in messages:
        content = getattr(m, "content", "") or ""
        if not isinstance(content, str):
            continue
        match = _EQUIV_BLOCK_RE.search(content)
        if not match:
            continue
        try:
            payload = json.loads(match.group(1))
        except Exception:
            continue
        for q, v in payload.items():
            status = (v or {}).get("status", "") if isinstance(v, dict) else str(v)
            out[q] = status.strip().lower() == "equivalent"
    return out


async def run_one(
    fixture_text: str,
    single_pass: bool,
    model,
    approach: str,
    fixture: str,
    record_dir: Path | None = None,
    upstream: str = DEFAULT_UPSTREAM,
    *,
    eval_mode: bool = False,
    translation_model_override: str | None = None,
    translation_reasoning_override: bool | None = None,
) -> dict:
    from langchain_core.messages import HumanMessage
    from langgraph.checkpoint.memory import MemorySaver

    from react_agent.context import Context
    from react_agent.graph import graph

    # output_schema=OutputState, so ainvoke's return is narrowed; a checkpointer lets us read the
    # FULL final State (validation results, equivalence diffs, loop count) via aget_state.
    g = graph.builder.compile(checkpointer=MemorySaver(), name="UOM Experiment Runner")
    run_id = str(uuid.uuid4())
    config = {
        "configurable": {"thread_id": run_id},
        "recursion_limit": 80,
        "run_id": run_id,
        "metadata": {"experiment": fixture, "approach": approach, "single_pass": single_pass},
    }

    # When recording, spawn a throwaway aimock for THIS run and point the orchestrator's model base
    # URL at it (get_model reads Context.openai_api_url). The real OPENAI_API_KEY is kept — aimock
    # forwards it upstream and strips it from the saved fixtures. ExitStack keeps the non-recording
    # path allocation-free while still tearing the instance down even if ainvoke throws.
    import contextlib as _contextlib

    async def _invoke(base_url: str | None) -> None:
        ctx_kwargs: dict = {}
        if model:
            ctx_kwargs["model"] = model
        if base_url:
            ctx_kwargs["openai_api_url"] = base_url
        # Evaluation-only knobs (production-safe defaults: off). eval_mode turns on the per-run
        # cache-bust header; translation_model_override drives the generate_translation_node model
        # sweep. These are set per-invoke on Context (never a global) so concurrent eval runs can't
        # race. See react_agent.context.Context.
        if eval_mode:
            ctx_kwargs["eval_mode"] = True
        if translation_model_override:
            ctx_kwargs["translation_model_override"] = translation_model_override
        if translation_reasoning_override is not None:
            ctx_kwargs["translation_reasoning_override"] = translation_reasoning_override
        ctx = Context(**ctx_kwargs)
        await g.ainvoke(
            {"messages": [HumanMessage(content=fixture_text)], "single_pass": single_pass},
            config=config, context=ctx,
        )

    t0 = time.perf_counter()
    error = None
    try:
        with _contextlib.ExitStack() as stack:
            base_url = (
                stack.enter_context(record_fixtures(record_dir, upstream=upstream))
                if record_dir is not None
                else None
            )
            await _invoke(base_url)
    except Exception as e:  # record the failure rather than aborting the whole experiment
        error = f"{type(e).__name__}: {e}"
    wall = round(time.perf_counter() - t0, 1)

    snap = await g.aget_state(config)
    st = snap.values

    src = st.get("source_target")
    dst = st.get("destination_target")
    src_s = src.value if hasattr(src, "value") else (src or None)
    dst_s = dst.value if hasattr(dst, "value") else (dst or None)
    schema_code = st.get("translated_schema_code")
    query_code = st.get("translated_query_code")
    per_query = _scrape_equivalence(list(st.get("translation_messages", [])) + list(st.get("messages", [])))
    lang, ext = target_lang(dst_s)

    return {
        "approach": approach,
        "single_pass": single_pass,
        "fixture": fixture,
        "run_id": run_id,
        "pair": f"{src_s} -> {dst_s}" if src_s and dst_s else "unknown",
        "pair_slug": pair_slug(src_s, dst_s),
        "model": str(model) if model else os.environ.get("MODEL", "default"),
        "lang": lang,
        "ext": ext,
        "wall_clock_s": wall,
        "translation_loops": int(st.get("translation_loop_count", 0) or 0),
        "accepted": bool(schema_code or query_code),
        "compile_pass": st.get("source_query_validation_results") is not None
        and st.get("target_query_validation_results") is not None,
        "queries_total": len(per_query),
        "queries_equivalent": sum(1 for v in per_query.values() if v),
        "pass_at_1": round(sum(per_query.values()) / len(per_query), 4) if per_query else None,
        "error": error,
        "_schema_code": schema_code,
        "_query_code": query_code,
    }


async def main_async(args: argparse.Namespace) -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(args.env)
    except Exception:
        pass

    model = None
    if args.model:
        from react_agent.constants import AvailableModel
        model = AvailableModel(args.model)

    fixture_text = _load_fixture(args.fixture)
    pred_root = Path(args.pred_root)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    aimock_root = Path(args.aimock_root) if args.record_fixtures else None

    results = []
    for approach in args.approaches:
        single_pass = approach == "baseline"
        print(f"\n=== running {approach} (single_pass={single_pass}) on {args.fixture} ===")
        record_dir = None
        if aimock_root is not None:
            # Per-run folder, named from what we know BEFORE invoking (no pair yet): the run is
            # uniquely identified by fixture + approach + a human-readable timestamp. aimock writes
            # the captures under <record_dir>/recorded/.
            ts = time.strftime("%Y%m%d-%H%M%S")
            record_dir = aimock_root / args.dataset / f"{args.fixture}__{approach}__{ts}"
            print(f"  recording LLM traffic → {record_dir}/recorded/ (spawning aimock)")
        r = await run_one(
            fixture_text, single_pass, model, approach, args.fixture,
            record_dir=record_dir, upstream=args.aimock_upstream,
        )
        if record_dir is not None:
            r["aimock_dir"] = str(record_dir)
        # write finalize artifacts to the predictions tree (only when accepted)
        if r["accepted"]:
            base = pred_root / args.dataset / r["pair_slug"] / slug(r["model"]) / f"{approach}-{r['run_id'][:8]}"
            w = _write_artifacts(base, r.pop("_schema_code"), r.pop("_query_code"), r["ext"])
            r["predictions"] = w
        else:
            r.pop("_schema_code", None)
            r.pop("_query_code", None)
            r["predictions"] = []
        results.append(r)
        print(f"  accepted={r['accepted']} loops={r['translation_loops']} "
              f"pass@1={r['pass_at_1']} wall={r['wall_clock_s']}s err={r['error']}")

    (out_dir / f"experiment-{args.fixture}.json").write_text(json.dumps(results, indent=2))

    print(f"\n{'approach':<14}{'accepted':>9}{'loops':>7}{'pass@1':>8}{'compile':>9}{'wall_s':>9}")
    for r in results:
        print(f"{r['approach']:<14}{str(r['accepted']):>9}{r['translation_loops']:>7}"
              f"{str(r['pass_at_1']):>8}{str(r['compile_pass']):>9}{r['wall_clock_s']:>9}")
    print(f"\nwrote experiment-{args.fixture}.json to {out_dir}; predictions under {pred_root}")
    print("→ token/funnel/per-node cost: run aggregate_traces.py over the LangSmith traces "
          "(filter on metadata.approach).")
    if "baseline" in args.approaches:
        bl = next((r for r in results if r["approach"] == "baseline"), None)
        print("\n[verify the baseline ACTUALLY ran single-pass] In its LangSmith trace (run_id "
              f"{bl['run_id'] if bl else '?'}) confirm EXACTLY ONE generate_translation_node span "
              "and ZERO docs-MCP tool calls. translation_loops==1 alone is NOT sufficient — a "
              "full-loop run that succeeds first try is also 1.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fixture", default="efcore-mongodb-q1",
                    help=f"fixture name ({', '.join(FIXTURES)}) or a path")
    ap.add_argument("--approaches", nargs="+", default=["baseline", "our_approach"],
                    choices=["baseline", "our_approach"])
    ap.add_argument("--model", default=None, help="AvailableModel value (default: env MODEL / Context default)")
    ap.add_argument("--dataset", default="wwi")
    ap.add_argument("--pred-root", default="../predictions")
    ap.add_argument("--out", default="./out")
    ap.add_argument("--env", default="../.env")
    ap.add_argument("--record-fixtures", action="store_true",
                    help="spawn a throwaway aimock per run that RECORDS LLM traffic to disk "
                         "(needs the live upstream + the real OPENAI_API_KEY)")
    ap.add_argument("--aimock-root", default="../aimock",
                    help="base dir for recorded fixtures (per-run subfolder created underneath)")
    ap.add_argument("--aimock-upstream", default=DEFAULT_UPSTREAM,
                    help="real OpenAI-compatible provider aimock proxies to (no trailing /v1)")
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
