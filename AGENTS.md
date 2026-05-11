# Credit Card Advisor — AGENTS.md

This file provides context for AI coding agents (Jules) working on this project.

## Environment Constraints

- **HA Installation Type:** HA Core (no Supervisor)
  - **No add-ons** — everything runs inside the HA Python process or as standalone services
  - **No HACS Supervisor integration** — HACS can still be installed manually on HA Core
  - **Phase 4 scraper** must run as a standalone Docker container or systemd service, not as a Supervisor add-on
  - Custom component communicates with external services via HTTP (standard integration pattern)

## Project Overview

A Home Assistant custom component (`custom_components/credit_advisor/`) that helps users decide which credit card to use for purchases and track benefit usage. Privacy-first — all data stored locally on the user's HA instance.

## Tech Stack

- **Platform:** Home Assistant (2025.8+, Python 3.12)
- **Storage:** YAML files in `[HA_CONFIG]/credit_advisor/`
- **LLM:** HA `ai_task` integration (routes through OpenRouter, configured once in HA UI)
- **Frontend:** Native Lovelace cards (no custom JS for MVP)
- **HTTP:** HA service bus (no direct HTTP calls needed)
- **No external databases, ORMs, or frameworks**

## Architecture

```
custom_components/credit_advisor/
├── __init__.py       → Setup via config entry, service registration
├── config_flow.py    → HA UI config flow (one-step, no options)
├── const.py          → Domain, service names, event types only
├── manifest.json     → HA manifest (version, requirements)
├── card_registry.py  → Card CRUD, YAML I/O
├── benefit_tracker.py → Usage tracking, expiry calc, annual rollup
├── sensors.py        → Sensor entities for dashboard/automations
```

## Development Rules

### Required Tooling
- **Ruff** (v0.11.6) — all linting and formatting. NO other formatters/linters.
- **uv** — for virtualenv and dependency management.
- **Makefile** targets: `make lint`, `make format`, `make check`, `make fix`
- **Pre-commit** hooks run on commit: ruff --fix, ruff-format, check-yaml, trailing-whitespace, end-of-file-fixer

### Style (per HA Developer Docs)
- **Line length:** 100
- **Quotes:** double quotes (ruff default)
- **Imports:** standard library → third-party → custom_components (isort via ruff)
- **Type hints:** required for all function signatures
- **No stubs or type comments** — inline annotations only
- **Comments:** full sentences ending with period
- **Constants:** alphabetical order within lists and dicts
- **f-strings:** PREFERRED for all string formatting — EXCEPT logging (see below)

### Logging (HA-specific conventions)
- Always via module-level `_LOGGER`, never `print()`
- Use **%-formatting** (NOT f-strings) — avoids formatting when log is suppressed
  ```python
  # CORRECT for logging:
  _LOGGER.warning("Could not reach API: %s", err)

  # WRONG for logging:
  _LOGGER.warning(f"Could not reach API: {err}")
  ```
- **No period at end** of log messages (like syslog)
- **Don't add component name** — HA prepends it automatically
- `_LOGGER.error` / `_LOGGER.warning` for user-visible issues
- `_LOGGER.debug` for everything else — be restrictive with `info`
- Never log API keys, tokens, usernames, or passwords (even when wrong)

### Docstrings (Google style)
Per HA convention, follow [Google style](https://google.github.io/styleguide/pyguide.html) for docstrings with parameters/returns/exceptions:
```python
def some_method(self, param1: str, param2: str) -> int:
    """Example Google-style docstring.

    Args:
        param1: The first parameter.
        param2: The second parameter.

    Returns:
        An integer result.

    Raises:
        KeyError: If the key doesn't exist.
    """
    return 0
```

### Sensor Design (HA best practices)
- Derive from `homeassistant.components.sensor.SensorEntity`
- Properties must return from memory — NO I/O in property accessors
- **Do NOT use `extra_state_attributes` for values that change** — they bloat the DB
- Instead, create separate sensor entities for each value
- Use `SensorDeviceClass.MONETARY` for dollar amounts, `SensorDeviceClass.DATE` for dates
- The response sensor (`sensor.credit_advisor_response`) is a text sensor — no device class

### Config Flow (no configuration.yaml)
The component uses a config flow — no `configuration.yaml` needed:
- `config_flow.py` with a single-step `async_step_user` (empty form, accepts on confirm)
- `async_setup_entry` / `async_unload_entry` in `__init__.py`
- No `CONFIG_SCHEMA` — config flow handles setup
- Future options (storage path override, etc.) go in `async_step_options` when needed

### File Conventions
- All custom component files live under `custom_components/credit_advisor/`
- Card YAML files go in `[HA_CONFIG]/credit_advisor/cards/`
- Benefit usage YAML goes in `[HA_CONFIG]/credit_advisor/benefits/`
- Use `yaml.safe_dump` with `default_flow_style=False, sort_keys=False`

### Service API
Register services via `hass.services.async_register` — parameter keys are inline strings, not constants:
- `credit_advisor.query` — takes `text` (string), calls `ai_task.generate_data` with card context and structured output, returns recommendation
- `credit_advisor.add_card` — takes `card_name` (string), calls `ai_task.generate_data` to research card, saves YAML
- `credit_advisor.log_benefit_usage` — (Phase 2, event type TBD)
- `credit_advisor.refresh_benefits` — (Phase 2) weekly LLM check for benefit changes

### Sensor Platform
- Expose `sensor.credit_advisor_response` for the LLM query result
- Phase 2: `sensor.credit_benefit_expiring`, `sensor.credit_benefit_unused`, `sensor.credit_annual_value_*`, `binary_sensor.credit_enrollment_needed`

### AI Task Integration
- No custom LLM client — use HA's built-in `ai_task.generate_data` service
- Build structured prompt with card context (rewards, benefit balances) + user query
- Use `hass.services.async_call("ai_task", "generate_data", ...)` with `blocking=True, return_response=True`
- Submit a `structure` parameter defining the expected output fields (recommended_card, reason, multiplier, alternatives, credit_flagged, warnings)
- For card research, submit structure with card_data field
- The user configures OpenRouter once in HA UI — no API key or model needed in our component
- Our manifest declares `"after_dependencies": ["ai_task", "open_router"]` so these are loaded first
- To handle the case where ai_task is not configured, wrap the call in try/except and return a friendly message

### Naming
- Card IDs: snake_case slug from card name (e.g. `amex_gold`)
- YAML filenames: `{card_id}.yaml` for cards, `{benefit_id}_{year}.yaml` for benefits
- Sensor entity IDs: prefixed with `credit_`
- Service names: lowercase_with_underscores

### Error Handling
- `ai_task.generate_data` unavailable (not configured) → friendly prompt to set up OpenRouter in HA UI
- No cards stored → friendly prompt to add cards
- In both cases, log a warning and return a human-readable message, never crash

### Testing (Phase 2+)
When adding tests, follow the official HA custom component testing pattern:
- Use `pytest` with `pytest-homeassistant-custom-component`
- Required fixtures: `enable_custom_integrations` (loads from custom_components/)
- Required config: `asyncio_mode = auto` in `pyproject.toml` under `[tool.pytest.ini_options]`
- Import HA test helpers from `pytest_homeassistant_custom_component.common` (not `tests.common`)
- Use syrupy snapshots for sensor state testing via `HomeAssistantSnapshotExtension`
- Test structure:
  ```
  tests/
  ├── conftest.py          # fixture definitions
  ├── test_init.py         # component setup
  ├── test_sensor.py       # sensor state tests
  └── snapshots/           # syrupy snapshot files
  ```

## Implementation Order (MVP)

1. Component skeleton (config_flow.py, const.py, __init__.py with async_setup_entry/async_unload_entry)
2. Card registry (YAML I/O, card CRUD)
3. Query + add-card services (calls `ai_task.generate_data` instead of a custom LLM client)
4. Sensor platform (response sensor for dashboard)
5. Lovelace dashboard configuration (input_text, button, markdown)

Phase 2 (benefit tracking) and Phase 3 (transaction hearing) will be planned separately.

## Git Conventions

- Branch from `main`
- Commit messages: `feat(scope): description` or `fix(scope): description`
- One commit per logical change
- No code changes without a Jules task — all implementation goes through Jules
