# Evaluation scripts — runnable workflow (WideWorldImporters)

These three scripts turn the orchestrator's **LangSmith** traces into the thesis metrics. They run
against a **separate venv** so the service env is untouched:

```bash
uv venv evaluation/.venv-eval --python 3.12
uv pip install --python evaluation/.venv-eval -r evaluation/eval-requirements.txt
```

`LANGSMITH_API_KEY` / `LANGSMITH_PROJECT` / `LANGSMITH_ENDPOINT` are read from `../.env.dev`.

## 1. `aggregate_traces.py` — E1 funnel + E4 internal stats + verifier confusion matrix

```bash
.venv-eval/bin/python scripts/aggregate_traces.py --limit 50 --env ../.env.dev --out ./out --stratify
```

Reconstructs, per run (root span `Universal Object Mapping Translator`), from the **current**
post-finalize-split graph — not the old structured-output contract:

- **E1 funnel**: extract → schema_inspection → generate → compiled/executed → equivalent → accepted,
  as node-reached + per-query equivalence (no text-scraping of ACCEPT/REJECT for the funnel).
- **E4 per-node cost**: wall-clock per node (summed chain spans) + tokens attributed to the nearest
  node-named ancestor of each `ChatLiteLLM` span. *Finding on current WWI runs: `validate_query_node`
  (Daytona sandbox compile+exec) takes the largest **share of node time** (~60% of summed node time,
  not of e2e — there is un-attributed gap time between spans), while `generate_translation_node`
  dominates tokens — the time bottleneck and the token bottleneck are different nodes.*
- **Computational accuracy (headline functional metric)**: pass@1 = fraction of queries whose
  execution output is equivalent (`[Query Equivalence Results]` → all `Equivalent`).
- **Judge-vs-execution confusion matrix** (precision/recall/accuracy/FAR/FRR): the LLM judge's
  ACCEPT/REJECT (read from the **last `evaluation_node` span's real verdict**, not "finalize
  reached") classifies against the execution-equivalence ground-truth label. Only runs with a
  **definite verdict** (ACCEPT/REJECT) *and* an equivalence label are counted, so schema-only
  auto-accepts, error verdicts, and in-progress/aborted traces don't masquerade as decisions.

> This replaces E2 (fault-injection mutants) as the source of precision/recall — the generator is
> fixed, so precision/recall come from judge-vs-execution-equivalence on real runs instead of a
> synthetic mutant confusion matrix.

## 2. `extract_predictions.py` — harvest finalize artifacts (E3 step 1)

```bash
# predictions from every accepted run:
.venv-eval/bin/python scripts/extract_predictions.py --limit 50 --env ../.env.dev --root ../predictions
# freeze ONE manually-reviewed accepted run as the CodeBLEU baseline for its (dataset, pair):
.venv-eval/bin/python scripts/extract_predictions.py --limit 1 --env ../.env.dev --reference --root ../reference
# offline, from a LangGraph run export (lacks the pair → pass it):
.venv-eval/bin/python scripts/extract_predictions.py --from-export '../../run-*.json' --pair efcore->mongo --lang java --root ../predictions
```

Writes `translated_schema_code` / `translated_query_code` as
`<root>/<dataset>/<pair>/<model>/<run_id>/{schema,queries}.<ext>` (predictions) or
`<root>/<dataset>/<pair>/{schema,queries}.<ext>` (`--reference`, the frozen baseline).

## 3. `score_predictions.py` — CodeBLEU vs the frozen reference (E3 step 2)

```bash
.venv-eval/bin/python scripts/score_predictions.py --pred-root ../predictions --ref-root ../reference --out ./out
```

Per artifact: CodeBLEU **with its 4-component breakdown** (ngram / weighted-ngram / syntax /
dataflow) + normalized-exact + token-overlap.

> **CodeBLEU is secondary, reported with a caveat.** Verified empirically here: CodeBLEU scores an
> *identical* file as low as **0.66** because its `dataflow_match` component degenerates to 0 and
> `ngram_match` collapses on some inputs (syntax_match stays 1.0). It cannot self-score to 1.0, so
> it is a structural-similarity signal only — **lead conclusions with computational accuracy
> (execution-equivalence pass@1)**, not CodeBLEU. The component columns make the degeneracy visible.

## 4. `run_experiment.py` — our-approach vs single-pass baseline (E7 / 2a)

Runs the **same graph** twice on one WWI fixture and writes finalize artifacts + run-time metrics:

```bash
# needs the LIVE stack (e-INFRA model, Daytona, WWI DBs) and the ORCHESTRATOR venv (.venv), not .venv-eval
.venv/bin/python evaluation/scripts/run_experiment.py --fixture efcore-mongodb-q1 \
    --approaches baseline our_approach --pred-root evaluation/predictions --out evaluation/out
```

- **baseline** = `single_pass=True`: one direct model call (system + human prompt, save tool only,
  **no docs MCP, no ReAct loop**), then the SAME deterministic assemble → validate → finalize, with
  **no self-repair retry and no human hand-off** (failure terminates). The only difference from
  our-approach is the agentic loop, so the comparison isolates its value.
- **our_approach** = the full agentic loop (current default).

The `single_pass` flag is a state field (set at invoke); the validation routers
(`route_post_translation` / `route_post_schema_validation` / `route_post_evaluation`) read it and
route to `__end__` instead of looping/escalating. Both arms still finalize on ACCEPT → identical
clean-code artifacts, so `extract_predictions` / `score_predictions` / `aggregate_traces` score them
the same way. Writes `experiment-<fixture>.json` (latency, loops, accepted, compile_pass, pass@1)
and predictions under `<pred-root>/<dataset>/<pair>/<model>/<approach>-<run_id>/`. **Token/funnel/
per-node cost come from `aggregate_traces.py`** over the LangSmith traces these runs emit (each is
stamped with `metadata.approach` for joining).

Fixtures (all WideWorldImporters): `dapper-mongodb`, `efcore-mongodb`, `efcore-mongodb-q1`,
`efcore-neo4j`, `nhibernate-mongodb` (in `tests/fixtures/`).

### Recording each run's LLM traffic (`--record-fixtures`)

Add `--record-fixtures` and every run spawns its OWN throwaway aimock (`aimock_recorder.py`) that
proxies to e-INFRA and **saves** the run's LLM traffic into its own folder, so threads never mingle:

```bash
.venv/bin/python evaluation/scripts/run_experiment.py --fixture efcore-mongodb-q1 \
    --approaches our_approach --record-fixtures --aimock-root evaluation/aimock
# or: make record_experiment FIXTURE=efcore-mongodb-q1 APPROACHES=our_approach
```

Per-run captures land in `evaluation/aimock/<dataset>/<fixture>__<approach>__<timestamp>/recorded/`
(the `recorded/` segment is appended by aimock). The runner points that run's `Context.openai_api_url`
at the instance (so `get_model` routes through it) and keeps the real `OPENAI_API_KEY` — aimock
forwards auth upstream and **strips it from saved fixtures**, so no secret lands on disk.

> **`--record` saves; `--record --proxy-only` saves NOTHING.** aimock's `persistFixture` early-returns
> when `proxyOnly` is set — the two flags together (the old Makefile `record_requests`) recorded
> nothing. We pass `--record` alone. The one tradeoff: an *identical* request recurring within a run
> replays aimock's in-memory cache instead of re-hitting e-INFRA (distinct prompts never trigger it;
> only an exact retry would) — harmless for recording, and the reason proxy-only can't also save.
> **Port note:** the einfra path does `openai_api_url.rstrip("/v1")` (a char-set strip), so a port
> ending in `1` is mangled — `aimock_recorder` only ever picks ports whose last digit isn't `1`.

## 5. `export_manual_prompts.py` — copy-pasteable prompt for MANUAL SOTA-model baselines

Proprietary SOTA models (Claude, GPT, Gemini) are only reachable here through chat UIs / CLIs (Claude
Code, Claude.ai, Gemini app, Google AI Studio, Antigravity), not API keys. This emits the **exact**
translation-stage system + user prompt for a fixture so the baseline can be run by hand:

```bash
.venv/bin/python evaluation/scripts/export_manual_prompts.py --fixture efcore-mongodb-q1 \
    --out evaluation/manual-eval --env .env.dev
```

It drives the real graph with `interrupt_before=["generate_translation_node"]` — so live
`extract_input` + `schema_inspection` populate the State — then renders with the SAME
`build_system_prompt` / `build_translation_user_message` the node uses (single source of truth in
`react_agent/prompts.py`). What you paste is byte-for-byte what the pipeline sends its own model. It
stops **before** the translation model call, so it spends no SOTA tokens and never touches the
proprietary models (it does need the live stack for extract_input/schema_inspection).

Per fixture, under `<out>/wwi/<fixture>__<timestamp>/`: `system.txt`, `user.txt` (raw, cleanest to
copy), and `prompt.md` (both + per-platform paste instructions + a manual-run adaptation that turns
the `save_translation` tool-call into two labeled `*_validation_body` code blocks + an output-capture
template). See `evaluation/manual-eval/SAMPLE/` for an illustrative render. Capture each model's two
bodies and assemble→validate→finalize them through the same pipeline for an apples-to-apples score.

**Gate the FIRST live baseline run** (the one path not testable without infra): open its LangSmith
trace and confirm **exactly one `generate_translation_node` span and zero docs-MCP tool calls**.
`translation_loops==1` alone does not prove single-pass — a full-loop run that succeeds on the first
try is also 1. If the baseline shows research/docs spans or multiple generation spans, the
`single_pass` channel didn't propagate and the baseline silently ran the full loop.

**Known asymmetry (held constant):** the baseline's single generation call uses `reasoning=True`
to match our-approach's generation agent, so the ablation isolates the **tools + self-repair loop**,
not reasoning mode. (`temperature=0` on the baseline call for reproducibility; our-approach's agent
uses the default — a minor, documented difference.)

**On baseline funnels:** `aggregate_traces` treats a single-pass run that ends without finalizing as
a **decided `failed`** outcome (not excluded `incomplete`), so the baseline's characteristic
early-failures stay in the funnel denominator. It reads `metadata.single_pass`/`metadata.approach`
stamped by this runner.

## 6. `run_langsmith_eval.py` — UNIFIED LangSmith experiment (judges + deterministic metrics)

Runs the graph over the **"UOM Final Experiments"** dataset (ID `56708f08-2697-4af2-b3b7-9172c0e68b4b`)
via LangSmith's `aevaluate`, so results land as proper **Experiments** with per-example feedback in the
UI. **The two eval suites are joined:** each example runs the pipeline **ONCE** (via the shared
`run_experiment.run_one`), and that single run feeds BOTH the LLM judges (grade the translated code)
AND cheap **non-LLM evaluators** that surface the deterministic metrics (`accepted`, `compile_pass`,
`pass_at_1`, `translation_loops`, `wall_clock_s`, …) — so the provider is **not hit twice**. It also
writes prediction artifacts for the post-hoc CodeBLEU pass. Needs the ORCHESTRATOR venv with the `eval`
extra (`uv sync --extra eval`) and the live stack.

**One Experiment per source→target PAIR.** Examples are tagged `metadata.{pair,variant}` (see §7);
the runner filters per pair client-side and calls `aevaluate` once per `(variant, pair, generate-model)`.
`--repetitions 15` realises "15 iterations" per pair; `--max-concurrency 2` is the parallelism.

```bash
# A/B the judge model with an echo target (no graph/Daytona) BEFORE spending pipeline tokens:
uv run python evaluation/scripts/run_langsmith_eval.py --dry-run --judge-model einfra/gemma4 --env .env.dev
# fast gate: small (<=5 query) variant, all pairs, default generate-model:
make eval_small          # (or: run_langsmith_eval.py --variants small ...)
# full ~15-query matrix, all pairs:
make eval_full
# opt-in 4-model generate_translation_node sweep:
make eval_sweep
```

- **Staging / sweep:** `--variants small full` runs the small gate first then the full matrix.
  `--sweep` adds the 4 generate-models (`qwen3.5` / `kimi-k2.7` / `glm-5.2` / `deepseek-v4-pro-thinking`)
  — opt-in, off by default. The generate-model is forced via `Context.translation_model_override`
  (set per-invoke, never a global, so concurrent runs don't race). NB: `glm-5.2`'s `model_profiles`
  extra_body forces thinking on, so its "non-reasoning" sweep arm may still think (flagged, not fixed).
- **Preflight** (on by default; `--no-preflight` to skip): a stdlib-socket TCP liveness check of the
  model endpoint, Daytona, MSSQL, MongoDB, Neo4j BEFORE submitting, so a misfire fails fast instead of
  producing a night of errored runs.
- **Reference-free judges (graded against the SOURCE):** `code_correctness`, `conciseness`,
  `hallucination` (source as `context`), and custom `translation_equivalence`. No gold reference exists;
  for reference-based CodeBLEU use the frozen pair reference (`extract_predictions.py --reference` +
  `score_predictions.py`). No first-accepted-as-reference judge — incoherent across *different* queries.
- **Judge model:** e-INFRA (no proprietary keys). Default **`einfra/gemma4`** (non-thinking, 32k out).
  The old `llama-4-scout` default is actually `redhatai-scout` capped at `max_tokens: 50` → it
  TRUNCATED every verdict; thinking models (deepseek-v4-pro-thinking / gpt-oss / qwen-coder) HANG the
  structured-output path on long grading prompts — avoid both as judges. openevals' own scorer also
  hangs, so we keep openevals' **prompts** but call ourselves (`with_structured_output` →
  JSON-fallback → graceful `None`, per-judge timeout) with `score` declared before `reasoning`.
  **Spot-check a couple of judge comments on the first real run** to confirm discrimination on real
  (long) translations — `--dry-run` only proves the call path against a stub.

### Run full experiment
`make eval_full_experiment` runs the preflight-gated **small gate then full matrix**, exports
`EVAL_MODE=1` (per-run cache-bust header at the TOP of every system prompt to defeat e-INFRA
prompt/KV caching), and tees to `evaluation/out/full-experiment-<ts>.log`. Schedule it with `at` or a
systemd timer, e.g.:

```bash
# one-shot at 1am (keep the shell/tunnel/Daytona up):
echo 'cd /…/services/orchestrator && make eval_full_experiment' | at 01:00
# or a systemd-timer / cron entry calling the same `make eval_full_experiment`.
```

## 7. `build_eval_dataset.py` — benchmark→dataset harvester (generalization queries)

Generates the bundled per-pair examples in "UOM Final Experiments". The ~15 queries are derived from the
`.NET` ORM `benchmarks/` (EFCore LINQ / Dapper SQL / NHibernate LINQ-over-ISession) spanning the
benchmark categories (selection, range, IN, text, paging, grouped aggregation, relationships, sorting,
distinct, projection, compound filter) over the self-contained 4-entity WWI subset — so the **full
schema is sent once per prompt** (the "bundle per pair" decision; no per-query entity-subset assembly).
Six pairs × {`small` (first 5 queries), `full` (~15)} = 12 examples, each tagged
`metadata.{pair,variant,source_fw,target_fw}`. **Idempotent** (keyed by `(pair,variant)` → updates,
not duplicates).

```bash
uv run python evaluation/scripts/build_eval_dataset.py --dry-run          # print prompts, no upload
uv run python evaluation/scripts/build_eval_dataset.py --env .env.dev         # upsert for real
make eval_dataset                                                          # same, via Makefile
```

## Notes
- The funnel runs over **query-bearing decided runs** (`translation_type` in query/both that reached
  a pipeline terminal); incomplete/in-progress traces are excluded and schema-only/other-path accepts
  are reported separately, so every conditional rate is a real `P(pass | reached previous)`.
- `--dataset` is a **label only** (default `wwi`); it does not filter the LangSmith project. If
  multiple datasets share one project, run per-dataset and tag, or add a metadata filter.
- `metrics.py` holds the reusable comparators (normalized-exact, token-overlap, codebleu wrapper,
  execution-equivalence on `{count, firstSample, lastSample}`).
- `fault_injection.py` is the old E2 skeleton — **superseded/skipped** (generator is fixed; precision
  /recall now come from §1's judge-vs-execution matrix). Kept for reference only.
- CodeBLEU deps are **version-pinned** (`eval-requirements.txt`): unpinning breaks with
  "Incompatible Language version" / "an integer is required" (tree-sitter ABI mismatch).
