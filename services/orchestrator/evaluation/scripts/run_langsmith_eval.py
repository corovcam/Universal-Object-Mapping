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
        --judge-model einfra/kimi-k2.6 --env .env

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
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# orchestrator src on path
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parents[1] / "src"))  # services/orchestrator/src

DATASET_ID = "56708f08-2697-4af2-b3b7-9172c0e68b4b"  # "UOM Final Experiments"
DATASET_NAME = "UOM Final Experiments"
# Judge model is finicky on e-INFRA (verified empirically): thinking models (gpt-oss-120b, mini,
# qwen-coder) reason heavily on the long grading prompts and HANG `with_structured_output`;
# llama-4-scout is non-thinking and fast (<1s) but occasionally drops the schema. The judge call is
# made robust (structured → JSON-fallback → graceful None, per-judge timeout), and the model is a CLI
# knob so it can be tuned on the live stack. Default to the fast non-thinking instruct model.
DEFAULT_JUDGE_MODEL = "einfra/deepseek-v4-pro-thinking"


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


# ------------------------------------------------------------------------------------------- target
async def _make_target(approach: str, model_name: str | None):
    """Build an async ``aevaluate`` target that runs the graph on one dataset example."""
    from langchain_core.messages import HumanMessage
    from langgraph.checkpoint.memory import MemorySaver

    from react_agent.constants import AvailableModel
    from react_agent.context import Context
    from react_agent.graph import graph

    single_pass = approach == "baseline"
    model = AvailableModel(model_name) if model_name else None

    async def target(inputs: dict[str, Any]) -> dict[str, Any]:
        prompt = _source_prompt(inputs)
        # output_schema=OutputState narrows ainvoke's return; a checkpointer lets us read the FULL
        # final State (validation results, equivalence, loop count) via aget_state.
        g = graph.builder.compile(checkpointer=MemorySaver(), name="UOM LangSmith Eval")
        run_id = str(uuid.uuid4())
        config = {
            "configurable": {"thread_id": run_id},
            "recursion_limit": 80,
            "run_id": run_id,
            "metadata": {"approach": approach, "single_pass": single_pass},
        }
        ctx = Context(model=model) if model else Context()
        try:
            await g.ainvoke(
                {"messages": [HumanMessage(content=prompt)], "single_pass": single_pass},
                config=config,
                context=ctx,
            )
        except Exception as e:  # surface the failure as output rather than aborting the experiment
            return {"error": f"{type(e).__name__}: {e}", "accepted": False}
        st = (await g.aget_state(config)).values
        src = st.get("source_target")
        dst = st.get("destination_target")
        schema_code = st.get("translated_schema_code")
        query_code = st.get("translated_query_code")
        return {
            "translated_schema_code": schema_code,
            "translated_query_code": query_code,
            "explanation_message": st.get("explanation_message"),
            "accepted": bool(schema_code or query_code),
            "translation_loops": int(st.get("translation_loop_count", 0) or 0),
            "pair": (
                f"{getattr(src, 'value', src)} -> {getattr(dst, 'value', dst)}"
                if src and dst
                else "unknown"
            ),
        }

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
        {"openai_api_url": url, "openai_api_key": key, "temperature": 0, "reasoning": False},
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


# --------------------------------------------------------------------------------------------- main
async def main_async(args: argparse.Namespace) -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(args.env)
    except Exception:
        pass

    from langsmith import aevaluate

    if args.dry_run:
        target = _echo_target
        evaluators: list = []
        if not args.no_judges:
            judge = await _build_judge_model(args.judge_model)
            evaluators = _build_evaluators(judge)
        prefix = args.experiment_prefix or "uom-dryrun"
    else:
        target = await _make_target(args.approach, args.model)
        judge = await _build_judge_model(args.judge_model)
        evaluators = _build_evaluators(judge)
        prefix = args.experiment_prefix or f"uom-{args.approach}"

    print(f"=== aevaluate over dataset {DATASET_NAME!r} ({DATASET_ID}) ===")
    print(f"  target={'echo (dry-run)' if args.dry_run else args.approach}  "
          f"judge_model={args.judge_model}  judges={len(evaluators)}  "
          f"max_concurrency={args.max_concurrency}  repetitions={args.repetitions}")

    results = await aevaluate(
        target,
        data=DATASET_ID,
        evaluators=evaluators,
        experiment_prefix=prefix,
        max_concurrency=args.max_concurrency,
        num_repetitions=args.repetitions,
        metadata={"approach": args.approach, "judge_model": args.judge_model,
                  "dry_run": args.dry_run},
    )
    # Surface the experiment URL/name for the user.
    name = getattr(results, "experiment_name", None)
    print(f"\nExperiment: {name or prefix}")
    print("Open LangSmith → Datasets → 'UOM Final Experiments' → Experiments to inspect scores.")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--approach", default="our_approach", choices=["our_approach", "baseline"],
                    help="full agentic loop vs single_pass baseline")
    ap.add_argument("--model", default=None,
                    help="AvailableModel value for the TARGET graph (default: Context default)")
    ap.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL,
                    help="einfra/* model the LLM judges run on (reasoning forced off)")
    ap.add_argument("--experiment-prefix", default=None,
                    help="LangSmith experiment name prefix (default: uom-<approach>)")
    ap.add_argument("--max-concurrency", type=int, default=2,
                    help="parallel examples (keep low — each runs the full live pipeline)")
    ap.add_argument("--repetitions", type=int, default=1,
                    help="runs per example (variance / pass@k style)")
    ap.add_argument("--dry-run", action="store_true",
                    help="echo target (no graph/Daytona) to validate dataset+judge plumbing")
    ap.add_argument("--no-judges", action="store_true",
                    help="with --dry-run: also skip judges (pure dataset/target wiring check)")
    ap.add_argument("--env", default="../.env", help="path to .env with LANGSMITH_*/OPENAI_* keys")
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
