# Credit Card Advisor — MVP Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Architecture:** HA custom component (`custom_components/credit_advisor/`) with config flow, YAML-based card registry, integration with HA's built-in `ai_task.generate_data` service, and two services (query, add_card). Lovelace uses native cards (input_text + markdown) — no custom JS.

**Tech Stack:** Home Assistant (2025.8+), Python 3.12, HA `ai_task` integration (provider-agnostic), YAML storage.

**HA Config Path:** Replace `[HA_CONFIG]` in all file paths with your HA config directory (e.g. `/config`, `/home/homeassistant/.homeassistant/`).

**Notes:**
- No API keys or HTTP clients in our component — all LLM calls go through `ai_task.generate_data`
- User configures their LLM provider through HA's AI Task integration (Settings → Devices & services)
- manifest.json uses `"after_dependencies": ["ai_task"]` to ensure it's loaded first

---

### Task 1: Create Custom Component Skeleton

**Objective:** Scaffold the HA custom component with config flow, constants, and `__init__.py` using `async_setup_entry`/`async_unload_entry`.

**Files:**
- Create: `[HA_CONFIG]/custom_components/credit_advisor/const.py`
- Create: `[HA_CONFIG]/custom_components/credit_advisor/config_flow.py`
- Create: `[HA_CONFIG]/custom_components/credit_advisor/__init__.py`

**Step 1: Create `const.py`**

True constants only — things that define a stable contract across files:

```python
"""Constants for the Credit Advisor integration."""

DOMAIN = "credit_advisor"
SERVICE_QUERY = "query"
SERVICE_ADD_CARD = "add_card"
```

No setup-time variables (STORAGE_DIR is a local in async_setup_entry), no ATTR_* keys (inline at the handler), no forward declarations for future phases.

**Step 2: Create `config_flow.py`**

Standard HA config flow with a single-step form (no user-configurable options for MVP):

```python
"""Config flow for Credit Advisor integration."""
from __future__ import annotations

from homeassistant import config_entries
import voluptuous as vol

from .const import DOMAIN


class CreditAdvisorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Credit Advisor."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title="Credit Card Advisor", data={})

        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))
```

**Step 3: Create `__init__.py`**

Setup via config entry — no CONFIG_SCHEMA, no async_setup:

```python
"""Credit Advisor integration for Home Assistant."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, SERVICE_QUERY, SERVICE_ADD_CARD
from .card_registry import CardRegistry

_LOGGER = logging.getLogger(__name__)


@dataclass
class CreditAdvisorData:
    """Runtime data for the integration."""

    card_registry: CardRegistry


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Credit Advisor from a config entry."""
    storage_path = hass.config.path(DOMAIN)
    os.makedirs(storage_path, exist_ok=True)

    card_registry = CardRegistry(storage_path)
    hass.data[DOMAIN] = CreditAdvisorData(card_registry=card_registry)

    # Register services
    async def handle_query(call: ServiceCall) -> ServiceResponse:
        """Handle credit_advisor.query service call."""
        query_text: str = call.data["text"]
        data = hass.data[DOMAIN]
        return await _async_query(hass, data, query_text)

    async def handle_add_card(call: ServiceCall) -> ServiceResponse:
        """Handle credit_advisor.add_card service call."""
        card_name: str = call.data["card_name"]
        data = hass.data[DOMAIN]
        return await _async_add_card(hass, data, card_name)

    hass.services.async_register(
        DOMAIN, SERVICE_QUERY, handle_query,
        schema=vol.Schema({vol.Required("text"): cv.string})
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_CARD, handle_add_card,
        schema=vol.Schema({vol.Required("card_name"): cv.string})
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.services.async_remove(DOMAIN, SERVICE_QUERY)
    hass.services.async_remove(DOMAIN, SERVICE_ADD_CARD)
    hass.data.pop(DOMAIN, None)
    return True


async def _async_query(hass: HomeAssistant, data: CreditAdvisorData, query_text: str) -> dict:
    """Run a purchase query via ai_task."""
    cards = data.card_registry.list_cards()
    if not cards:
        return {"response": "You haven't added any cards yet."}

    card_yamls = [data.card_registry.load_yaml(cid) for cid in cards]

    instructions = f"The user has these cards:\n{card_yamls}\n\nPurchase query: {query_text}"

    try:
        result = await hass.services.async_call(
            "ai_task", "generate_data",
            {
                "task_name": "Credit Card Advisor",
                "instructions": instructions,
                "structure": {
                    "recommended_card": "",
                    "reason": "",
                    "multiplier": "",
                    "alternatives": [],
                    "credit_flagged": [],
                    "warnings": [],
                },
            },
            blocking=True,
            return_response=True,
        )
        return {"response": result, "card_count": len(cards)}
    except Exception:
        _LOGGER.warning("ai_task call failed for query")
        return {"response": "The AI Task integration is not configured. Set up an LLM provider in Settings → Devices & services → AI Task.", "card_count": 0}


async def _async_add_card(hass: HomeAssistant, data: CreditAdvisorData, card_name: str) -> dict:
    """Research a card and save it via ai_task."""
    try:
        result = await hass.services.async_call(
            "ai_task", "generate_data",
            {
                "task_name": "Credit Card Research",
                "instructions": f"Research the credit card \"{card_name}\" and return its benefits and reward structure.",
                "structure": {
                    "name": "",
                    "issuer": "",
                    "annual_fee": 0,
                    "benefits": [],
                    "rewards": {},
                },
            },
            blocking=True,
            return_response=True,
        )
    except Exception:
        _LOGGER.warning("ai_task call failed for add_card")
        return {"error": "The AI Task integration is not configured. Set up an LLM provider in Settings → Devices & services → AI Task."}

    if not result:
        return {"error": f"Could not research card: {card_name}"}

    card_id = data.card_registry.save_card(card_name, result)
    return {"card_id": card_id, "card_yaml": result}
```

**Step 4: Verify the component loads in HA**

Restart HA and check logs:
```
# In HA logs (Settings → System → Logs):
# Expected: No errors loading credit_advisor
# If missing: check custom_components directory path and permissions
```

**Step 5: Commit**

```bash
git add [HA_CONFIG]/custom_components/credit_advisor/
git commit -m "feat: add Credit Advisor config flow and services"
```

---

### Task 2: Create Card Registry (YAML I/O)

**Objective:** Build the `CardRegistry` class that manages reading/writing card YAML files in a local directory.

**Files:**
- Create: `[HA_CONFIG]/custom_components/credit_advisor/card_registry.py`

**Step 1: Write the module**

```python
"""Card registry — manages YAML storage for credit card definitions."""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml

_LOGGER = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    """Convert a card name to a safe file ID."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


class CardRegistry:
    """Manages credit card YAML files in a local directory."""

    def __init__(self, storage_path: str) -> None:
        self._cards_dir = os.path.join(storage_path, "cards")
        self._benefits_dir = os.path.join(storage_path, "benefits")
        os.makedirs(self._cards_dir, exist_ok=True)
        os.makedirs(self._benefits_dir, exist_ok=True)

    def list_cards(self) -> list[str]:
        """Return card IDs of all stored cards."""
        files = Path(self._cards_dir).glob("*.yaml")
        return sorted(f.stem for f in files)

    def get_card_path(self, card_id: str) -> str:
        """Get the YAML file path for a card ID."""
        return os.path.join(self._cards_dir, f"{card_id}.yaml")

    def load_yaml(self, card_id: str) -> dict[str, Any] | None:
        """Load a card's YAML file. Returns None if not found."""
        path = self.get_card_path(card_id)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            return yaml.safe_load(f)

    def save_card(self, card_name: str, card_yaml: dict[str, Any]) -> str:
        """Save a card's YAML data. Returns the card ID."""
        card_id = _slugify(card_name)
        # Ensure card has an ID field
        card_yaml["id"] = card_id
        path = self.get_card_path(card_id)
        with open(path, "w") as f:
            yaml.dump(card_yaml, f, default_flow_style=False, sort_keys=False)
        _LOGGER.info("Saved card: %s → %s", card_name, path)
        return card_id

    def delete_card(self, card_id: str) -> bool:
        """Delete a card file. Returns True if deleted."""
        path = self.get_card_path(card_id)
        if os.path.exists(path):
            os.remove(path)
            _LOGGER.info("Deleted card: %s", card_id)
            return True
        return False
```

**Step 2: Create an example card YAML for testing**

Create `[HA_CONFIG]/credit_advisor/cards/example.yaml`:

```yaml
id: example_card
name: Example Card
issuer: Example Bank
annual_fee: 0
benefits: []
rewards:
  base:
    dining: 3x
    groceries: 2x
    everything_else: 1x
offers:
  active: []
```

**Step 3: Commit**

```bash
git add [HA_CONFIG]/custom_components/credit_advisor/card_registry.py
git add [HA_CONFIG]/credit_advisor/cards/example.yaml
git commit -m "feat: add card registry with YAML storage"
```

---

### Task 3: LLM Query Service (ai_task)

**Objective:** Already implemented in Task 1's `__init__.py`. Both `credit_advisor.query` and `credit_advisor.add_card` call `ai_task.generate_data` via the HA service bus — no separate LLM client file needed.

The prompt builder and structure definitions live as inline code in `__init__.py`:
- `query` sends card context + user purchase query to `ai_task.generate_data` with a structured output schema
- `add_card` sends a card research prompt to `ai_task.generate_data` with a card data schema
- Both wrap the call in try/except for when AI Task isn't configured
- No `llm_client.py`, no aiohttp, no API keys

---

### Task 4: Register Sensor Platform for Dashboard Integration

**Objective:** Create the sensor that feeds the LLM query response into a Lovelace-markdown-displayable entity.

**Files:**
- Create: `[HA_CONFIG]/custom_components/credit_advisor/sensor.py`
- Modify: `[HA_CONFIG]/custom_components/credit_advisor/__init__.py` (register sensor platform via config entry)

**Step 1: Write sensor platform** — uses `async_setup_entry`, not `async_setup_platform` (config flow component):

```python
"""Sensor platform for Credit Advisor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the credit advisor sensor from a config entry."""
    async_add_entities([CreditResponseSensor()])


@callback
def update_response(response: str) -> None:
    """Update the sensor with a new LLM response."""
    if SENSOR_INSTANCE is not None:
        SENSOR_INSTANCE._attr_native_value = response  # noqa: SLF001
        SENSOR_INSTANCE.async_write_ha_state()


class CreditResponseSensor(SensorEntity):
    """Sensor that holds the last LLM query response."""

    _attr_name = "Credit Advisor Response"
    _attr_unique_id = "credit_advisor_response"
    _attr_icon = "mdi:credit-card-outline"
    _attr_native_value = "Ask a question to get started."
```

**Step 2: Update `__init__.py`** — register sensor platform and wire up response updates:

```python
# In async_setup_entry, add:
await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

# Add import at top:
from .sensor import update_response

# In _async_query, before returning:
update_response(result)
```

**Step 3: Commit**

```bash
git add [HA_CONFIG]/custom_components/credit_advisor/sensor.py
git add [HA_CONFIG]/custom_components/credit_advisor/__init__.py
git commit -m "feat: add response sensor for Lovelace dashboard integration"
```

---

### Task 5: Configure Lovelace Dashboard

**Objective:** Set up the Lovelace view with input_text, button, and markdown card for the query interface. The component uses a config flow — no YAML config entry is needed.

**Files:**
- Modify: Lovelace dashboard configuration (via HA UI or YAML)
- No config YAML modifications needed

**Step 1: Add input helpers via HA UI**

Create these entities in Settings → Devices & services → Helpers → Create helper:

1. **Text helper** — `input_text.credit_query`
   - Name: "What are you buying?"
   - Icon: mdi:cart

2. **Button helper** — `input_button.credit_ask`
   - Name: "Ask the Advisor"
   - Icon: mdi:send

**Step 2: Add automation via HA UI**

Settings → Automations → Create automation → Create new automation:

- Trigger: `input_button.credit_ask` → state is `pressed`
- Action: Call service `credit_advisor.query` with text `{{ states('input_text.credit_query') }}`

**Step 3: Create Lovelace view**

Edit Dashboard → Add View → Enter dashboard YAML:

```yaml
title: Credit Advisor
icon: mdi:credit-card
cards:
  - type: heading
    heading: 💳 Credit Card Advisor

  - type: entities
    title: Ask a Question
    entities:
      - entity: input_text.credit_query
        name: "What are you buying?"
      - entity: input_button.credit_ask
        name: "Ask the Advisor"

  - type: markdown
    title: Recommendation
    content: >
      {{ state_attr('sensor.credit_advisor_response', 'state') or
         states('sensor.credit_advisor_response') }}
```

**Step 4: Restart HA and test**

1. Restart Home Assistant
2. Navigate to the Credit Advisor dashboard
3. Type a query: "Chipotle $14"
4. Press "Ask the Advisor"
5. Observe the markdown card update with the recommendation

**Step 5: Commit**

```bash
git add lovelace/ (or export the view config if using YAML dashboards)
git commit -m "docs: add Lovelace dashboard configuration instructions"
```

---

## Verification

After installation:
1. HA starts without errors in the logs
2. Developer Tools → Services shows `credit_advisor.query` and `credit_advisor.add_card`
3. Calling `credit_advisor.add_card` with `card_name: "Chase Sapphire Reserve"` creates a YAML file
4. Calling `credit_advisor.query` with `text: "flights to Tokyo"` returns a card recommendation
5. The Lovelace dashboard shows the query result in the markdown card
