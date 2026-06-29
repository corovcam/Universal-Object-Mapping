.PHONY: all format lint type_check dev debug test tests test_watch integration_tests docker_tests help extended_tests \
	eval_dataset eval_dataset_dryrun eval_judge_check eval_small eval_full eval_sweep eval_overnight eval_codebleu

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
	npx -p @copilotkit/aimock llmock --port 4020 --record --latency 5 --upstream-timeout-ms 300000  --body-timeout-ms 300000 --log-level debug --provider-openai https://llm.ai.e-infra.cz -f $(RECORD_FIXTURES_DIR)

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
JUDGE_MODEL ?= einfra/gemma4
REPS        ?= 15
CONCURRENCY ?= 2
EVAL_ENV    ?= .env.dev

# Build/refresh the bundled per-pair examples in the "UOM Final Experiments" dataset (idempotent).
eval_dataset:
	uv run python evaluation/scripts/build_eval_dataset.py --env $(EVAL_ENV)

eval_dataset_dryrun:
	uv run python evaluation/scripts/build_eval_dataset.py --dry-run

# A/B the judge model on the dataset WITHOUT running the graph (echo target) — verify judge
# discrimination + parsing before spending pipeline tokens. Override JUDGE_MODEL to compare.
eval_judge_check:
	uv run python evaluation/scripts/run_langsmith_eval.py --dry-run --judge-model $(JUDGE_MODEL) --env $(EVAL_ENV)

# Fast gate: the small (<=5 query) variant across all pairs, default generate-model.
eval_small:
	EVAL_MODE=1 uv run python evaluation/scripts/run_langsmith_eval.py --variants small \
		--judge-model $(JUDGE_MODEL) --repetitions $(REPS) --max-concurrency $(CONCURRENCY) \
		--pred-root evaluation/predictions --env $(EVAL_ENV)

# Full ~15-query matrix across all pairs, default generate-model.
eval_full:
	EVAL_MODE=1 uv run python evaluation/scripts/run_langsmith_eval.py --variants full \
		--judge-model $(JUDGE_MODEL) --repetitions $(REPS) --max-concurrency $(CONCURRENCY) \
		--pred-root evaluation/predictions --env $(EVAL_ENV)

# Opt-in 4-model generate_translation_node sweep (qwen3.5 / kimi-k2.7 / glm-5.2 / deepseek-v4-pro-thinking).
eval_sweep:
	EVAL_MODE=1 uv run python evaluation/scripts/run_langsmith_eval.py --variants full --sweep \
		--judge-model $(JUDGE_MODEL) --repetitions $(REPS) --max-concurrency $(CONCURRENCY) \
		--pred-root evaluation/predictions --env $(EVAL_ENV)

# Staged: preflight-gated small variant FIRST, then the full matrix; both default generate-model.
# Logs to evaluation/out/full-experiment-<ts>.log. The runner aborts fast if the live stack is unreachable.
eval_full_experiment:
	@mkdir -p evaluation/out
	@ts=$$(date +%Y%m%d-%H%M%S); log=evaluation/out/full-experiment-$$ts.log; \
		echo "full experiment eval -> $$log"; \
		EVAL_MODE=1 uv run python evaluation/scripts/run_langsmith_eval.py --variants small full \
			--judge-model $(JUDGE_MODEL) --repetitions $(REPS) --max-concurrency $(CONCURRENCY) \
			--pred-root evaluation/predictions --env $(EVAL_ENV) 2>&1 | tee $$log

# Post-hoc CodeBLEU over the predictions the runs wrote (separate eval venv with codebleu pinned).
eval_codebleu:
	uv run --project evaluation python evaluation/scripts/extract_predictions.py --reference --pred-root evaluation/predictions
	uv run --project evaluation python evaluation/scripts/score_predictions.py --pred-root evaluation/predictions

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
	@echo 'eval_full                    - full ~15-query matrix, all pairs, default model'
	@echo 'eval_sweep                   - full matrix + 4-model generate_translation_node sweep'
	@echo 'eval_overnight               - unattended staged run (small then full), logs to evaluation/out/'
	@echo 'eval_codebleu                - post-hoc CodeBLEU over the predictions tree'

