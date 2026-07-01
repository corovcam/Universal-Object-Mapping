#!/usr/bin/env python3
"""run_langsmith_eval.py — LangSmith-native experiment: run the graph over a dataset + LLM judges.

Unlike ``run_experiment.py`` (which drives the graph directly and writes its own JSON metrics), this
script uses LangSmith's ``aevaluate`` so the results land as a proper **Experiment** attached to a
dataset, with per-example LLM-as-judge feedback scores visible in the LangSmith UI.

  * Dataset: defaults to "UOM Final Experiments" (ID below). Each example's input is
    ``{"messages": [{"role": "user", "content": "Translate ... <schema+query>"}]}`` — the same shape
    the graph consumes. There is NO gold reference output (the dataset's ``outputs.message`` is a
    dev-time artifact and is ignored).
  * Target: compiles and invokes the graph on each example (our_approach or the single_pass
    baseline) and returns the translated code + acceptance/equivalence signals.
  * Judges (LLM-as-judge, all REFERENCE-FREE, graded against the SOURCE in the input):
      - code_correctness  : openevals CODE_CORRECTNESS_PROMPT (is the translated code correct?)
      - conciseness       : openevals CONCISENESS_PROMPT
      - hallucination     : openevals HALLUCINATION_PROMPT, grounded with the source as ``context``
                            (did it invent entities/fields not present in the source?)
      - translation_equivalence : a custom prompt — does the target faithfully preserve the source
                            schema/query semantics, translating ONLY what appears in the source?
    We deliberately do NOT use a "first-accepted-as-reference" judge here: that idea is only coherent
    across runs of the SAME input, whereas these examples are DIFFERENT queries (one query's
    translation is no reference for another's). For reference-based CodeBLEU scoring keep using the
    frozen pair-level reference from ``extract_predictions.py --reference`` / ``score_predictions.py``.

Judge model: the user has NO proprietary API keys, so the judge runs on the same e-INFRA
OpenAI-compatible endpoint as the pipeline (``OPENAI_API_URL`` / ``OPENAI_API_KEY`` from .env),
with ``reasoning=False`` (reasoning tokens pollute structured judge output and can 400 sglang).

Needs the LIVE stack (e-INFRA model endpoint, Daytona sandboxes, WWI DBs) and the orchestrator venv
(it imports react_agent), plus the ``eval`` extra for openevals:

    uv sync --extra eval
    uv run python evaluation/scripts/run_langsmith_eval.py --approach our_approach \
        --judge-model einfra/gemma4 --env .env

Use ``--dry-run`` to validate dataset/judge plumbing with a trivial echo target (no graph, no
Daytona) before spending tokens on a real run.

Judge implementation notes (all learned empirically against e-INFRA, then designed around):
  * openevals' OWN scorer (``create_async_llm_as_judge``) drives the judge through a structured-output
    method that HANGS on the e-INFRA models — so we keep openevals' *prompts* but make the call
    ourselves (see ``_judge_call``): ``with_structured_output`` first, then a plain-invoke + lenient
    JSON-parse fallback, with a per-judge timeout and graceful ``None`` on failure (one flaky judge
    never stalls the experiment).
  * Thinking models (gpt-oss-120b, mini, qwen-coder) reason heavily on the long grading prompts and
    hang structured output; the non-thinking ``llama-4-scout`` is fast (<1s) — hence the default.
  * The judge schema declares ``score`` BEFORE ``reasoning``: these models write a long reasoning
    that can truncate before a trailing field, so score-first preserves the verdict.
CALL PATH verified end-to-end via ``--dry-run`` against the live dataset: ~17/20 judge calls return a
parsed verdict (the rest degrade to ``None``). NOTE this graded the dry-run *stub*, so it proves the
plumbing + parse path only — judge **discrimination on real (long) translations is UNVERIFIED**. The
graph target needs the full live stack (Daytona + WWI DBs); on the first real run, spot-check a couple
of judge comments to confirm they actually distinguish good vs bad translations, and tune
``--judge-model`` if a judge underperforms.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# orchestrator src on path
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parents[1] / "src"))  # services/orchestrator/src

from aimock_recorder import (
    DEFAULT_UPSTREAM,  # noqa: E402 — sibling script (LLM-traffic recorder)
)

DATASET_ID = "56708f08-2697-4af2-b3b7-9172c0e68b4b"  # "UOM Final Experiments"
DATASET_NAME = "UOM Final Experiments"
# Judge model is finicky on e-INFRA (verified empirically): thinking models (deepseek-v4-pro-thinking,
# gpt-oss-120b, mini, qwen-coder) reason heavily on the long grading prompts and HANG
# `with_structured_output`; the e-INFRA "llama-4-scout" alias is actually `redhatai-scout` capped at
# `max_tokens: 50`, which TRUNCATES every verdict. `gemma4` (google/gemma-4-31B-it) is non-thinking,
# multimodal, fast, and has a full 32k output budget — hence the default. The judge call is still made
# robust (structured → JSON-fallback → graceful None, per-judge timeout) and the model is a CLI knob,
# so it can be A/B'd against a non-thinking fallback (e.g. einfra/mistral-medium-3.5) on the live stack.
DEFAULT_JUDGE_MODEL = "einfra/kimi-k2.7"  # einfra/gemma4 is also good, but deepseek-v4-pro-thinking has more recent knowledge (April 2026)


# --------------------------------------------------------------------------- inputs/outputs helpers
def _source_prompt(inputs: dict[str, Any]) -> str:
    """Extract the user 'Translate ...' text from a dataset example's inputs.

    The example input is ``{"messages": [{"role": "user", "content": "..."}]}``; ``messages`` may be
    a list (canonical) or a JSON string (depending on how it was uploaded). Returns the concatenated
    user-message content.
    """
    msgs = inputs.get("messages")
    if isinstance(msgs, str):
        try:
            msgs = json.loads(msgs)
        except Exception:
            return msgs
    if isinstance(msgs, list):
        parts = [
            str(m.get("content", ""))
            for m in msgs
            if isinstance(m, dict) and m.get("role") in (None, "user", "human")
        ]
        return "\n".join(p for p in parts if p)
    return str(msgs or "")


def _translation_text(outputs: dict[str, Any]) -> str:
    """The target's translated code, combined into one string for the judges to grade."""
    blocks = []
    if outputs.get("translated_schema_code"):
        blocks.append("// --- translated schema ---\n" + outputs["translated_schema_code"])
    if outputs.get("translated_query_code"):
        blocks.append("// --- translated query ---\n" + outputs["translated_query_code"])
    if not blocks and outputs.get("explanation_message"):
        # Nothing accepted; let the judges grade whatever the agent produced/explained.
        return str(outputs["explanation_message"])
    return "\n\n".join(blocks)


# --------------------------------------------------------------- generate-model sweep (opt-in)
# The 4-model sweep the user called exploratory (qwen3.5 / kimi-k2.7 / glm-5.2 non-reasoning /
# deepseek-v4-pro-thinking). Each tuple is (generate_translation_node model override, reasoning
# override). qwen3.5 with reasoning=None reproduces the PRODUCTION default (so the default arm is in
# the sweep). NOTE: glm-5.2's model_profiles extra_body forces thinking on, so its "non-reasoning"
# (False) may not take effect — flagged, not worked around (this is opt-in/exploratory).
SWEEP_MODELS: list[tuple[str | None, bool | None]] = [
    ("einfra/glm-5.2", None),
    ("einfra/kimi-k2.7", None),
    ("einfra/deepseek-v4-pro-thinking", None),
]


# ------------------------------------------------------------------------------------------- target
async def _make_target(
    approach: str,
    *,
    pred_root: str,
    dataset: str,
    run_tag: str,
    pair: str | None = None,
    variant: str | None = None,
    translation_model_override: str | None = None,
    translation_reasoning_override: bool | None = None,
    record_fixtures: bool = False,
    aimock_root: str | None = None,
    aimock_upstream: str = DEFAULT_UPSTREAM,
):
    """Build an async ``aevaluate`` target that runs the graph ONCE per example and returns BOTH the
    translated code (for the LLM judges) AND the deterministic metrics (for the non-LLM evaluators),
    writing prediction artifacts for the post-hoc CodeBLEU pass. Reuses ``run_experiment.run_one`` so
    the invoke / equivalence-scrape / metrics logic is shared (no second graph execution anywhere).

    Fault tolerance: this target NEVER raises. ``run_one`` already catches graph-execution exceptions
    (network blips, Daytona/DB errors, model errors — the model calls also retry internally via
    litellm + ModelFallbackMiddleware) and returns them as ``error`` rather than propagating, so one
    bad example can't abort the experiment. We additionally wrap the artifact-write / dict-build here:
    on ANY unexpected failure the target returns a minimal error dict, so ``aevaluate`` records the
    example and moves on. With ``num_repetitions`` (e.g. 15), a transient per-rep failure costs one
    rep, not the run.

    No-overwrite: predictions are written under a per-INVOCATION ``run_tag`` (timestamp) AND a fresh
    per-run uuid leaf, so re-running never clobbers a previous batch's artifacts.

    Fixture recording (opt-in, ``record_fixtures``): when on, EACH run gets its OWN throwaway aimock
    instance (auto-picked free port, concurrency-safe) that proxies to ``aimock_upstream`` and SAVES
    the run's LLM traffic into its own directory under
    ``<aimock_root>/<dataset>/<run_tag>/<pair>/<gen_model>/<approach>-<uuid8>/recorded/`` — mirroring
    the predictions layout so a run's fixtures and predictions sit in parallel trees and never mingle
    with another run's. eval_mode's per-run cache-bust header keeps every prompt distinct, so aimock's
    in-memory replay cache never short-circuits a recording."""
    import uuid as _uuid

    from extract_predictions import _write_artifacts, slug
    from run_experiment import run_one

    single_pass = approach == "baseline"
    gen_model_tag = translation_model_override or "default"
    pair_tag = _pair_short(pair) if pair else "unknown"

    async def target(inputs: dict[str, Any]) -> dict[str, Any]:
        try:
            prompt = _source_prompt(inputs)
            # Per-run aimock recording dir (known BEFORE invoke; run_one's own run_id isn't available
            # yet, so the leaf carries a fresh uuid). aimock writes under <record_dir>/recorded/.
            record_dir = None
            if record_fixtures and aimock_root:
                leaf = f"{approach}-{variant or 'na'}-{_uuid.uuid4().hex[:8]}"
                record_dir = (
                    Path(aimock_root) / dataset / run_tag / pair_tag / slug(gen_model_tag) / leaf
                )
            # eval_mode=True turns on the per-run cache-bust header; the sweep model (if any) is forced
            # on generate_translation_node via Context. run_one returns the full metric bundle + raw
            # code and never raises (it catches graph exceptions internally). record_dir!=None spawns a
            # recording aimock for THIS run and points the model base URL at it.
            r = await run_one(
                prompt, single_pass, None, approach, "langsmith",
                record_dir=record_dir, upstream=aimock_upstream,
                eval_mode=True,
                translation_model_override=translation_model_override,
                translation_reasoning_override=translation_reasoning_override,
            )
            predictions: list = []
            if r.get("accepted"):
                try:
                    base = (
                        Path(pred_root) / dataset / run_tag / r["pair_slug"] / slug(gen_model_tag)
                        / f"{approach}-{r['run_id'][:8]}"
                    )
                    predictions = _write_artifacts(
                        base, r.get("_schema_code"), r.get("_query_code"), r["ext"]
                    )
                except Exception as we:  # noqa: BLE001 — a disk hiccup must not lose the metrics
                    predictions = [f"artifact-write-failed: {type(we).__name__}: {we}"]
            return {
                "translated_schema_code": r.get("_schema_code"),
                "translated_query_code": r.get("_query_code"),
                "explanation_message": None,
                "accepted": bool(r.get("accepted")),
                "compile_pass": bool(r.get("compile_pass")),
                "pass_at_1": r.get("pass_at_1"),
                "translation_loops": r.get("translation_loops"),
                "wall_clock_s": r.get("wall_clock_s"),
                "queries_total": r.get("queries_total"),
                "queries_equivalent": r.get("queries_equivalent"),
                "pair": r.get("pair"),
                "generate_model": gen_model_tag,
                "predictions": predictions,
                "aimock_dir": str(record_dir) if record_dir is not None else None,
                "error": r.get("error"),
            }
        except Exception as e:  # noqa: BLE001 — last-resort guard so aevaluate always continues
            return {"accepted": False, "compile_pass": False, "pass_at_1": None,
                    "generate_model": gen_model_tag,
                    "error": f"target-fatal: {type(e).__name__}: {e}"}

    return target


async def _echo_target(inputs: dict[str, Any]) -> dict[str, Any]:
    """Trivial target for --dry-run: echoes the source so judge/plumbing wiring can be validated."""
    prompt = _source_prompt(inputs)
    return {
        "translated_schema_code": "// echo (dry-run): " + prompt[:200],
        "translated_query_code": None,
        "explanation_message": "dry-run echo target",
        "accepted": True,
        "pair": "dry-run",
    }


# ------------------------------------------------------------------------------------------- judges
async def _build_judge_model(model_name: str):
    """An e-INFRA chat model for judging — reasoning OFF (clean structured output, no sglang 400)."""
    from react_agent.utils.utils import load_chat_model

    url = os.environ.get("OPENAI_API_URL", "https://llm.ai.e-infra.cz/v1")
    key = os.environ.get("OPENAI_API_KEY", "")
    provider, _, model = model_name.partition("/")
    if provider != "einfra":
        raise SystemExit(f"--judge-model must be an einfra/* model; got {model_name!r}")
    return await load_chat_model(
        model_name,
        {"openai_api_url": url, "openai_api_key": key, "temperature": 0},
    )


# A custom equivalence judge prompt (reference-free, graded against the source). Mirrors the
# pipeline's own "Translate ONLY what appears in the source" contract.
TRANSLATION_EQUIVALENCE_PROMPT = """You are an expert grader of database object-mapping/ORM code \
translations. You are given the SOURCE translation request (containing the source ORM schema and/or \
query) and the model's TRANSLATED output.

<source_request>
{inputs}
</source_request>

<translated_output>
{outputs}
</translated_output>

Grade whether the translated output is SEMANTICALLY EQUIVALENT to the source. Specifically:
- Every entity, field, type, relationship, and query operation in the SOURCE is faithfully \
represented in the target's idioms.
- The query's filter/projection/ordering/grouping/limit semantics are preserved.
- NOTHING is invented: no entity, field, or query clause that is absent from the source.
- Target-framework idioms are used correctly (e.g. embedding vs references for the target store).

Return true only if the translation is a faithful, complete, semantically-equivalent rendering of \
the source with no invented or dropped elements."""


class JudgeResult(BaseModel):
    """The structured verdict every judge returns.

    ``score`` is declared FIRST on purpose: tool-calling/structured output fills fields in schema
    order, and the e-INFRA judge models tend to write a long ``reasoning`` that gets truncated before
    a trailing field would be emitted. Score-first means the verdict survives even if reasoning is cut
    off; ``reasoning`` is optional for the same reason.
    """

    score: bool = Field(description="true if the judged criterion is satisfied, false otherwise")
    reasoning: str = Field(default="", description="brief (<=40 words) justification for the score")


_JSON_OBJ_RE = re.compile(r"\{.*\}", re.S)


def _coalesce_text(content: Any) -> str:
    """Flatten a chat message's content (str or list of text/thinking blocks) to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for b in content:
            if isinstance(b, str):
                out.append(b)
            elif isinstance(b, dict) and b.get("type") == "text":
                out.append(b.get("text", ""))
        return "".join(out)
    return str(content or "")


async def _judge_call(judge, structured, prompt: str, key: str, timeout_s: float) -> dict:
    """Grade one (prompt) with the judge, robustly, and return a LangSmith feedback dict.

    Why not openevals' own scorer: ``create_async_llm_as_judge`` drives the judge through a
    structured-output method that HANGS against the e-INFRA models here (verified). We keep openevals'
    *prompts* but make the call ourselves: try ``with_structured_output`` first (clean), and on any
    failure/timeout fall back to a plain invoke + lenient JSON parse. On total failure we return a
    ``None`` score with the error in the comment, so one flaky judge never stalls the whole experiment
    (the per-judge ``timeout_s`` guards against the thinking-model long-prompt hang).
    """
    try:
        res = await asyncio.wait_for(structured.ainvoke(prompt), timeout=timeout_s)
        return {"key": key, "score": bool(res.score), "comment": res.reasoning}
    except Exception as primary:
        # Fallback: ask for raw JSON and parse it ourselves (handles models whose structured-output
        # path is unreliable but which answer plain prompts fine).
        try:
            suffix = (
                '\n\nRespond with ONLY a JSON object, no other text, no markdown, score FIRST: '
                '{"score": true or false, "reasoning": "<brief, <=40 words>"}'
            )
            msg = await asyncio.wait_for(judge.ainvoke(prompt + suffix), timeout=timeout_s)
            m = _JSON_OBJ_RE.search(_coalesce_text(msg.content))
            if m:
                data = json.loads(m.group(0))
                return {"key": key, "score": bool(data.get("score")),
                        "comment": str(data.get("reasoning", ""))}
            raise ValueError("no JSON object in judge response")
        except Exception as fallback:
            return {"key": key, "score": None,
                    "comment": f"judge error: structured={type(primary).__name__}: {primary}; "
                               f"fallback={type(fallback).__name__}: {fallback}"}


def _build_evaluators(judge, *, timeout_s: float = 90.0):
    """Return ASYNC ``aevaluate`` evaluators that grade with openevals' prompts via our own robust
    call (see :func:`_judge_call`). Per-judge kwargs differ, so each prompt is formatted individually
    (conciseness/code_correctness/equivalence: inputs+outputs; hallucination also gets
    context+reference_outputs, grounded on the source)."""
    from openevals.prompts import (
        CODE_CORRECTNESS_PROMPT,
        CONCISENESS_PROMPT,
        HALLUCINATION_PROMPT,
    )

    structured = judge.with_structured_output(JudgeResult)

    def _grade(inputs: dict, outputs: dict) -> tuple[str, str]:
        return _source_prompt(inputs), _translation_text(outputs)

    async def code_correctness_evaluator(inputs: dict, outputs: dict) -> dict:
        src, tgt = _grade(inputs, outputs)
        return await _judge_call(judge, structured,
                                 CODE_CORRECTNESS_PROMPT.format(inputs=src, outputs=tgt),
                                 "code_correctness", timeout_s)

    async def conciseness_evaluator(inputs: dict, outputs: dict) -> dict:
        src, tgt = _grade(inputs, outputs)
        return await _judge_call(judge, structured,
                                 CONCISENESS_PROMPT.format(inputs=src, outputs=tgt),
                                 "conciseness", timeout_s)

    async def hallucination_evaluator(inputs: dict, outputs: dict) -> dict:
        # Ground hallucination detection on the SOURCE: anything in the target not derivable from the
        # source request is an invention. No gold reference exists, so reference_outputs is empty.
        src, tgt = _grade(inputs, outputs)
        return await _judge_call(
            judge, structured,
            HALLUCINATION_PROMPT.format(inputs=src, outputs=tgt, context=src, reference_outputs=""),
            "hallucination", timeout_s)

    async def translation_equivalence_evaluator(inputs: dict, outputs: dict) -> dict:
        src, tgt = _grade(inputs, outputs)
        return await _judge_call(judge, structured,
                                 TRANSLATION_EQUIVALENCE_PROMPT.format(inputs=src, outputs=tgt),
                                 "translation_equivalence", timeout_s)

    return [
        code_correctness_evaluator,
        conciseness_evaluator,
        hallucination_evaluator,
        translation_equivalence_evaluator,
    ]


# ----------------------------------------------------------------------- deterministic evaluators
def _build_deterministic_evaluators() -> list:
    """Cheap NON-LLM evaluators that surface the target's precomputed deterministic metrics as
    LangSmith feedback scores. They make ZERO model calls — they just read fields the single graph
    run already produced (``outputs``), so the funnel/latency/pass@1 metrics ride the SAME run as the
    LLM judges (the 'don't run the pipeline twice' unification). Booleans map to 1.0/0.0; ``None``
    (metric unavailable, e.g. an errored run) is surfaced as a ``None`` score, not a fake 0."""
    keys = [
        "accepted", "compile_pass", "pass_at_1",
        "translation_loops", "wall_clock_s", "queries_equivalent", "queries_total",
    ]

    def _make(key: str):
        def _ev(inputs: dict, outputs: dict) -> dict:
            v = outputs.get(key)
            if isinstance(v, bool):
                v = 1.0 if v else 0.0
            return {"key": key, "score": v}
        _ev.__name__ = f"det_{key}"
        return _ev

    return [_make(k) for k in keys]


# --------------------------------------------------------------------------------------- preflight
def _preflight() -> list[str]:
    """TCP-liveness check of the live local stack BEFORE submitting any experiment, so a 1am misfire
    fails fast instead of yielding a whole night of errored runs. Dependency-free (stdlib socket): we
    only confirm each host:port accepts a connection (model endpoint, Daytona, MSSQL, MongoDB, Neo4j),
    parsed from the same env the graph uses. Returns a list of human-readable failures (empty == OK)."""
    import socket
    from urllib.parse import urlparse

    checks: list[tuple[str, str | None, int | None]] = []

    def _http(name: str, url: str, default_port: int) -> None:
        p = urlparse(url)
        port = p.port or (443 if p.scheme == "https" else default_port)
        checks.append((name, p.hostname, port))

    _http("model-endpoint", os.environ.get("OPENAI_API_URL", "https://llm.ai.e-infra.cz/v1"), 80)
    _http("daytona", os.environ.get("DAYTONA_API_URL", "http://localhost:3000/api"), 80)

    # MSSQL: "Server=host,port;Database=...". Default port 1433 if not specified.
    conn = os.environ.get("MSSQL_CONNECTION_STRING", "Server=localhost,1333;")
    server = next((seg.split("=", 1)[1] for seg in conn.split(";") if seg.lower().startswith("server=")), "")
    if server:
        host, _, port = server.partition(",")
        checks.append(("mssql", host.strip(), int(port) if port.strip().isdigit() else 1433))

    p = urlparse(os.environ.get("MONGODB_URI", "mongodb://localhost:27027"))
    checks.append(("mongodb", p.hostname, p.port or 27017))
    p = urlparse(os.environ.get("NEO4J_URI", "neo4j://localhost:7697"))
    checks.append(("neo4j", p.hostname, p.port or 7687))

    failures = []
    for name, host, port in checks:
        if not host or not port:
            failures.append(f"{name}: could not parse host/port")
            continue
        try:
            socket.create_connection((host, port), timeout=5).close()
            print(f"  preflight OK   {name} {host}:{port}")
        except Exception as e:  # noqa: BLE001
            failures.append(f"{name} {host}:{port} -> {type(e).__name__}: {e}")
    return failures


def _pair_short(pair: str) -> str:
    """Compact slug for experiment names, e.g. dotnet_efcore->java_spring_data_mongodb -> efcore-mongo."""
    src, _, dst = pair.partition("->")
    abbr = {
        "dotnet_efcore": "efcore", "dotnet_dapper": "dapper", "dotnet_nhibernate": "nhib",
        "java_spring_data_mongodb": "mongo", "java_spring_data_neo4j": "neo4j",
    }
    return f"{abbr.get(src, src)}-{abbr.get(dst, dst)}"


def _model_short(model: str | None) -> str:
    return (model or "default").rsplit("/", 1)[-1].replace(".", "")


# --------------------------------------------------------------------------------------------- main
async def main_async(args: argparse.Namespace) -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(args.env)
    except Exception:
        pass

    from langsmith import Client, aevaluate

    # Build the judges (shared across all experiments) + the cheap deterministic evaluators.
    evaluators: list = []
    if not args.no_judges:
        judge = await _build_judge_model(args.judge_model)
        evaluators = _build_evaluators(judge)
    det_evaluators = _build_deterministic_evaluators()

    # ---- dry-run: echo target over the whole dataset, judges only (no graph / Daytona / preflight).
    if args.dry_run:
        prefix = args.experiment_prefix or "uom-dryrun"
        print(f"=== DRY-RUN aevaluate over {DATASET_NAME!r} ({DATASET_ID}) — judges={len(evaluators)} ===")
        await aevaluate(
            _echo_target, data=DATASET_ID, evaluators=evaluators,
            experiment_prefix=prefix, max_concurrency=args.max_concurrency,
            num_repetitions=args.repetitions,
            metadata={"approach": args.approach, "judge_model": args.judge_model, "dry_run": True},
        )
        print(f"\nDry-run experiment: {prefix} — inspect judge scores in LangSmith.")
        return

    # ---- preflight (fail fast before burning the overnight window on a dead dependency).
    if not args.no_preflight:
        print("=== preflight: checking live stack (model endpoint / Daytona / DBs) ===")
        fails = _preflight()
        if fails:
            print("\nPREFLIGHT FAILED — not submitting experiments:")
            for f in fails:
                print(f"  ✘ {f}")
            raise SystemExit(2)
        print("  all dependencies reachable.")

    client = Client()
    all_examples = list(client.list_examples(dataset_id=DATASET_ID))

    def _meta(e):
        return getattr(e, "metadata", None) or {}

    pairs = args.pairs or sorted({_meta(e).get("pair") for e in all_examples if _meta(e).get("pair")})
    # small variant first (the fast gate), then full.
    variants = sorted(set(args.variants), key=lambda v: 0 if v == "small" else 1)
    models = SWEEP_MODELS if args.sweep else [(None, None)]

    # Per-INVOCATION tag (timestamp): groups this batch's predictions/summary and guarantees a re-run
    # never overwrites a previous batch's artifacts.
    import time
    run_tag = args.run_tag or time.strftime("%Y%m%d-%H%M%S")

    plan = [(v, p, m) for v in variants for p in pairs for m in models]
    print(f"=== run_tag={run_tag} | {len(plan)} experiment(s): {len(pairs)} pair x {len(variants)} "
          f"variant x {len(models)} model | approach={args.approach} reps={args.repetitions} "
          f"concurrency={args.max_concurrency} judges={len(evaluators)} ===")
    if args.record_fixtures:
        print(f"  recording LLM traffic per run → {args.aimock_root}/{args.dataset}/{run_tag}/"
              "<pair>/<gen_model>/<approach>-<uuid>/recorded/ (one aimock per run)")

    # Each experiment is isolated: a failure in ONE (LangSmith API error, auth blip, etc.) is caught
    # and logged so the remaining experiments still run — the overnight matrix is never aborted by a
    # single transient fault. (Per-EXAMPLE faults are already absorbed inside the target + run_one.)
    summary: list[dict] = []
    for i, (variant, pair, (gen_model, gen_reasoning)) in enumerate(plan, 1):
        examples = [
            e for e in all_examples
            if _meta(e).get("pair") == pair and _meta(e).get("variant") == variant
        ]
        prefix = (args.experiment_prefix or "uom") + \
            f"-{args.approach}-{_pair_short(pair)}-{variant}-{_model_short(gen_model)}"
        if not examples:
            print(f"  ({i}/{len(plan)} skip) no examples for {pair} [{variant}]")
            summary.append({"experiment": prefix, "pair": pair, "variant": variant,
                            "generate_model": gen_model or "default", "status": "skipped-no-examples"})
            continue
        target = await _make_target(
            args.approach, pred_root=args.pred_root, dataset=args.dataset, run_tag=run_tag,
            pair=pair, variant=variant,
            translation_model_override=gen_model, translation_reasoning_override=gen_reasoning,
            record_fixtures=args.record_fixtures, aimock_root=args.aimock_root,
            aimock_upstream=args.aimock_upstream,
        )
        print(f"\n--- ({i}/{len(plan)}) {prefix}  ({len(examples)} example(s) x {args.repetitions} reps) ---")
        rec = {"experiment": prefix, "pair": pair, "variant": variant,
               "generate_model": gen_model or "default", "examples": len(examples)}
        try:
            await aevaluate(
                target, data=examples, evaluators=[*evaluators, *det_evaluators],
                experiment_prefix=prefix, max_concurrency=args.max_concurrency,
                num_repetitions=args.repetitions,
                metadata={
                    "approach": args.approach, "pair": pair, "variant": variant, "run_tag": run_tag,
                    "generate_model": gen_model or "default", "judge_model": args.judge_model,
                },
            )
            rec["status"] = "ok"
        except Exception as e:  # noqa: BLE001 — one experiment's failure must not abort the rest
            rec["status"] = "failed"
            rec["error"] = f"{type(e).__name__}: {e}"
            print(f"  ✘ experiment FAILED (continuing): {rec['error']}")
        summary.append(rec)

    # Durable, timestamped summary (never overwrites a prior batch) — also the fault audit trail.
    ok = sum(1 for s in summary if s["status"] == "ok")
    failed = [s for s in summary if s["status"] == "failed"]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / f"experiments-summary-{run_tag}.json"
    summary_path.write_text(json.dumps(
        {"run_tag": run_tag, "approach": args.approach, "judge_model": args.judge_model,
         "ok": ok, "failed": len(failed), "experiments": summary}, indent=2))

    print(f"\nDone: {ok}/{len(plan)} experiments OK, {len(failed)} failed. Summary → {summary_path}")
    if failed:
        print("Failed experiments (re-run just these with --pairs/--variants):")
        for s in failed:
            print(f"  ✘ {s['experiment']}: {s.get('error')}")
    print("Open LangSmith → Datasets → 'UOM Final Experiments' → Experiments to compare.")
    print("→ CodeBLEU is a post-hoc pass: extract_predictions.py --reference + score_predictions.py "
          f"over the predictions tree at {args.pred_root}/{args.dataset}/{run_tag}/.")


def main() -> None:
    """CLI entry point."""
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--approach", default="our_approach", choices=["our_approach", "baseline"],
                    help="full agentic loop vs single_pass baseline")
    ap.add_argument("--variants", nargs="+", default=["full"], choices=["small", "full"],
                    help="which bundled query variants to run (small gate runs before full)")
    ap.add_argument("--pairs", nargs="*", default=None,
                    help="restrict to these metadata.pair slugs (default: all in the dataset)")
    ap.add_argument("--sweep", action="store_true",
                    help="run the 3-model generate_translation_node sweep (opt-in; otherwise the "
                         "production default model only)")
    ap.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL,
                    help="einfra/* model the LLM judges run on")
    ap.add_argument("--experiment-prefix", default=None,
                    help="LangSmith experiment name prefix (default: 'uom')")
    ap.add_argument("--max-concurrency", type=int, default=1,
                    help="parallel examples per experiment (keep low — each runs the full pipeline)")
    ap.add_argument("--repetitions", type=int, default=1,
                    help="runs per example ('10 iterations' per pair)")
    ap.add_argument("--pred-root", default="../predictions",
                    help="where finalize artifacts are written for the post-hoc CodeBLEU pass")
    ap.add_argument("--dataset", default="wwi", help="predictions-tree dataset folder name")
    ap.add_argument("--out", default="./out",
                    help="dir for the timestamped experiments-summary JSON (fault audit trail)")
    ap.add_argument("--run-tag", default=None,
                    help="batch tag grouping this invocation's predictions/summary (default: timestamp; "
                         "guarantees re-runs never overwrite a previous batch)")
    ap.add_argument("--record-fixtures", action="store_true",
                    help="spawn a throwaway aimock per run that RECORDS LLM traffic to its OWN dir "
                         "(under --aimock-root, mirroring the predictions tree); needs the live "
                         "upstream + the real OPENAI_API_KEY")
    ap.add_argument("--aimock-root", default="../aimock",
                    help="base dir for recorded fixtures (per-run subfolder created underneath)")
    ap.add_argument("--aimock-upstream", default=DEFAULT_UPSTREAM,
                    help="real OpenAI-compatible provider aimock proxies to (no trailing /v1)")
    ap.add_argument("--dry-run", action="store_true",
                    help="echo target (no graph/Daytona) to validate dataset+judge plumbing")
    ap.add_argument("--no-judges", action="store_true", help="skip LLM judges (deterministic only)")
    ap.add_argument("--no-preflight", action="store_true", help="skip the live-stack TCP preflight")
    ap.add_argument("--env", default="../.env", help="path to .env with LANGSMITH_*/OPENAI_* keys")
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
