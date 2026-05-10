.PHONY: default install lint format check fix ci-format ci-lint clean

PYTHON ?= python3
VENV_BIN ?= .venv/bin
RUFF ?= $(VENV_BIN)/ruff
PRECOMMIT ?= $(VENV_BIN)/pre-commit
UV_LINK_MODE ?= copy

export UV_LINK_MODE

default: install

## Setup ########################################################################

install:  ## Create virtualenv and install dev dependencies
	test -d .venv || uv venv
	uv pip install -r requirements-dev.txt
	test -f .git/hooks/pre-commit || $(PRECOMMIT) install

venv:  ## Create virtualenv only
	uv venv

## Quality ######################################################################

lint:  ## Run ruff linter (read-only)
	$(RUFF) check .

format:  ## Format all Python files in place
	$(RUFF) format .

check: lint format-check  ## Full quality check (no write)

fix:  ## Auto-fix all lint issues + format in place
	$(RUFF) check --fix .
	$(RUFF) format .

format-check:  ## Verify formatting (CI use)
	$(RUFF) format --check .

pre-commit:  ## Run all pre-commit hooks on all files
	$(PRECOMMIT) run --all-files

## CI ###########################################################################

ci-lint:  ## CI: lint with sarif output
	$(RUFF) check --output-format sarif .

ci-format:  ## CI: check formatting
	$(RUFF) format --check .

## Cleanup ######################################################################

clean:  ## Remove virtualenv and cache directories
	rm -rf .venv venv
	rm -rf __pycache__ **/__pycache__
	rm -rf .ruff_cache
	rm -rf .mypy_cache .pytest_cache
	rm -rf .jules

## Help #########################################################################

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
