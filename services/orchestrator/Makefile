.PHONY: all format lint type_check dev debug test tests test_watch integration_tests docker_tests help extended_tests \
	eval_dataset eval_dataset_dryrun eval_judge_check eval_small eval_full eval_sweep eval_overnight eval_codebleu \
	eval_rejudge eval_node_tokens eval_deliverables

# Default target executed when no arguments are given to make.
all: help

######################
# DEVELOPMENT
######################

ifeq ($(OS),Windows_NT)
install:
	uv sync --all-extras

dev:
	powershell -ExecutionPolicy Bypass -File scripts/load_env.ps1 .env.dev
	langgraph dev --allow-blocking --n-jobs-per-worker 20

debug:
	powershell -ExecutionPolicy Bypass -File scripts/load_env.ps1 .env.dev
	langgraph dev --debug-port 5678 --wait-for-client --allow-blocking --n-jobs-per-worker 20
else
install:
	uv sync --all-extras
	./scripts/load_env.sh
	./scripts/init_daytona_snapshots.sh

dev:
	uv run langgraph dev --allow-blocking --n-jobs-per-worker 20

debug:
	uv run langgraph dev --debug-port 5678 --wait-for-client --allow-blocking --n-jobs-per-worker 20
endif

langgraphics:
	uv run langgraphics-server

mock_server:
	npx @copilotkit/aimock --config aimock.json --port 4020

######################
# TESTS
######################

# Define a variable for the test file path.
TEST_FILE ?= tests/unit_tests/

test:
	python -m pytest $(TEST_FILE)

integration_tests:
	python -m pytest tests/integration_tests 

test_watch:
	python -m ptw --snapshot-update --now . -- -vv tests/unit_tests

test_profile:
	python -m pytest -vv tests/unit_tests/ --profile-svg

extended_tests:
	python -m pytest --only-extended $(TEST_FILE)

# Manual recorder: one long-lived aimock that proxies to e-INFRA and SAVES every unmatched
# request as a fixture under ./tests/aimock/recorded/.
RECORD_FIXTURES_DIR ?= ./tests/aimock
record_requests:
	npx -p @copilotkit/aimock llmock --port 4020 --record --upstream-timeout-ms 300000  --body-timeout-ms 300000 --log-level debug --provider-openai https://llm.ai.e-infra.cz -f $(RECORD_FIXTURES_DIR)

# Integrated recorder: drive the pipeline on a WWI fixture and spawn a FRESH aimock per run, so
# each thread's traffic is saved into its OWN folder under evaluation/aimock/. Needs the live stack
# (e-INFRA, Daytona, WWI DBs) and the orchestrator venv. FIXTURE/APPROACHES override the defaults.
FIXTURE ?= efcore-mongodb-q1
APPROACHES ?= our_approach
record_experiment:
	uv run python evaluation/scripts/run_experiment.py --fixture $(FIXTURE) --approaches $(APPROACHES) \
		--record-fixtures --aimock-root evaluation/aimock --pred-root evaluation/predictions --out evaluation/out --env .env.dev

######################
# EVALUATION (LangSmith-native experiments + LLM judges + deterministic metrics)
######################
# One graph execution per run produces BOTH the LLM-judge scores AND the deterministic metrics
# (funnel/latency/pass@1). Each source->target PAIR is a separate LangSmith Experiment. 
# Needs the LIVE local stack (e-INFRA tunnel, Daytona, WWI DBs) + the eval
# extra (`uv sync --extra eval`). Knobs: JUDGE_MODEL / REPS / CONCURRENCY / VARIANTS / PAIRS.
# The judge is a fallback CHAIN (comma-separated, tried in order per call). deepseek-v4-pro's
# April-2026 knowledge cutoff covers the graded framework APIs (gemma4's 2025 cutoff does not) —
# thinking first for discrimination, non-thinking second for reliability, gemma4 as the terminal
# safety net. The model that produced each verdict lands in the feedback comment + summary JSON.
JUDGE_MODEL ?= einfra/deepseek-v4-pro-thinking,einfra/deepseek-v4-pro,einfra/gemma4
REPS        ?= 10
CONCURRENCY ?= 4
# Cross-experiment work-stealing: all experiments launch concurrently under this many GLOBAL
# pipeline slots, so a draining experiment's idle tail slots are used by the next one.
GLOBAL_CONCURRENCY ?= 4
EVAL_ENV    ?= .env.dev
# Record LLM traffic per run into its own dir under AIMOCK_ROOT (mirrors the predictions tree). On by
# default for the eval runs; set RECORD= to disable.
RECORD      ?= 1
AIMOCK_ROOT ?= evaluation/aimock
RECORD_FLAG := $(if $(RECORD),--record-fixtures --aimock-root $(AIMOCK_ROOT),)

# Build/refresh the bundled per-pair examples in the "UOM Final Experiments" dataset (idempotent).
# All variants are upserted so every eval_* target has examples: the eight 5-query batches
# (batch1-3 = original 15 queries; batch4-8 = extended Query16-40 workload) plus the small gate,
# the bundled 15-query stress arm (full) and the bundled 25-query extended stress arm (xl).
eval_dataset:
	uv run python evaluation/scripts/build_eval_dataset.py --variants small batch1 batch2 batch3 batch4 batch5 batch6 batch7 batch8 full xl --env $(EVAL_ENV)

eval_dataset_dryrun:
	uv run python evaluation/scripts/build_eval_dataset.py --variants small batch1 batch2 batch3 batch4 batch5 batch6 batch7 batch8 full xl --dry-run

# A/B the judge model on the dataset WITHOUT running the graph (echo target) — verify judge
# discrimination + parsing before spending pipeline tokens. Override JUDGE_MODEL to compare.
eval_judge_check:
	uv run python evaluation/scripts/run_langsmith_eval.py --dry-run --judge-model $(JUDGE_MODEL) --env $(EVAL_ENV)

# Re-run ONLY the LLM-as-a-judge evaluators over already-finished experiments (no graph, no
# Daytona, no stores) — reference-aware where frozen refs exist. REJUDGE_CSV is a glob of
# exported experiment CSVs; add REJUDGE_FLAGS='--push' to write *_ref feedback back to LangSmith.
# ⚠ shares the e-INFRA endpoint with live experiments — keep REJUDGE_CONCURRENCY low (default 2).
eval_rejudge:
	uv run python evaluation/scripts/rejudge_experiments.py --csv '$(REJUDGE_CSV)' \
		--judge-concurrency $(REJUDGE_CONCURRENCY) --env $(EVAL_ENV) $(REJUDGE_FLAGS)

REJUDGE_CSV ?= evaluation/traces/10-7-2026/uom-*.csv
REJUDGE_CONCURRENCY ?= 2
REJUDGE_FLAGS ?=

# Fast gate: the small (<=5 query) variant across all pairs, default generate-model.
eval_small:
	EVAL_MODE=1 uv run python evaluation/scripts/run_langsmith_eval.py --variants small \
		--judge-model $(JUDGE_MODEL) --repetitions $(REPS) --max-concurrency $(CONCURRENCY) --global-concurrency $(GLOBAL_CONCURRENCY) \
		--pred-root evaluation/predictions $(RECORD_FLAG) --env $(EVAL_ENV)

# The 15-query workload split into three 5-query batches per pair (the experiment default —
# 5 queries per prompt is the size the pipeline translates reliably).
eval_full:
	EVAL_MODE=1 uv run python evaluation/scripts/run_langsmith_eval.py --variants batch1 batch2 batch3 \
		--judge-model $(JUDGE_MODEL) --repetitions $(REPS) --max-concurrency $(CONCURRENCY) --global-concurrency $(GLOBAL_CONCURRENCY) \
		--pred-root evaluation/predictions $(RECORD_FLAG) --env $(EVAL_ENV)

# The EXTENDED experiment (user shape 2026-07-10): the ENTIRE 40-query workload (original 15 +
# extended Query16-40) bundled into ONE prompt per pair — variant `xl`. Run `make eval_dataset`
# (or `build_eval_dataset.py --variants xl`) first so the xl examples exist.
eval_extended:
	EVAL_MODE=1 uv run python evaluation/scripts/run_langsmith_eval.py --variants xl \
		--judge-model $(JUDGE_MODEL) --repetitions $(REPS) --max-concurrency $(CONCURRENCY) --global-concurrency $(GLOBAL_CONCURRENCY) \
		--pred-root evaluation/predictions $(RECORD_FLAG) --env $(EVAL_ENV)

# All 15 queries bundled into ONE prompt per pair (the query-count stress arm, for comparison).
eval_full_bundled:
	EVAL_MODE=1 uv run python evaluation/scripts/run_langsmith_eval.py --variants full \
		--judge-model $(JUDGE_MODEL) --repetitions $(REPS) --max-concurrency $(CONCURRENCY) --global-concurrency $(GLOBAL_CONCURRENCY) \
		--pred-root evaluation/predictions $(RECORD_FLAG) --env $(EVAL_ENV)

# Opt-in generate_translation_node sweep (default trio: kimi-k2.7 / glm-5.2 / deepseek-v4-pro-thinking).
# SWEEP_GEN_MODELS narrows the swept models (comma-separated einfra/* ids), e.g.
#   make eval_sweep SWEEP_GEN_MODELS="einfra/glm-5.2,einfra/deepseek-v4-pro-thinking"
SWEEP_GEN_MODELS ?=
eval_sweep:
	EVAL_MODE=1 uv run python evaluation/scripts/run_langsmith_eval.py --variants batch1 batch2 batch3 --sweep \
		$(if $(SWEEP_GEN_MODELS),--sweep-models "$(SWEEP_GEN_MODELS)",) \
		--judge-model $(JUDGE_MODEL) --repetitions $(REPS) --max-concurrency $(CONCURRENCY) --global-concurrency $(GLOBAL_CONCURRENCY) \
		--pred-root evaluation/predictions $(RECORD_FLAG) --env $(EVAL_ENV)

# Staged: preflight-gated small variant FIRST, then the three 5-query batches; both default
# generate-model. Logs to evaluation/out/full-experiment-<ts>.log. The runner aborts fast if the
# live stack is unreachable.
eval_full_experiment:
	@mkdir -p evaluation/out
	@ts=$$(date +%Y%m%d-%H%M%S); log=evaluation/out/full-experiment-$$ts.log; \
		echo "full experiment eval -> $$log"; \
		EVAL_MODE=1 uv run python evaluation/scripts/run_langsmith_eval.py --variants full \
			--judge-model $(JUDGE_MODEL) --repetitions $(REPS) --max-concurrency $(CONCURRENCY) --global-concurrency $(GLOBAL_CONCURRENCY) \
			--pred-root evaluation/predictions $(RECORD_FLAG) --env $(EVAL_ENV) 2>&1 | tee $$log

# Post-hoc CodeBLEU (structural similarity — SECONDARY to execution-equivalence pass@k) over the
# predictions the runs wrote, in the eval venv (codebleu + tree-sitter pinned). Step 1 freezes the
# per-VARIANT harness-form references OFFLINE from the first execution-verified (strict 15/15)
# repetition of $(CODEBLEU_REF_TAG) per pair -> evaluation/reference/<dataset>/<variant>/<pair>/
# (+ provenance.json naming the source run so scorers can exclude it from its own arm). Step 2
# scores every prediction against those references -> evaluation/out/codebleu.csv.
eval_codebleu:
	uv run --project evaluation python evaluation/scripts/freeze_reference.py \
		--tag $(CODEBLEU_REF_TAG) --variant $(CODEBLEU_VARIANT) --dataset $(CODEBLEU_DATASET) \
		--expected $(CODEBLEU_EXPECTED)
	uv run --project evaluation python evaluation/scripts/score_predictions.py \
		--pred-root evaluation/predictions --ref-root evaluation/reference \
		--dataset $(CODEBLEU_DATASET) --variant $(CODEBLEU_VARIANT) --out evaluation/out

CODEBLEU_DATASET ?= wwi
# Reference provenance: the run whose execution-verified (strict 15/15) repetitions are frozen
# as the per-variant harness-form references (see freeze_reference.py). Re-freezing is
# idempotent — the first perfect repetition per pair wins.
CODEBLEU_REF_TAG ?= 20260709-150203
CODEBLEU_VARIANT ?= full
CODEBLEU_EXPECTED ?= 15

# Per-node token/time attribution from LangSmith (loop_tokens feeds fig8's fair token bar
# and the per-query heatmap). Read-only API calls; safe alongside live experiments.
eval_node_tokens:
	uv run python evaluation/scripts/harvest_node_tokens.py \
		--traces $(NODE_TOKENS_TRACES) --out evaluation/out/node_tokens.csv --env $(EVAL_ENV)

NODE_TOKENS_TRACES ?= evaluation/traces/10-7-2026

# Assemble the thesis-attachment bundle (copies existing artifacts only; idempotent).
# Add DELIVERABLES_FLAGS='--tag <xl-tag>' after further runs, or '--no-aimock' to slim it.
eval_deliverables:
	uv run python evaluation/scripts/build_deliverables.py --out $(DELIVERABLES_OUT) \
		$(DELIVERABLES_FLAGS)

DELIVERABLES_OUT ?= evaluation/out/deliverables
DELIVERABLES_FLAGS ?=

init_daytona_snaphosts:
	./scripts/init_daytona_snapshots.sh

######################
# LINTING AND FORMATTING
######################

# Define a variable for Python and notebook files.
PYTHON_FILES=src/
MYPY_CACHE=.mypy_cache
lint format: PYTHON_FILES=.
lint_diff format_diff: PYTHON_FILES=$(shell git diff --name-only --diff-filter=d main | grep -E '\.py$$|\.ipynb$$')
lint_package: PYTHON_FILES=src
lint_tests: PYTHON_FILES=tests
lint_tests: MYPY_CACHE=.mypy_cache_test

lint lint_diff lint_package lint_tests:
	python -m ruff check .
	[ "$(PYTHON_FILES)" = "" ] || python -m ruff format $(PYTHON_FILES) --diff
	[ "$(PYTHON_FILES)" = "" ] || python -m ruff check --select I $(PYTHON_FILES)
	[ "$(PYTHON_FILES)" = "" ] || python -m ty check
# 	[ "$(PYTHON_FILES)" = "" ] || python -m mypy --strict $(PYTHON_FILES)
# 	[ "$(PYTHON_FILES)" = "" ] || mkdir -p $(MYPY_CACHE) && python -m mypy --strict $(PYTHON_FILES) --cache-dir $(MYPY_CACHE)

format format_diff:
	ruff format $(PYTHON_FILES)
	ruff check --select I --fix $(PYTHON_FILES)

type_check:
	ty check

spell_check:
	codespell --toml pyproject.toml

spell_fix:
	codespell --toml pyproject.toml -w

make_api_docs:
	pydoc-mintlify build

######################
# HELP
######################

help:
	@echo '----'
	@echo 'install										  - setup development environment and install dependencies'
	@echo 'dev													- start development server'
	@echo 'debug												- start development server in debug mode'
	@echo 'format                       - run code formatters'
	@echo 'type_check                   - run type checker'
	@echo 'lint                         - run linters'
	@echo 'test                         - run unit tests'
	@echo 'tests                        - run unit tests'
	@echo 'test TEST_FILE=<test_file>   - run all tests in file'
	@echo 'test_watch                   - run unit tests in watch mode'
	@echo '----'
	@echo 'eval_dataset                 - build/refresh bundled per-pair examples in the LangSmith dataset'
	@echo 'eval_judge_check             - A/B the judge model (dry-run echo target, no graph)'
	@echo 'eval_small                   - fast gate: small (<=5 query) variant, all pairs'
	@echo 'eval_full                    - 15 queries as three 5-query batches, all pairs, default model'
	@echo 'eval_full_bundled            - all 15 queries in ONE prompt per pair (stress arm)'
	@echo 'eval_sweep                   - full matrix + 4-model generate_translation_node sweep'
	@echo 'eval_overnight               - unattended staged run (small then full), logs to evaluation/out/'
	@echo 'eval_codebleu                - post-hoc CodeBLEU over the predictions tree'

