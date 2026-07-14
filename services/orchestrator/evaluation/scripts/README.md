# Evaluation scripts — runnable workflow (WideWorldImporters)

These scripts turn the orchestrator's **LangSmith** experiments into the thesis metrics. They run in
a **separate uv project** (`evaluation/`, its own `.venv` with the heavy CodeBLEU/tree-sitter/
matplotlib deps pinned) so the service env is untouched — invoke everything with
`uv run --project evaluation python evaluation/scripts/<script>.py`. Keys (`LANGSMITH_*`,
`OPENAI_*`) come from `../.env`; the live-stack Daytona/DB knobs from `../.env.dev`.

## Workflow at a glance

1. **`build_eval_dataset.py`** → upsert the per-pair examples into the "UOM Final Experiments" dataset.
2. **`run_langsmith_eval.py`** → run the graph over the dataset as LangSmith Experiments (LLM judges +
   deterministic metrics in one pass); or `run_experiment.py` for the single-pass-vs-loop ablation.
3. **`fetch_experiments.py`** → download a set of experiments (by `run_tag`) to local CSVs.
4. **`aggregate_results.py`** / **`plot_results.py`** → per-pair + cross-batch tables, pass@k, and
   matplotlib charts (the thesis numbers).
5. **`extract_predictions.py`** + **`score_predictions.py`** → post-hoc CodeBLEU (secondary metric).
6. **`export_manual_prompts.py`** → **`score_external.py`** (or one-shot **`claude_arm.sh`**) →
   the closed "vs SOTA harness" loop: byte-identical prompt out, external answer validated back
   through the pipeline's own sandbox gauntlet.

`aggregate_traces.py` (LangSmith-trace funnel/per-node-cost) and `metrics.py` / `aimock_recorder.py`
are shared libraries used by the above. Detailed per-script docs follow.

## 1. `aggregate_traces.py` — E1 funnel + E4 internal stats + verifier confusion matrix

```bash
uv run --project evaluation python evaluation/scripts/aggregate_traces.py --limit 50 --env ../.env.dev --out ./out --stratify
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
uv run --project evaluation python evaluation/scripts/extract_predictions.py --limit 50 --env ../.env.dev --root ../predictions
# freeze ONE manually-reviewed accepted run as the CodeBLEU baseline for its (dataset, pair):
uv run --project evaluation python evaluation/scripts/extract_predictions.py --limit 1 --env ../.env.dev --reference --root ../reference
# offline, from a LangGraph run export (lacks the pair → pass it):
uv run --project evaluation python evaluation/scripts/extract_predictions.py --from-export '../../run-*.json' --pair efcore->mongo --lang java --root ../predictions
```

Writes `translated_schema_code` / `translated_query_code` as
`<root>/<dataset>/<pair>/<model>/<run_id>/{schema,queries}.<ext>` (predictions) or
`<root>/<dataset>/<pair>/{schema,queries}.<ext>` (`--reference`, the frozen baseline).

## 3. `score_predictions.py` — CodeBLEU vs the frozen reference (E3 step 2)

```bash
uv run --project evaluation python evaluation/scripts/score_predictions.py --pred-root ../predictions --ref-root ../reference --out ./out
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
uv run python evaluation/scripts/run_experiment.py --fixture efcore-mongodb-q1 \
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
uv run python evaluation/scripts/run_experiment.py --fixture efcore-mongodb-q1 \
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
uv run python evaluation/scripts/export_manual_prompts.py --fixture efcore-mongodb-q1 \
    --out evaluation/manual-eval --env .env.dev
```

It drives the real graph with `interrupt_before=["generate_translation_node"]` — so live
`extract_input` + `schema_inspection` populate the State — then renders with the SAME
`build_system_prompt` / `build_translation_user_message` the node uses (single source of truth in
`react_agent/prompts.py`). What you paste is byte-for-byte what the pipeline sends its own model. It
stops **before** the translation model call, so it spends no SOTA tokens and never touches the
proprietary models (it does need the live stack for extract_input/schema_inspection).

Per export, under `<out>/wwi/<name>__<timestamp>/`: `system.txt`, `user.txt`, `adaptation.txt`
(the no-tools rewrite of the save-tool contract), `prompt.md` (everything + per-platform paste
instructions), and — in fragment mode — a pre-labeled `capture.md` template with one fenced block
per required piece.

**Experiment-workload mode (the comparison arm):** `--pair <source>-<target> --variant full`
exports the SAME bundled 15-query prompt the LangSmith dataset examples carry (built by
`build_eval_dataset.build_prompt`), so the external harness answers the identical task the
pipeline is scored on:

```bash
uv run python evaluation/scripts/export_manual_prompts.py --pair dapper-mongodb --variant full \
    --out evaluation/manual-eval --env .env
```

### 5b. `score_external.py` + `claude_arm.sh` — the closed "vs SOTA harness" loop

`score_external.py` validates a captured external answer with the pipeline's own gauntlet — the
same `assemble_query_harness`, the same Daytona sandboxes, the same per-query execution
equivalence — and emits the same metrics row (`passed`, `compile_pass`,
`queries_expected/claimed/accepted`, `query_accuracy`, verdicts) plus a predictions-tree entry
(CodeBLEU-comparable). Deterministic equivalence IS acceptance in this arm (no judge) — the same
strict standard as the pipeline's `passed`.

```bash
uv run python evaluation/scripts/score_external.py \
    --capture evaluation/manual-eval/wwi/dapper-mongodb__full__<ts>/capture.md \
    --pair dapper-mongodb --variant full --approach claude_code --model-label claude-opus-4-8
```

Outputs: `evaluation/out/external/<approach>/<pair>__<variant>__<ts>/result.json` (+ sandbox logs
+ assembled harnesses), one appended row in `evaluation/out/external/<approach>/results.csv`, and
predictions under `evaluation/predictions/wwi/external-<approach>/…`.

`claude_arm.sh` automates the whole arm for Claude Code (export → headless `claude -p` with
`--tools ""` chat mode, CWD isolated to the export folder so no repo context leaks → capture →
score). **It spends Claude tokens** — run it deliberately, one pair at a time:

```bash
evaluation/scripts/claude_arm.sh dapper-mongodb full claude-opus-4-8
```

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
  model endpoint, Daytona, MSSQL, MongoDB, Neo4j BEFORE submitting, so a misfire fails fast.
- **Fixture recording** (`--record-fixtures`, **on by default for the `make eval_*` targets** via
  `RECORD=1`; set `RECORD=` to disable): every run spawns its OWN throwaway aimock (`aimock_recorder.py`,
  auto-picked free port → concurrency-safe) that proxies to e-INFRA and SAVES the run's LLM traffic to
  its own dir at `evaluation/aimock/<dataset>/<run_tag>/<pair>/<gen_model>/<approach>-<uuid>/recorded/`
  — the SAME layout the predictions tree uses, so a run's fixtures and predictions sit in parallel
  trees and never mingle across runs. The real `OPENAI_API_KEY` is forwarded upstream and stripped from
  saved fixtures (no secret on disk). Override the base dir with `AIMOCK_ROOT=…` (make) or
  `--aimock-root` (script). eval_mode's per-run cache-bust header keeps every prompt distinct, so
  aimock's in-memory replay cache never short-circuits a recording.
- **Reference-free, SCAFFOLD-AWARE, GRADED judges (against the SOURCE):** `code_correctness`,
  `conciseness`, `faithfulness` (replaces the old inverted-polarity `hallucination`), and
  `translation_equivalence`. Each returns a **fraction in [0,1]** = the proportion of the translation
  satisfying the criterion — NOT a boolean. Why: the target the judge grades is instrumented (each
  query wrapped in a `count`/`firstSample`/`lastSample` probe harness + boilerplate) and bundles up to
  15 queries; the old boolean prompts read the probe wrapper as "invented" AND failed the whole bundle
  on any single flaw, so they rejected 100% of runs (verified). The graded, look-through-the-harness
  prompts TRACK the deterministic per-query accuracy (a 13/15 run scores ~0.8, not 0). Verified live
  against execution-equivalence: not-always-reject ✓, discriminates good/bad ✓. Also optional
  CodeBLEU-in-run (`codebleu_schema`/`_queries`/`codebleu`) rides the same run when a reference exists.
- **CodeBLEU** stays available as the post-hoc structural signal too (`extract_predictions.py
  --reference` / `--from-predictions` + `score_predictions.py`). No first-accepted-as-reference judge.
- **Judge model:** e-INFRA (no proprietary keys). Verified tradeoff (both live-tested on the 35KB
  harness prompts): **`einfra/gemma4`** (non-thinking) is perfectly reliable (0 `None`) and separates a
  real translation from an empty one, but is coarser (missed a subtle single-query corruption);
  **`einfra/kimi-k2.7`** (thinking) discriminates finer (catches the corruption) but its
  structured-output path is slow → some `None` under concurrency (graceful; aggregate skips None). Pick
  via `--judge-model`. The call is ours (`with_structured_output` → JSON-fallback → graceful `None`,
  per-judge timeout, `score` before `reasoning`); `--dry-run` proves only the call path, so trust the
  live judge-vs-equivalence agreement in `aggregate_results.py` over a stub spot-check.

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

## 6b. `fetch_experiments.py` + `aggregate_results.py` + `plot_results.py` — download, tables, charts

LangSmith's UI shows ONE experiment at a time and exports one CSV at a time; when the 15-query
workload runs as three 5-query batches, each pair is 3 separate experiments and the UI never shows the
pair's aggregate. `fetch_experiments.py` pulls a whole SET down (READ-ONLY) in the UI-export CSV
schema; the aggregator stitches them:

```bash
# list every experiment in the dataset (start / run_tag / variant / model / judge / reps):
uv run --project evaluation python evaluation/scripts/fetch_experiments.py --list --env ../.env
# download all experiments of one run (one CSV per experiment):
uv run --project evaluation python evaluation/scripts/fetch_experiments.py \
    --run-tag 20260705-231626 --out evaluation/traces/final-experiments/B --env ../.env
# per-pair + overall table, pass@1/2/3 (Chen et al. unbiased), judge-vs-equivalence agreement
# (--pair-from-name reads the pair from each CSV's experiment name; batch CSVs of a pair combine):
uv run --project evaluation python evaluation/scripts/aggregate_results.py \
    --root evaluation/traces/final-experiments/B --out evaluation/out/final/B --pair-from-name
# matplotlib figures (pass@k, funnel, per-query equivalence/accuracy, judge-vs-truth, latency, overview):
uv run --project evaluation python evaluation/scripts/plot_results.py \
    --root evaluation/traces/final-experiments/B --out evaluation/out/final/B/charts --pair-from-name
```

Everything is built on the corrected **`passed`** metric (compiled/ran AND every demanded query
execution-equivalent), NOT the pipeline's inflated `accepted` flag, and is robust across metric-schema
eras (older runs lack `queries_accepted`/`query_accuracy` → it falls back to `queries_equivalent`).
`pass@k` is reported at the run level and, when `query_verdicts` is present, per query. The judge table
shows each graded judge's mean score on passed vs failed runs + its correlation with the
execution-equivalence rate — the diagnostic that exposes an always-reject (no pass/fail separation) or
inverted-polarity (negative corr) judge. The final thesis analysis lives in `evaluation/out/final/`
(see `FINAL-REPORT.md` there).

## CodeBLEU end-to-end (`make eval_codebleu`)

```bash
make eval_codebleu   # step 1 bootstraps a frozen per-pair reference OFFLINE from the predictions tree
                     # (extract_predictions.py --from-predictions; keeps any hand-pinned reference),
                     # step 2 scores every prediction against it -> evaluation/out/codebleu.csv
```

`score_predictions.py` is layout-robust (reads the pair off the `__` path component, so the
`<dataset>/<run_tag>/<pair>/…` tree works). CodeBLEU is a SECONDARY structural signal (schema ≈0.9,
queries ≈0.4 due to probe-form variance); execution-equivalence pass@k is the headline.

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
- Precision/recall come from the judge-vs-execution-equivalence agreement (§1 and the judge table in
  §6b), not synthetic fault-injection mutants (the generator is fixed).
- CodeBLEU deps are **version-pinned** (`evaluation/pyproject.toml`): unpinning breaks with
  "Incompatible Language version" / "an integer is required" (tree-sitter ABI mismatch).
