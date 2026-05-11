Implement the Credit Advisor custom component with config flow, card registry, and ai_task-based services.

## Files to create or modify

- `custom_components/credit_advisor/const.py` — rewrite with constants
- `custom_components/credit_advisor/config_flow.py` — new file, config flow
- `custom_components/credit_advisor/__init__.py` — rewrite with async_setup_entry/async_unload_entry
- `custom_components/credit_advisor/card_registry.py` — new file, YAML-based card storage

Note: `custom_components/credit_advisor/manifest.json` already exists with `"config_flow": true` — do not modify it.

## What to build

### const.py
True constants only — things that define the stable contract:
- `DOMAIN = "credit_advisor"`
- `SERVICE_QUERY = "query"` and `SERVICE_ADD_CARD = "add_card"`
No setup-time variables (STORAGE_DIR is a local in async_setup_entry), no ATTR_* keys (inline at the handler), no forward declarations for future phases.

### config_flow.py
Standard HA config flow with minimal setup — no user-configurable options for MVP.

- Import: `from homeassistant import config_entries`
- ConfigFlow class: `CreditAdvisorConfigFlow` extending `config_entries.ConfigFlow` with domain `DOMAIN`
- Title: "Credit Card Advisor"
- Single step `async_step_user` that accepts the default form (no fields needed) and creates the entry
- Use `self.async_show_form(step_id="user", data_schema=vol.Schema({}))` for the form
- Use `return self.async_create_entry(title="Credit Card Advisor", data={})` to complete
- VERSION = 1, MINOR_VERSION = 1
- Import DOMAIN from `.const` for the domain attribute

### card_registry.py
`CardRegistry` class managing YAML files in a storage directory:
- `__init__(self, storage_path: str)` — creates `cards/` subdirectory
- `list_cards() -> list[str]` — returns sorted card IDs (file stems of *.yaml)
- `get_card_path(card_id: str) -> str` — returns full path to a card's YAML file
- `load_yaml(card_id: str) -> dict | None` — loads and parses a card, returns None if missing
- `save_card(card_name: str, card_data: dict) -> str` — saves card data to `{slug}.yaml`, returns card ID. Slugify the card name (lowercase, replace non-alphanumeric chars with underscore)
- `delete_card(card_id: str) -> bool` — deletes the card file, returns True if deleted
- Use `yaml.dump(..., default_flow_style=False, sort_keys=False)` for writing
- Use `yaml.safe_load` for reading
- Use module-level `_LOGGER` with %-formatting for logging saves and deletes
- Standard library: `logging`, `os`, `re`, `pathlib.Path`, `typing.Any`
- Third-party: `yaml`

### __init__.py
Integration setup via config entry (no CONFIG_SCHEMA or async_setup):

- `from __future__ import annotations`
- `logging`, `os` from stdlib
- `dataclasses.dataclass`
- `voluptuous` as `vol`
- `homeassistant.helpers.config_validation` as `cv`
- `HomeAssistant`, `ServiceCall`, `ServiceResponse`, `ConfigEntry` from `homeassistant.core`
- `ConfigType` from `homeassistant.helpers.typing`
- DOMAIN, SERVICE_QUERY, SERVICE_ADD_CARD from `.const`
- `CardRegistry` from `.card_registry`

**CreditAdvisorData dataclass:** holds `card_registry: CardRegistry`

**async_setup_entry(hass, entry):**
- Create storage path: `storage_path = hass.config.path(DOMAIN)`
- `os.makedirs(storage_path, exist_ok=True)`
- Instantiate `CardRegistry(storage_path)`
- Store as `hass.data[DOMAIN] = CreditAdvisorData(card_registry=card_registry)`
- Register two services (see below)
- Return True

**async_unload_entry(hass, entry):**
- Remove services: `hass.services.async_remove(DOMAIN, SERVICE_QUERY)` and `SERVICE_ADD_CARD`
- Clean up: `hass.data.pop(DOMAIN, None)`
- Return True

**`credit_advisor.query` service (takes `text` string):**
- Load all card YAMLs from registry
- If no cards stored, return `{"response": "message to add cards first"}`
- Build instructions string: card context (rewards, benefits for each card) + user's purchase query
- Call `hass.services.async_call("ai_task", "generate_data", {"task_name": "Credit Card Advisor", "instructions": ..., "structure": {"recommended_card": "", "reason": "", "multiplier": "", "alternatives": [], "credit_flagged": [], "warnings": []}}, blocking=True, return_response=True)`
- Return `{"response": result, "card_count": len(cards)}`
- Wrap ai_task call in try/except — on failure return `{"response": "friendly message saying to configure an LLM provider in HA UI (Settings → Devices & services → AI Task)", "card_count": 0}`

**`credit_advisor.add_card` service (takes `card_name` string):**
- Call `hass.services.async_call("ai_task", "generate_data", {"task_name": "Credit Card Research", "instructions": "Research this credit card and return its benefits and reward structure. Include: name, issuer, annual_fee, benefits (list with type, name, amount, frequency, valid_at, expires), rewards.base (category to multiplier mapping).", "structure": {"name": "", "issuer": "", "annual_fee": 0, "benefits": [], "rewards": {}}}, blocking=True, return_response=True)`
- Save result via `card_registry.save_card(card_name, result)`
- Return `{"card_id": card_id, "card_yaml": result}` on success
- Wrap in try/except — return `{"error": msg}` on failure

**Service registration with Voluptuous schemas:**
```python
hass.services.async_register(
    DOMAIN, SERVICE_QUERY, handle_query,
    schema=vol.Schema({vol.Required("text"): cv.string})
)
hass.services.async_register(
    DOMAIN, SERVICE_ADD_CARD, handle_add_card,
    schema=vol.Schema({vol.Required("card_name"): cv.string})
)
```

## Behavior specifications
- **No cards stored scenario:** query returns immediate friendly message without calling ai_task
- **ai_task unavailable:** both services catch exception, return human-readable error telling user to configure an LLM provider via HA UI (Settings → Devices & services → AI Task)
- **add_card research failure:** if ai_task returns empty or invalid data, return error message
- **All failures:** log a warning with %-formatting, never crash HA

## Constraints
- No HTTP clients, no API keys, no external network calls — all LLM via `ai_task.generate_data`
- Uses config flow with async_setup_entry — no CONFIG_SCHEMA or async_setup
- ATTR_* keys inline at the handler (response dicts, service parameter names)
- STORAGE_DIR is a local variable in async_setup_entry, not a module constant
- HA conventions: %-formatting for logging, Google-style docstrings, type hints required
- Line length 100, double quotes

## Validation
```bash
ruff check .
ruff format --check .
```
