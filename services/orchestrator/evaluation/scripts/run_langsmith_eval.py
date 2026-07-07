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
  * Judges (LLM-as-judge, all REFERENCE-FREE, graded against the SOURCE in the input, all
    SCAFFOLD-AWARE and true=good so charts are uniformly higher-is-better):
      - code_correctness        : does the underlying translated code correctly implement the
                                  source's data operations in idiomatic target APIs?
      - conciseness             : is the underlying logic direct/idiomatic (no gratuitous complexity)?
      - faithfulness            : no invented/dropped DOMAIN entities/fields/queries (replaces the old
                                  detection-phrased, inverted-polarity ``hallucination`` judge).
      - translation_equivalence : does the target preserve the source schema/query semantics?
    Every prompt tells the judge to look THROUGH the execution-probe harness + boilerplate (the old
    prompts read that instrumentation as "invented behavior" and rejected 100% of runs — verified in
    the recorded fixtures). We deliberately do NOT use a "first-accepted-as-reference" judge: coherent
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
# Default judge = gemma4 (non-thinking): live-verified 0 None on the 35KB harness prompts and it cleanly
# separates a real translation from an empty one. kimi-k2.7 (thinking) discriminates finer (catches a
# subtle single-query corruption) but its structured-output path is slow → some None under judge
# concurrency — pass --judge-model einfra/kimi-k2.7 when you want that finer sensitivity. See _judge_call.
DEFAULT_JUDGE_MODEL = "einfra/gemma4"
DEFAULT_TRANSLATION_MODEL = "einfra/kimi-k2.7"  # default graph model (non-reasoning, fast, multimodal)


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
    """The target's translated code, combined into one string for the judges to grade.

    Grading priority: clean finalized code → the VALIDATED target harness (exists whenever the
    agent saved a draft, even on rejection) → the explanation message. Grading the harness on
    non-accepted runs is what makes the judge metrics measure translation quality instead of
    pipeline completion — previously they graded the literal '[Structured Output Error] …' string
    and returned 0/1 constants.
    """
    blocks = []
    if outputs.get("translated_schema_code"):
        blocks.append("// --- translated schema ---\n" + outputs["translated_schema_code"])
    if outputs.get("translated_query_code"):
        blocks.append("// --- translated query ---\n" + outputs["translated_query_code"])
    if not blocks and outputs.get("target_validation_harness_code"):
        blocks.append(
            "// --- validated target harness (translation not finalized/accepted) ---\n"
            + str(outputs["target_validation_harness_code"])
        )
    if not blocks and outputs.get("explanation_message"):
        # Nothing produced at all; let the judges grade whatever the agent produced/explained.
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
    in-memory replay cache never short-circuits a recording.
    """
    import uuid as _uuid

    from extract_predictions import _write_artifacts, slug
    from run_experiment import run_one

    single_pass = approach == "baseline"
    
    gen_model_tag = translation_model_override or DEFAULT_TRANSLATION_MODEL  # default graph model (non-reasoning, fast, multimodal)
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
                # Judges grade the validated harness when the run was not accepted (see
                # _translation_text) — measuring translation quality, not pipeline completion.
                "target_validation_harness_code": r.get("_target_harness_code"),
                "explanation_message": None,
                "accepted": bool(r.get("accepted")),
                "passed": bool(r.get("passed")),
                "compile_pass": bool(r.get("compile_pass")),
                "schema_validated": bool(r.get("schema_validated")),
                "pass_at_1": r.get("pass_at_1"),
                "translation_loops": r.get("translation_loops"),
                "wall_clock_s": r.get("wall_clock_s"),
                "queries_total": r.get("queries_total"),
                "queries_equivalent": r.get("queries_equivalent"),
                "queries_expected": r.get("queries_expected"),
                "queries_claimed": r.get("queries_claimed"),
                "queries_accepted": r.get("queries_accepted"),
                "query_accuracy": r.get("query_accuracy"),
                "query_precision": r.get("query_precision"),
                "query_recall": r.get("query_recall"),
                "query_verdicts": r.get("query_verdicts"),
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


# --- Scaffold-aware judges (rewritten 2026-07-06) -------------------------------------------------
# WHY the previous judges scored ~0 on EVERYTHING (even runs the deterministic execution-equivalence
# checker passed): the translated output the judge sees is INSTRUMENTED for automated testing — each
# query is wrapped in a small harness method that returns a Map/dict of execution probes (``count``,
# ``firstSample``, ``lastSample`` …) and the file carries boilerplate (imports, an entrypoint class,
# DB/session setup, JSON config). The old prompts' absolutist "NOTHING is invented / no clause absent
# from the source" rule made the judge read that harness+boilerplate as "invented behavior" and
# reject uniformly (verified in the recorded fixtures: the judge reasoning literally flagged the
# count/firstSample/lastSample Map as "invented behavior … significant semantic deviation"). The fix
# is criteria, not the library: tell every judge the probe wrapper + boilerplate are the EXPECTED test
# harness to look THROUGH, and grade only the underlying schema/query semantics against the source.
_SCAFFOLD_NOTE = """The TRANSLATED output is INSTRUMENTED for automated execution-equivalence \
testing. Treat all of the following as an EXPECTED test harness and IGNORE it when grading — it is \
NOT part of the translation and is NOT an invention or deviation:
- each query wrapped in a helper/harness method that returns a Map/dict of probe values such as \
`count`, `firstSample`, `lastSample`, `rows`, or similar (an execution fingerprint, not a source feature);
- boilerplate: package/imports/using directives, an entrypoint or `main` class, DB/session/template \
setup, logging, JSON/serialization configuration, and result-printing.
Grade ONLY the UNDERLYING data mapping and query logic (entities, fields, types, relationships, and \
each query's filter / projection / join / ordering / grouping / limit) against the source request."""

TRANSLATION_EQUIVALENCE_PROMPT = """You are an expert grader of database object-mapping/ORM code \
translations. You are given the SOURCE translation request (source ORM schema and/or queries) and \
the model's TRANSLATED output (in the target framework).

<source_request>
{inputs}
</source_request>

<translated_output>
{outputs}
</translated_output>

""" + _SCAFFOLD_NOTE + """

Score the FRACTION [0,1] of the source's queries (plus the schema mapping) that are rendered in the \
target with FULL semantic equivalence:
- every entity/field/type/relationship represented with the correct target idiom (e.g. embedding vs \
references for the target store);
- each query's filter, projection, join/traversal, ordering, grouping, and limit semantics preserved \
(values, comparison operators, and result shape match once the probe wrapper is ignored).
1.0 = the schema and every query are equivalent. Lower the score IN PROPORTION to how many queries \
(or the schema) have a genuine semantic difference — a wrong/missing filter, a dropped or invented \
field, wrong ordering/grouping, wrong relationship direction. Do NOT score 0 because a minority of \
queries are wrong (e.g. 13 of 15 equivalent ≈ 0.87). Minor idiomatic differences and the test \
harness itself do not lower the score."""

CODE_CORRECTNESS_PROMPT = """You are an expert grader of database object-mapping/ORM code \
translations. Given the SOURCE request and the model's TRANSLATED output in the target framework, \
judge whether the underlying translated code is CORRECT.

<source_request>
{inputs}
</source_request>

<translated_output>
{outputs}
</translated_output>

""" + _SCAFFOLD_NOTE + """

Score the FRACTION [0,1] of the underlying translated code (schema mapping + each query) that is \
CORRECT: would compile and execute against the target store and correctly implement the source's \
data operations using idiomatic target-framework APIs (correct types, correct query builder / \
criteria / traversal usage, correct field references). 1.0 = the schema and every query are correct; \
lower the score in proportion to how many have a real defect (wrong API usage that would not \
compile/run, a query that computes the wrong result). Do NOT score 0 for a minority of bad queries, \
and do NOT penalise the presence of the test harness."""

FAITHFULNESS_PROMPT = """You are an expert grader checking a database object-mapping/ORM code \
translation for FAITHFULNESS (no hallucinated or dropped domain content).

<source_request>
{inputs}
</source_request>

<translated_output>
{outputs}
</translated_output>

""" + _SCAFFOLD_NOTE + """

Score the FRACTION [0,1] of the translation that is FAITHFUL: every entity, field, and query in the \
source appears in the target, and the target does NOT invent domain entities, fields, filters, or \
query clauses absent from the source. 1.0 = fully faithful; lower in proportion to how much real \
DOMAIN content was invented or dropped. The probe wrapper and boilerplate above are NOT inventions — \
ignore them. Do NOT score 0 for a minor omission/invention (higher score = more faithful)."""

CONCISENESS_PROMPT = """You are grading whether a database object-mapping/ORM code translation is \
CONCISE in its underlying logic (no gratuitous complexity).

<source_request>
{inputs}
</source_request>

<translated_output>
{outputs}
</translated_output>

""" + _SCAFFOLD_NOTE + """

Score the FRACTION [0,1] of the underlying schema mapping and queries that are expressed directly \
and idiomatically, without redundant round-trips, dead code, or needlessly convoluted query \
construction. 1.0 = uniformly concise; lower in proportion to how much of the UNDERLYING logic is \
gratuitously complex. The test harness and boilerplate do NOT count against conciseness — ignore \
them. Do NOT score 0 for one clumsy query (higher score = more concise)."""


class JudgeResult(BaseModel):
    """The structured verdict every judge returns — a GRADED (continuous) score, not a boolean.

    Why graded, not boolean: these prompts grade a BUNDLE of up to 15 queries + the schema at once. A
    boolean "is the whole thing perfect?" collapses to false on ANY single imperfect query, so with 15
    queries it is ~always false even for a strong translation — the exact 'judge always rejects' bug
    (verified: on a run the deterministic checker passed 13/15, the boolean judge said false, correctly
    citing 2 bad queries, but threw away the 13 good ones). A fraction in [0,1] = the proportion of the
    translation that satisfies the criterion instead TRACKS the deterministic per-query accuracy (that
    run scores ~0.87, not 0) and still discriminates good from bad.

    ``score`` is declared FIRST on purpose: structured output fills fields in schema order and the
    e-INFRA judge models write a long ``reasoning`` that can truncate before a trailing field; score-
    first means the verdict survives truncation, and ``reasoning`` is optional for the same reason.
    """

    score: float = Field(
        description="fraction in [0.0, 1.0] = the proportion of the translation (its queries and "
        "schema) that satisfies this criterion. 1.0 = fully satisfied; 0.0 = not at all. Do NOT "
        "return 0 just because a minority of queries have issues — score the proportion that ARE "
        "correct (e.g. 13 of 15 queries good ≈ 0.87)."
    )
    reasoning: str = Field(default="", description="brief (<=40 words) justification for the score")


_JSON_OBJ_RE = re.compile(r"\{.*\}", re.S)


def _clamp01(v: Any) -> float | None:
    """Coerce a judge score to a float in [0,1]. Accepts a bool (a model that ignored the fraction
    instruction and answered true/false → 1.0/0.0) or a numeric string; returns None if unparseable
    so a malformed verdict surfaces as 'no score', never a fake 0.
    """
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return None


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
    structured-output method that HANGS against the e-INFRA thinking models here (verified). We keep
    our prompts but make the call ourselves: try ``with_structured_output`` first (clean), and on any
    failure/timeout/unparseable-score fall back to a plain invoke + lenient JSON parse. On total
    failure we return a ``None`` score (never a fake 0) so one flaky judge never stalls the experiment,
    and the aggregate simply skips None.

    JUDGE-MODEL NOTE (both verified live on the 35KB harness prompts, tradeoff is real):
      * kimi-k2.7 (THINKING): more DISCRIMINATING — scores a genuine 13/15 run ~0.81, catches a single
        corrupted query filter (~0.75), an empty output 0.0 — but its structured-output path is slow
        and under judge concurrency some calls time out → ``None`` (graceful; the aggregate skips it).
      * gemma4 (NON-thinking): perfectly RELIABLE (0 None) and cleanly separates a real translation
        (~0.73) from an empty one (0.0), but COARSER — it missed the single-filter corruption (scored
        it the same 0.73). Fast, no structured hang. ``--judge-model einfra/gemma4``.
    Pick by need: gemma4 for clean aggregate correlation with query_accuracy (no None), kimi-k2.7 for
    finer per-query sensitivity. The per-judge ``timeout_s`` bounds either way."""
    try:
        res = await asyncio.wait_for(structured.ainvoke(prompt), timeout=timeout_s)
        if _clamp01(res.score) is not None:
            return {"key": key, "score": _clamp01(res.score), "comment": res.reasoning}
        raise ValueError("structured verdict had no parseable score")
    except Exception as primary:
        # Fallback: ask for raw JSON and parse it ourselves (handles models whose structured-output
        # path is unreliable but which answer plain prompts fine).
        try:
            suffix = (
                '\n\nRespond with ONLY a JSON object, no other text, no markdown, score FIRST — score '
                'is a FRACTION in [0,1] = the proportion of the translation satisfying the criterion '
                '(1.0=fully, 0.0=not at all; do not return 0 for a minority of bad queries): '
                '{"score": 0.0-1.0, "reasoning": "<brief, <=40 words>"}'
            )
            msg = await asyncio.wait_for(judge.ainvoke(prompt + suffix), timeout=timeout_s)
            m = _JSON_OBJ_RE.search(_coalesce_text(msg.content))
            if m:
                data = json.loads(m.group(0))
                return {"key": key, "score": _clamp01(data.get("score")),
                        "comment": str(data.get("reasoning", ""))}
            raise ValueError("no JSON object in judge response")
        except Exception as fallback:
            return {"key": key, "score": None,
                    "comment": f"judge error: structured={type(primary).__name__}: {primary}; "
                               f"fallback={type(fallback).__name__}: {fallback}"}


def _build_evaluators(judge, *, timeout_s: float = 90.0):
    """Return ASYNC ``aevaluate`` evaluators that grade with our SCAFFOLD-AWARE prompts via the robust
    call (see :func:`_judge_call`). All four are reference-free, graded against the SOURCE, and score
    true=good (uniform polarity, so charts are 'higher is better' without a special-cased judge). We
    dropped openevals' generic prompts + the detection-phrased hallucination judge: the generic
    prompts read the execution-probe harness as 'invented behavior' and rejected everything, and the
    hallucination judge's polarity was inverted/vacuous on empty outputs. ``faithfulness`` replaces it
    (true = faithful, no invented/dropped DOMAIN content, ignoring the harness).
    """
    structured = judge.with_structured_output(JudgeResult)

    def _grade(inputs: dict, outputs: dict) -> tuple[str, str]:
        return _source_prompt(inputs), _translation_text(outputs)

    def _make(key: str, prompt: str):
        async def _ev(inputs: dict, outputs: dict) -> dict:
            src, tgt = _grade(inputs, outputs)
            return await _judge_call(judge, structured, prompt.format(inputs=src, outputs=tgt),
                                     key, timeout_s)
        _ev.__name__ = f"{key}_evaluator"
        return _ev

    return [
        _make("code_correctness", CODE_CORRECTNESS_PROMPT),
        _make("conciseness", CONCISENESS_PROMPT),
        _make("faithfulness", FAITHFULNESS_PROMPT),
        _make("translation_equivalence", TRANSLATION_EQUIVALENCE_PROMPT),
    ]


# ----------------------------------------------------------------------- deterministic evaluators
def _build_deterministic_evaluators() -> list:
    """Cheap NON-LLM evaluators that surface the target's precomputed deterministic metrics as
    LangSmith feedback scores. They make ZERO model calls — they just read fields the single graph
    run already produced (``outputs``), so the funnel/latency/pass@1 metrics ride the SAME run as the
    LLM judges (the 'don't run the pipeline twice' unification). Booleans map to 1.0/0.0; ``None``
    (metric unavailable, e.g. an errored run) is surfaced as a ``None`` score, not a fake 0.
    """
    keys = [
        "accepted", "passed", "compile_pass", "schema_validated", "pass_at_1",
        "translation_loops", "wall_clock_s", "queries_equivalent", "queries_total",
        # Per-query headline metrics: accuracy over the queries the task DEMANDED, plus
        # precision (over what the system saved) and recall (over what was asked).
        "queries_expected", "queries_claimed", "queries_accepted",
        "query_accuracy", "query_precision", "query_recall",
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


def _build_codebleu_evaluator(dataset: str, ref_root: str) -> list:
    """Optional NON-LLM CodeBLEU evaluator that rides the SAME run (no extra pipeline execution),
    scoring the run's finalized code against the frozen per-pair reference under ``ref_root`` and
    surfacing ``codebleu_schema`` / ``codebleu_queries`` / ``codebleu`` as LangSmith feedback — so
    CodeBLEU sits next to the other deterministic metrics instead of only in the post-hoc pass.

    Graceful & self-disabling: returns ``[]`` when codebleu isn't importable in this venv (it lives in
    the eval extra) OR when the reference tree is missing, so the default orchestrator-venv run never
    breaks. When on but a given pair has no reference yet (first run, pre-bootstrap), it scores
    ``None`` for that run. CodeBLEU is SECONDARY — structural similarity, not correctness (it penalises
    equivalent-but-restructured code); the headline remains execution-equivalence pass@k.
    """
    try:
        from codebleu import (
            calc_codebleu,  # type: ignore[import-not-found]  # noqa: F401
        )
    except ImportError:
        return []
    if not Path(ref_root).exists():
        return []

    from extract_predictions import pair_slug, target_lang
    from score_predictions import _codebleu

    def _ref_texts(outputs: dict) -> tuple[str | None, str | None, str] | None:
        pair = outputs.get("pair") or ""
        src, _, dst = pair.partition(" -> ")
        if not src or not dst:
            return None
        lang, ext = target_lang(dst)
        base = Path(ref_root) / dataset / pair_slug(src, dst)
        sref = base / f"schema.{ext}"
        qref = base / f"queries.{ext}"
        return (sref.read_text(encoding="utf-8") if sref.exists() else None,
                qref.read_text(encoding="utf-8") if qref.exists() else None, lang)

    def _score(outputs: dict, artifact: str) -> float | None:
        refs = _ref_texts(outputs)
        if not refs:
            return None
        sref, qref, lang = refs
        ref = sref if artifact == "schema" else qref
        hyp = outputs.get("translated_schema_code" if artifact == "schema" else "translated_query_code")
        if not ref or not hyp:
            return None
        cb = _codebleu(ref, str(hyp), lang)
        return cb["codebleu"] if cb else None

    def codebleu_schema(inputs: dict, outputs: dict) -> dict:
        return {"key": "codebleu_schema", "score": _score(outputs, "schema")}

    def codebleu_queries(inputs: dict, outputs: dict) -> dict:
        return {"key": "codebleu_queries", "score": _score(outputs, "queries")}

    def codebleu_mean(inputs: dict, outputs: dict) -> dict:
        parts = [p for p in (_score(outputs, "schema"), _score(outputs, "queries")) if p is not None]
        return {"key": "codebleu", "score": round(sum(parts) / len(parts), 4) if parts else None}

    return [codebleu_schema, codebleu_queries, codebleu_mean]


# --------------------------------------------------------------------------------------- preflight
def _preflight() -> list[str]:
    """TCP-liveness check of the live local stack BEFORE submitting any experiment, so a 1am misfire
    fails fast instead of yielding a whole night of errored runs. Dependency-free (stdlib socket): we
    only confirm each host:port accepts a connection (model endpoint, Daytona, MSSQL, MongoDB, Neo4j),
    parsed from the same env the graph uses. Returns a list of human-readable failures (empty == OK).
    """
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
    return (model or DEFAULT_TRANSLATION_MODEL).rsplit("/", 1)[-1].replace("-", "_").replace(".", "")


# --------------------------------------------------------------------------------------------- main
def _force_blocking_stdio() -> None:
    """Guard against ``BlockingIOError: [Errno 11] write could not complete without blocking`` killing
    an experiment mid-run. If this process inherited a NON-blocking stdout/stderr (seen when the eval
    is launched from certain shells / CI / long-output pipes), a single large ``print`` raises on the
    write — and because it happens INSIDE ``aevaluate`` it aborts that whole pair's experiment. This is
    exactly how efcore-neo4j died on the 5-07 run (BlockingIOError in the summary) while the other
    pairs finished: the neo4j runs emit very large tool outputs (200KB+ sample dumps), so they hit the
    full pipe buffer first. Forcing the fds back to blocking makes every write complete.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            os.set_blocking(stream.fileno(), True)
        except (OSError, ValueError, AttributeError):
            pass  # not a real fd (redirected to a StringIO etc.) — nothing to force


async def main_async(args: argparse.Namespace) -> None:
    _force_blocking_stdio()
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
    if not args.no_codebleu:
        cb = _build_codebleu_evaluator(args.dataset, args.ref_root)
        if cb:
            det_evaluators += cb
            print(f"  CodeBLEU evaluator ON (reference tree {args.ref_root})")

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
    # small variant first (the fast gate), then the 5-query batches, then full.
    _variant_order = {"small": 0, "batch1": 1, "batch2": 2, "batch3": 3, "full": 4}
    variants = sorted(set(args.variants), key=lambda v: _variant_order.get(v, 9))
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
                            "generate_model": gen_model or DEFAULT_TRANSLATION_MODEL, "status": "skipped-no-examples"})
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
               "generate_model": gen_model or DEFAULT_TRANSLATION_MODEL, "examples": len(examples)}
        try:
            await aevaluate(
                target, data=examples, evaluators=[*evaluators, *det_evaluators],
                experiment_prefix=prefix, max_concurrency=args.max_concurrency,
                num_repetitions=args.repetitions,
                metadata={
                    "approach": args.approach, "pair": pair, "variant": variant, "run_tag": run_tag,
                    "generate_model": gen_model or DEFAULT_TRANSLATION_MODEL, "judge_model": args.judge_model,
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
    ap.add_argument("--variants", nargs="+", default=["batch1", "batch2", "batch3"],
                    choices=["small", "batch1", "batch2", "batch3", "full"],
                    help="which bundled query variants to run (default: the three 5-query "
                         "batches covering all 15 queries; small gate runs first if included)")
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
    ap.add_argument("--no-codebleu", action="store_true",
                    help="skip the optional CodeBLEU deterministic evaluator (it self-disables anyway "
                         "when codebleu isn't installed or the reference tree is missing)")
    ap.add_argument("--ref-root", default="../reference",
                    help="frozen per-pair CodeBLEU reference tree for the in-run CodeBLEU evaluator")
    ap.add_argument("--no-preflight", action="store_true", help="skip the live-stack TCP preflight")
    ap.add_argument("--env", default="../.env", help="path to .env with LANGSMITH_*/OPENAI_* keys")
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
