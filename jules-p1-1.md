Create an empty integration shell that can be added and removed via Home Assistant's UI. No services, no storage, no card registry — just the component appearing in the integrations list.

## Files to create or modify

- `custom_components/credit_advisor/const.py` — rewrite with minimal constants
- `custom_components/credit_advisor/config_flow.py` — new file, config flow
- `custom_components/credit_advisor/__init__.py` — rewrite with empty async_setup_entry/async_unload_entry

Note: `custom_components/credit_advisor/manifest.json` already exists with `"config_flow": true` — do not modify it.

## What to build

### const.py
Single constant — just the domain identifier:
- `DOMAIN = "credit_advisor"`

No service names, no event types, no storage dir, no attribute keys. Those come in later tasks.

### config_flow.py
Standard HA config flow, one-step, no user-configurable options:

- Import: `from homeassistant import config_entries`
- Import: `voluptuous` as `vol`
- Import: `DOMAIN` from `.const`
- ConfigFlow class: `CreditAdvisorConfigFlow` extending `config_entries.ConfigFlow` with domain `DOMAIN`
- Title: "Credit Card Advisor"
- VERSION = 1, MINOR_VERSION = 1
- Single step `async_step_user` that shows an empty form (`vol.Schema({})`) and creates the entry on submit
- Use `self.async_create_entry(title="Credit Card Advisor", data={})`

### __init__.py
Minimal setup — the component is functional but does nothing yet:

- `from __future__ import annotations`
- `logging`
- `HomeAssistant`, `ConfigEntry` from `homeassistant.core`
- `DOMAIN` from `.const`

**async_setup_entry(hass, entry):**
- Log an info message: "Credit Advisor integration started"
- Return True

**async_unload_entry(hass, entry):**
- Log an info message: "Credit Advisor integration stopped"
- Return True

No services registered. No data directory created. No CardRegistry instantiated. No hass.data used.

## Constraints
- HA conventions: %-formatting for logging, type hints required
- Line length 100, double quotes

## Validation
```bash
ruff check .
ruff format --check .
```
