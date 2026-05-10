# Credit Card Advisor — AGENTS.md

This file provides context for AI coding agents (Jules) working on this project.

## Project Overview

A Home Assistant custom component (`custom_components/credit_advisor/`) that helps users decide which credit card to use for purchases and track benefit usage. Privacy-first — all data stored locally on the user's HA instance.

## Tech Stack

- **Platform:** Home Assistant (2024.12+, Python 3.12)
- **Storage:** YAML files in `[HA_CONFIG]/credit_advisor/`
- **LLM:** OpenRouter REST API (configurable model)
- **Frontend:** Native Lovelace cards (no custom JS for MVP)
- **HTTP:** aiohttp (HA-native async HTTP)
- **No external databases, ORMs, or frameworks**

## Architecture

```
custom_components/credit_advisor/
├── __init__.py       → Component setup, service registration
├── const.py          → Constants, domain, attributes
├── manifest.json     → HA manifest (version, requirements)
├── card_registry.py  → Card CRUD, YAML I/O
├── benefit_tracker.py → Usage tracking, expiry calc, annual rollup
├── llm_client.py     → OpenRouter calls, prompt building
├── sensors.py        → Sensor entities for dashboard/automations
```

## Development Rules

### Required Tooling
- **Ruff** (v0.11.6) — all linting and formatting. NO other formatters/linters.
- **uv** — for virtualenv and dependency management.
- **Makefile** targets: `make lint`, `make format`, `make check`, `make fix`
- **Pre-commit** hooks run on commit: ruff --fix, ruff-format, check-yaml, trailing-whitespace, end-of-file-fixer

### Style
- Line length: 100
- Quotes: double quotes (PEP 8 with ruff default)
- Imports: standard library → third-party → custom_components (isort managed by ruff)
- Logging: always via `_LOGGER` (module-level logger), never `print()`
- Type hints: required for all function signatures (HA convention)
- No stub files or type comments — inline annotations only

### File Conventions
- All custom component files live under `custom_components/credit_advisor/`
- Card YAML files go in `[HA_CONFIG]/credit_advisor/cards/`
- Benefit usage YAML goes in `[HA_CONFIG]/credit_advisor/benefits/`
- Use `yaml.safe_dump` with `default_flow_style=False, sort_keys=False`
- Use `aiohttp` for all HTTP calls (HA-native)

### Service API
Register services via `hass.services.async_register`:
- `credit_advisor.query` — takes `text` string, returns LLM recommendation
- `credit_advisor.add_card` — takes `card_name` string, researches via LLM, saves YAML
- `credit_advisor.log_benefit_usage` — (Phase 2) logs benefit period usage
- `credit_advisor.refresh_benefits` — (Phase 2) weekly LLM check for benefit changes

### Sensor Platform
- Expose `sensor.credit_advisor_response` for the LLM query result
- Phase 2: `sensor.credit_benefit_expiring`, `sensor.credit_benefit_unused`, `sensor.credit_annual_value_*`, `binary_sensor.credit_enrollment_needed`

### LLM Prompting
- Temperature: 0.3 for consistency
- System prompt: "You are a credit card advisor assistant..."
- Always request structured JSON output for card research
- For purchase queries, include current benefit balances in context
- Timeout: 30 seconds via aiohttp

### Naming
- Card IDs: snake_case slug from card name (e.g. `amex_gold`)
- YAML filenames: `{card_id}.yaml` for cards, `{benefit_id}_{year}.yaml` for benefits
- Sensor entity IDs: prefixed with `credit_`
- Service names: lowercase_with_underscores

### Error Handling
- LLM timeout/unavailable → fallback to static rewards comparison
- No cards stored → friendly prompt to add cards
- Malformed LLM JSON response → log error, return None
- Always log errors with `_LOGGER.error` at point of failure

### Testing
- No test framework for MVP (manual testing via HA logs)
- Phase 2+: pytest with pytest-homeassistant-custom-component
- Benefit math should be verifiable by inspection

## Implementation Order (MVP)

1. Component skeleton (manifest, const, __init__.py)
2. Card registry (YAML I/O, card CRUD)
3. LLM client (OpenRouter API, prompt building)
4. Sensor platform (response sensor for dashboard)
5. Lovelace dashboard configuration (input_text, button, markdown)

Phase 2 (benefit tracking) and Phase 3 (transaction hearing) will be planned separately.

## Git Conventions

- Branch from `main`
- Commit messages: `feat(scope): description` or `fix(scope): description`
- One commit per logical change
- No code changes without a Jules task — all implementation goes through Jules