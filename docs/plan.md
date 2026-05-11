# Credit Card Advisor — MVP Implementation Plan

**Architecture:** HA custom component (`custom_components/credit_advisor/`) with config flow, YAML-based card registry, LLM calls via HA's built-in `ai_task.generate_data` service, and Lovelace native cards (input_text + markdown) for the query interface.

**Tech Stack:** Home Assistant (2025.8+), Python 3.12, `ai_task` integration (provider-agnostic), YAML storage.

**Notes:**
- No API keys or HTTP clients in our component — all LLM via `ai_task.generate_data`
- User configures an LLM provider through HA's AI Task integration
- `manifest.json` uses `"after_dependencies": ["ai_task"]`

---

### Task 1: Create Custom Component Skeleton

**Objective:** Scaffold the HA custom component with config flow, constants, and `__init__.py` using `async_setup_entry`/`async_unload_entry`.

**Files to create:**
- `custom_components/credit_advisor/const.py`
- `custom_components/credit_advisor/config_flow.py`
- `custom_components/credit_advisor/__init__.py`

**const.py** — true constants only, things that define the stable contract across files:
- `DOMAIN`, `SERVICE_QUERY`, `SERVICE_ADD_CARD`, `SERVICE_REMOVE_CARD`
- No setup-time variables (storage path is a local in `async_setup_entry`), no `ATTR_*` keys (inline at handler), no forward declarations for future phases

**config_flow.py** — standard HA config flow, one-step, no user-configurable options for MVP:
- `VERSION = 1`, `MINOR_VERSION = 1`
- `async_step_user` with empty form (no fields), accepts on submit, creates entry with title "Credit Card Advisor"
- Minimal imports: `config_entries`, `voluptuous`, `DOMAIN` from `.const`

**__init__.py** — setup via config entry (no CONFIG_SCHEMA, no async_setup):
- `CreditAdvisorData` dataclass holding `CardRegistry` instance
- `async_setup_entry`: creates storage dir at `hass.config.path(DOMAIN)`, instantiates `CardRegistry`, registers three services, returns True
- `async_unload_entry`: removes all three services, cleans up `hass.data`, returns True
- Services registered with inline Voluptuous schemas (parameter keys are strings, not constants):
  - `query` — takes `"text"` (string). Loads cards from registry, formats them, calls `ai_task.generate_data`. Returns `{"response": ..., "card_count": n}`. No cards → early return. ai_task failure → friendly error message directing user to configure AI Task in HA UI.
  - `add_card` — takes `"card_name"` (string). Calls `ai_task.generate_data` to research the card, saves via `CardRegistry.save_card()`. Returns `{"card_id": ..., "card_yaml": ...}` or `{"error": ...}`.
  - `remove_card` — takes `"card_name"` (string). Slugifies to get card ID, calls `CardRegistry.delete_card()`. Returns `{"removed": True, "card_id": ...}` or `{"error": "Card not found"}`. No LLM call.

---

### Task 2: Create Card Registry (YAML I/O)

**Objective:** Build the `CardRegistry` class that manages card YAML files in a local directory.

**Files to create:**
- `custom_components/credit_advisor/card_registry.py`

**CardRegistry** — manages YAML files under `storage_path/cards/`:
- Constructor takes `storage_path` string, creates `cards/` and `benefits/` subdirectories
- `slugify(card_name)` — public staticmethod, lowercases, strips non-alphanumeric to underscores, returns the slug
- `list_cards()` — returns sorted card IDs (file stems of *.yaml in the cards dir)
- `get_card_path(card_id)` — returns `{cards_dir}/{card_id}.yaml`
- `load_yaml(card_id)` — reads and `yaml.safe_load`s the file, returns dict or None
- `save_card(card_name, card_data)` — slugifies the name, writes YAML via `yaml.dump(..., default_flow_style=False, sort_keys=False)`, returns card ID
- `delete_card(card_id)` — removes the file, returns True/False

Use module-level `_LOGGER` with %-formatting. Standard library + `yaml` only.

---

### Task 3: LLM Query Service (ai_task)

Already implemented in Task 1's `__init__.py`. Both `credit_advisor.query` and `credit_advisor.add_card` call `ai_task.generate_data` via the HA service bus. No separate LLM client file.

---

### Task 4: Register Sensor Platform for Dashboard Integration

**Objective:** Create a sensor entity that holds the last LLM query response, displayed in a Lovelace markdown card.

**Files to create/modify:**
- Create: `custom_components/credit_advisor/sensor.py`
- Modify: `custom_components/credit_advisor/__init__.py`

**Sensor (`sensor.py`):**
- Uses `async_setup_entry` (not `async_setup_platform`) since the component uses config flow
- `CreditResponseSensor` extends `SensorEntity` with `_attr_name = "Credit Advisor Response"`, `_attr_unique_id = "credit_advisor_response"`, `_attr_icon = "mdi:credit-card-outline"`, default state "Ask a question to get started."
- Module-level `update_response(response)` callback that updates the sensor's state and calls `async_write_ha_state()`

**`__init__.py` wiring:**
- In `async_setup_entry`, add `await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])` to register the sensor platform
- Import `update_response` from `.sensor`
- In `_async_query`, call `update_response(result)` before returning

---

### Task 5: Configure Lovelace Dashboard

**Objective:** Set up the Lovelace view with input_text, button, and markdown card for the query interface.

**All done via HA UI:**
- Create input helpers (Settings → Helpers): `input_text.credit_query` and `input_button.credit_ask`
- Create automation: trigger on `input_button.credit_ask → pressed`, action calls `credit_advisor.query` with `text: {{ states('input_text.credit_query') }}`
- Create Lovelace view with: heading card, entities card (showing the two helpers), and a markdown card displaying `sensor.credit_advisor_response`
