#!/usr/bin/env python3
"""export_manual_prompts.py — emit the translation-stage prompt for MANUAL SOTA-model evaluation.

The baseline arm wants state-of-the-art proprietary models (Claude, GPT, Gemini) as a comparison
point, but those are only available here through chat UIs / CLIs (Claude Code, Claude.ai, Gemini
app, Google AI Studio, Antigravity), not via API keys. This script produces a copy-pasteable
**system prompt + user prompt** for one WWI fixture so the translation can be run by hand in any of
those, then fed back for scoring.

Fidelity: it drives the real graph with `interrupt_before=["generate_translation_node"]`, so the
live `extract_input` (framework/version/source-code parsing) and `schema_inspection` (DB schema
context) populate the State exactly as a normal run would — then it renders the prompt with the
SAME `build_system_prompt` / `build_translation_user_message` the node itself uses. What you paste
into Claude/Gemini is byte-for-byte what the pipeline sends its own model. (This needs the live
stack — e-INFRA for extract_input, Daytona/DB for schema_inspection — but it stops BEFORE the
translation model call, so it spends no SOTA tokens and never touches the proprietary models.)

Outputs, per run, under <out>/<dataset>/<fixture>__<timestamp>/:
  * system.txt  — the system prompt, raw (cleanest to copy)
  * user.txt    — the user prompt, raw
  * prompt.md   — both, plus per-platform paste instructions and an output-capture template

Usage (orchestrator venv — imports react_agent):
  .venv/bin/python evaluation/scripts/export_manual_prompts.py --fixture efcore-mongodb-q1 \
      --out evaluation/manual-eval --env .env
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
import types
import uuid
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parents[1] / "src"))  # services/orchestrator/src
from run_experiment import FIXTURES, _load_fixture  # noqa: E402

# Fields the two prompt builders read off the State (attribute access only) — gathered from the
# interrupted graph's state dict into a lightweight shim so we don't reconstruct the full dataclass.
_PROMPT_STATE_FIELDS = (
    "source_target", "destination_target", "translation_type",
    "source_target_version", "destination_target_version",
    "schema_context", "source_schema_code", "source_query_code",
)


def _val(x) -> str | None:
    return x.value if hasattr(x, "value") else (x or None)


async def export_one(fixture_text: str, fixture: str, model, out_root: Path) -> Path:
    from langchain_core.messages import HumanMessage
    from langgraph.checkpoint.memory import MemorySaver

    from react_agent.context import Context
    from react_agent.graph import graph
    from react_agent.prompts import build_system_prompt, build_translation_user_message

    # Pause BEFORE generation: extract_input + schema_inspection run for real, the model call does
    # not. A checkpointer is required for interrupts and to read the paused State.
    g = graph.builder.compile(
        checkpointer=MemorySaver(),
        interrupt_before=["generate_translation_node"],
        name="UOM Prompt Exporter",
    )
    ctx = Context(model=model) if model else Context()
    run_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": run_id}, "recursion_limit": 80, "run_id": run_id}

    await g.ainvoke({"messages": [HumanMessage(content=fixture_text)]}, config=config, context=ctx)
    snap = await g.aget_state(config)
    st = snap.values

    if st.get("source_target") is None or st.get("destination_target") is None:
        raise SystemExit(
            "graph stopped before targets were resolved — extract_input did not complete; "
            "check the live stack (e-INFRA / DB inspection) and the fixture."
        )

    # Shim with attribute access for the prompt builders (they only read; never reconstruct State).
    shim = types.SimpleNamespace(**{f: st.get(f) for f in _PROMPT_STATE_FIELDS})
    system_prompt = await build_system_prompt(shim)  # type: ignore[arg-type]
    user_prompt = build_translation_user_message(shim)  # type: ignore[arg-type]

    pair = f"{_val(st.get('source_target'))} → {_val(st.get('destination_target'))}"
    ttype = _val(st.get("translation_type")) or "both"
    ts = time.strftime("%Y%m%d-%H%M%S")
    out = out_root / "wwi" / f"{fixture}__{ts}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "system.txt").write_text(system_prompt, encoding="utf-8")
    (out / "user.txt").write_text(user_prompt, encoding="utf-8")
    (out / "prompt.md").write_text(
        _render_markdown(fixture, pair, ttype, system_prompt, user_prompt), encoding="utf-8"
    )
    return out


# A 5-backtick fence so the prompts (which contain ``` and ` from code + schema tables) never break
# out of their block in the rendered markdown.
_F = "`````"


def _render_markdown(fixture: str, pair: str, ttype: str, system_prompt: str, user_prompt: str) -> str:
    return f"""# Manual translation prompt — {fixture}

| | |
|---|---|
| **Pair** | {pair} |
| **Translation type** | {ttype} |
| **Fixture** | `{fixture}` (WideWorldImporters) |
| **Source of prompt** | the orchestrator's own translation stage (`build_system_prompt` + `build_translation_user_message`), captured live before the model call — identical to what the pipeline sends its own model. |

Run this by hand in a SOTA chat model to produce a baseline translation, then capture the output
for scoring. The two prompts below are **verbatim**; copy them from `system.txt` / `user.txt` in
this folder (cleaner than copying out of the fences here).

## How to run it per platform

- **Claude.ai / Gemini app / Google AI Studio / Antigravity** — paste **System prompt** into the
  *system instructions* box (AI Studio: "System instructions"; Antigravity: system message), and
  **User prompt** as the first chat message. If there is no system box (plain Claude.ai chat), send
  the system prompt as the first message, then the user prompt as the second.
- **Claude Code** — put the System prompt in a `CLAUDE.md` (or pass via `--append-system-prompt`),
  then send the User prompt as your message.

## ⚠️ Manual-run adaptation (append to the user prompt)

The system prompt tells the model to finish by *calling the `save_translation` tool* and mentions
research tools (`search_spring_docs`, `microsoft_docs_search`, …). A chat UI has no such tools, so
append this to the **end of the user prompt** before sending:

{_F}
There are no tools available in this chat. Do NOT call save_translation; instead, output your
result as two fenced code blocks, labeled exactly:

```source_validation_body
<the SOURCE-side runnable harness body>
```
```target_validation_body
<the TARGET-side runnable harness body>
```

Use only your own knowledge for any framework API details (the research tools are unavailable).
{_F}

## System prompt

{_F}text
{system_prompt}
{_F}

## User prompt

{_F}text
{user_prompt}
{_F}

## Capture the result

Save the model's two `*_validation_body` blocks (and which model/platform produced them) so they can
be assembled and validated through the same pipeline as the automated runs for an apples-to-apples
comparison.
"""


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

    out_root = Path(args.out)
    fixtures = args.fixtures or [args.fixture]
    for fx in fixtures:
        print(f"=== exporting prompt for {fx} (running graph up to generate_translation_node) ===")
        text = _load_fixture(fx)
        out = await export_one(text, fx, model, out_root)
        print(f"  wrote {out}/prompt.md (+ system.txt, user.txt)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fixture", default="efcore-mongodb-q1",
                    help=f"fixture name ({', '.join(FIXTURES)}) or a path")
    ap.add_argument("--fixtures", nargs="*", default=None,
                    help="export several fixtures in one go (overrides --fixture)")
    ap.add_argument("--model", default=None, help="AvailableModel value (default: env MODEL / Context default)")
    ap.add_argument("--out", default="../manual-eval", help="output root for the prompt folders")
    ap.add_argument("--env", default="../.env")
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
