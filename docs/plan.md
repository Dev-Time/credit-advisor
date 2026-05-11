# Credit Card Advisor — MVP Implementation Plan

**Architecture:** HA custom component (`custom_components/credit_advisor/`) with config flow, YAML-based card registry, LLM calls via HA's built-in `ai_task.generate_data` service, and Lovelace native cards (input_text + markdown) for the query interface.

**Tech Stack:** Home Assistant (2025.8+), Python 3.12, `ai_task` integration (provider-agnostic), YAML storage.

**Notes:**
- No API keys or HTTP clients in our component — all LLM via `ai_task.generate_data`
- User configures an LLM provider through HA's AI Task integration
- `manifest.json` uses `"after_dependencies": ["ai_task"]`
- Tasks are intentionally small — each should produce a diff that can be reviewed in under 5 minutes

---

## Phase 1 — Core Integration

### P1-1: Empty integration shell

Create the minimal files needed to add the integration via HA UI. No services, no storage, no card registry — just a component that appears in the integrations list and can be added/removed.

**Files:**
- `custom_components/credit_advisor/manifest.json` — already exists with `config_flow: true`, `after_dependencies: ["ai_task"]`, `integration_type: service`
- `custom_components/credit_advisor/const.py` — `DOMAIN` constant only (the single thing needed for config flow registration)
- `custom_components/credit_advisor/config_flow.py` — single-step flow with empty form, creates entry on submit
- `custom_components/credit_advisor/__init__.py` — `async_setup_entry` and `async_unload_entry` that do nothing (return True). No services, no data dir, no state.

---

### P1-2: Setup/unload hooks + storage directory

Wire up `async_setup_entry` to create the data directory at `hass.config.path(DOMAIN)`, and `async_unload_entry` to clean up `hass.data`. Add a config flow option for storage directory path.

**Files:**
- `custom_components/credit_advisor/__init__.py` — `async_setup_entry` creates storage dir, stores path in `hass.data`; `async_unload_entry` cleans up
- `custom_components/credit_advisor/config_flow.py` — add configurable storage path option (optional, with default)

---

### P1-3: add_card service (LLM-assisted)

Add the `credit_advisor.add_card` service that uses `ai_task.generate_data` to research a card and saves its definition.

**Files:**
- `custom_components/credit_advisor/const.py` — add `SERVICE_ADD_CARD`
- `custom_components/credit_advisor/__init__.py` — register `add_card` service, call `ai_task.generate_data` for research, save result
- `custom_components/credit_advisor/card_registry.py` — `CardRegistry` class: `slugify`, `save_card`, `list_cards`, `load_yaml`, `get_card_path`

---

### P1-4: query and remove_card services (no LLM)

Add `credit_advisor.query` (reads card data, sends to ai_task for recommendation) and `credit_advisor.remove_card` (deletes card YAML, no LLM needed).

**Files:**
- `custom_components/credit_advisor/const.py` — add `SERVICE_QUERY`, `SERVICE_REMOVE_CARD`
- `custom_components/credit_advisor/__init__.py` — register both services; `query` calls `ai_task.generate_data` with card context; `remove_card` calls `card_registry.delete_card`
- `custom_components/credit_advisor/card_registry.py` — add `delete_card` method

---

### P1-5: Response sensor

Create a sensor entity that holds the last query response, wired to the query service.

**Files:**
- `custom_components/credit_advisor/sensor.py` — `CreditResponseSensor` with `update_response` callback
- `custom_components/credit_advisor/__init__.py` — register sensor platform, call `update_response` after each query

---

### P1-6: Lovelace dashboard

Configure the Lovelace view with input_text, button, and markdown card. All done via HA UI — no code changes.

**Files:**
- None — all configuration through HA UI (input helpers, automation, Lovelace view)

---

## Future Phases

- **Phase 2** — Benefit tracking (usage per period, annual value rollup, expiry notifications)
- **Phase 3** — Transaction hearing (Tasker notification listener → HA webhook)
- **Phase 4** — Offer scraping (headless browser)
