.PHONY: all format lint type_check dev debug test tests test_watch integration_tests docker_tests help extended_tests

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
	langgraph dev --allow-blocking

debug:
	powershell -ExecutionPolicy Bypass -File scripts/load_env.ps1 .env.dev
	langgraph dev --debug-port 5678 --wait-for-client --allow-blocking
else
install:
	uv sync --all-extras
	./scripts/setup_env.sh
	./scripts/install_logdy.sh

dev:
	langgraph dev --allow-blocking

debug:
	langgraph dev --debug-port 5678 --wait-for-client --allow-blocking
endif

mock_server:
	npx -p @copilotkit/aimock --config aimock.json --port 4010

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

record_requests:
	npx -p @copilotkit/aimock llmock --record --watch --upstream-timeout-ms 300000  --body-timeout-ms 300000 --log-level debug --provider-openai https://llm.ai.e-infra.cz -f ./tests/aimock/
# 	node ../../../aimock/dist/cli.js --record --watch --upstream-timeout-ms 300000  --body-timeout-ms 300000 --log-level debug --provider-openai https://llm.ai.e-infra.cz -f ./tests/aimock

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

