# Credit Card Advisor — MVP Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build the MVP query engine — a Home Assistant custom component that answers "which card should I use for this purchase?" via a Lovelace dashboard.

**Architecture:** HA custom component (`custom_components/credit_advisor/`) with a YAML-based card registry, OpenRouter-powered LLM client, and two services (query, add_card). Lovelace uses native cards (input_text + markdown) — no custom JS.

**Tech Stack:** Home Assistant (2024.12+), Python 3.12, OpenRouter REST API (any model), YAML storage.

**HA Config Path:** Replace `[HA_CONFIG]` in all file paths with your HA config directory (e.g. `/config`, `/home/homeassistant/.homeassistant/`).

---

### Task 1: Create Custom Component Skeleton

**Objective:** Scaffold the HA custom component with manifest, constants, and `__init__.py` that registers the domain and services.

**Files:**
- Create: `[HA_CONFIG]/custom_components/credit_advisor/__init__.py`
- Create: `[HA_CONFIG]/custom_components/credit_advisor/const.py`
- Create: `[HA_CONFIG]/custom_components/credit_advisor/manifest.json`

**Step 1: Create `manifest.json`**

```json
{
  "domain": "credit_advisor",
  "name": "Credit Card Advisor",
  "version": "1.0.0",
  "requirements": ["aiohttp"],
  "dependencies": [],
  "codeowners": [],
  "config_flow": false,
  "iot_class": "cloud_polling"
}
```

**Step 2: Create `const.py`**

```python
"""Constants for the Credit Advisor integration."""

DOMAIN = "credit_advisor"
CONF_OPENROUTER_API_KEY = "openrouter_api_key"
CONF_OPENROUTER_MODEL = "openrouter_model"
CONF_CARDS_DIR = "cards_dir"

DEFAULT_MODEL = "openai/gpt-4o-mini"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_TIMEOUT = 30

STORAGE_DIR = "credit_advisor"

# Service names
SERVICE_QUERY = "query"
SERVICE_ADD_CARD = "add_card"

# Attributes
ATTR_QUERY_TEXT = "text"
ATTR_CARD_NAME = "card_name"
ATTR_CARD_YAML = "card_yaml"
ATTR_RESPONSE = "response"
ATTR_ERROR = "error"

# Event types
EVENT_BENEFIT_EXPIRING = "credit_advisor_benefit_expiring"
```

**Step 3: Create `__init__.py`**

```python
"""Credit Advisor integration for Home Assistant."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_OPENROUTER_API_KEY,
    CONF_OPENROUTER_MODEL,
    DEFAULT_MODEL,
    STORAGE_DIR,
    SERVICE_QUERY,
    SERVICE_ADD_CARD,
    ATTR_QUERY_TEXT,
    ATTR_CARD_NAME,
)
from .card_registry import CardRegistry
from .llm_client import LLMClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = []

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_OPENROUTER_API_KEY): cv.string,
                vol.Optional(CONF_OPENROUTER_MODEL, default=DEFAULT_MODEL): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


@dataclass
class CreditAdvisorData:
    """Runtime data for the integration."""

    card_registry: CardRegistry
    llm_client: LLMClient


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Credit Advisor integration."""
    conf = config.get(DOMAIN)
    if conf is None:
        # Config via configuration.yaml is required until config_flow
        _LOGGER.warning("Credit Advisor not configured — add to configuration.yaml")
        return True

    api_key = conf[CONF_OPENROUTER_API_KEY]
    model = conf.get(CONF_OPENROUTER_MODEL, DEFAULT_MODEL)

    # Storage directory next to HA config
    storage_path = hass.config.path(STORAGE_DIR)
    os.makedirs(storage_path, exist_ok=True)

    card_registry = CardRegistry(storage_path)
    llm_client = LLMClient(api_key, model)

    hass.data[DOMAIN] = CreditAdvisorData(
        card_registry=card_registry,
        llm_client=llm_client,
    )

    # Register services
    async def handle_query(call: ServiceCall) -> ServiceResponse:
        """Handle credit_advisor.query service call."""
        query_text: str = call.data[ATTR_QUERY_TEXT]
        data = hass.data[DOMAIN]
        return await _async_query(data, query_text)

    async def handle_add_card(call: ServiceCall) -> ServiceResponse:
        """Handle credit_advisor.add_card service call."""
        card_name: str = call.data[ATTR_CARD_NAME]
        data = hass.data[DOMAIN]
        return await _async_add_card(hass, data, card_name)

    hass.services.async_register(
        DOMAIN, SERVICE_QUERY, handle_query, schema=vol.Schema({
            vol.Required(ATTR_QUERY_TEXT): cv.string,
        })
    )

    hass.services.async_register(
        DOMAIN, SERVICE_ADD_CARD, handle_add_card, schema=vol.Schema({
            vol.Required(ATTR_CARD_NAME): cv.string,
        })
    )

    # Register sensor platform
    hass.async_create_task(
        hass.helpers.discovery.async_load_platform("sensor", DOMAIN, {}, config)
    )

    return True


async def _async_query(data: CreditAdvisorData, query_text: str) -> dict:
    """Run a purchase query against the LLM."""
    cards = data.card_registry.list_cards()
    card_yamls = [data.card_registry.load_yaml(card_id) for card_id in cards]

    response = await data.llm_client.query_purchase(card_yamls, query_text)

    return {
        "response": response,
        "card_count": len(cards),
    }


async def _async_add_card(hass: HomeAssistant, data: CreditAdvisorData, card_name: str) -> dict:
    """Research a card and save it to the registry."""
    card_yaml = await data.llm_client.research_card(card_name)

    if not card_yaml:
        return {"error": f"Could not research card: {card_name}"}

    card_id = data.card_registry.save_card(card_name, card_yaml)
    return {"card_id": card_id, "card_yaml": card_yaml}
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
git commit -m "feat: add Credit Advisor custom component skeleton"
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

### Task 3: Create LLM Client (OpenRouter)

**Objective:** Build the `LLMClient` that calls OpenRouter with card context for purchase queries and card research.

**Files:**
- Create: `[HA_CONFIG]/custom_components/credit_advisor/llm_client.py`

**Step 1: Write the module**

```python
"""LLM client for OpenRouter — handles purchase queries and card research."""
from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

from .const import OPENROUTER_BASE_URL, OPENROUTER_TIMEOUT

_LOGGER = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a credit card advisor assistant. You help users decide which credit card to use for purchases.

You have access to the user's card portfolio with reward structures and benefit balances.

When answering:
1. Recommend the best card for this specific purchase
2. Explain why — mention the multiplier and value
3. List alternatives ranked by value
4. Flag any applicable monthly/quarterly credits the user should be aware of
5. Warn if a card has a low multiplier and should be saved for better categories

Be concise and specific. Use emojis where appropriate for readability."""

QUERY_PROMPT_TEMPLATE = """The user has the following credit cards:

{card_descriptions}

The user asks: "{query}"

Return a JSON object with these fields:
- "recommended_card": name of the best card
- "reason": why this card is best
- "multiplier": the multiplier this purchase earns (e.g. "4x")
- "alternatives": list of {name, multiplier, reason} for other cards
- "credit_flagged": any monthly/quarterly credits that could apply to this purchase
- "warnings": any things to watch out for"""

RESEARCH_PROMPT = """Research the credit card "{card_name}" and return its current benefits and reward structure as JSON.

Include:
- name, issuer, annual_fee
- benefits: list of benefits with type (monthly_credit, quarterly_credit, statement_credit, lounge, etc.), name, amount, frequency, valid_at merchants, expiration rules
- rewards.base: map of category to multiplier
Keep it factual and based on current publicly available information.
Return ONLY valid JSON, no other text."""


class LLMClient:
    """Client for OpenRouter API calls."""

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://homeassistant.local",
        }

    async def query_purchase(
        self, card_yamls: list[dict[str, Any]], query: str
    ) -> str:
        """Ask the LLM which card to use for a purchase."""
        if not card_yamls:
            return "You haven't added any cards yet. Use the **Add Card** option to add your credit cards first."

        card_descriptions = self._format_cards(card_yamls)
        prompt = QUERY_PROMPT_TEMPLATE.format(
            card_descriptions=card_descriptions,
            query=query,
        )

        result = await self._call_llm(prompt)
        return result

    async def research_card(self, card_name: str) -> dict[str, Any] | None:
        """Research a card's benefits and rewards via LLM."""
        prompt = RESEARCH_PROMPT.format(card_name=card_name)

        result = await self._call_llm(prompt)

        try:
            # Strip any markdown fences the LLM might wrap the JSON in
            clean = result.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1]
                clean = clean.rsplit("```", 1)[0]
            return json.loads(clean.strip())
        except (json.JSONDecodeError, IndexError) as e:
            _LOGGER.error("Failed to parse card research response: %s", e)
            _LOGGER.debug("Raw response: %s", result)
            return None

    async def _call_llm(self, prompt: str) -> str:
        """Make a raw LLM call to OpenRouter."""
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 1000,
        }

        timeout = aiohttp.ClientTimeout(total=OPENROUTER_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers=self._headers,
                    json=payload,
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        _LOGGER.error(
                            "OpenRouter error (HTTP %d): %s", resp.status, text
                        )
                        return f"Sorry, I couldn't reach the LLM service right now. (Error {resp.status})"

                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]

            except TimeoutError:
                _LOGGER.error("OpenRouter request timed out")
                return "The request timed out. Please try again."
            except Exception as e:
                _LOGGER.error("OpenRouter request failed: %s", e)
                return "Sorry, something went wrong processing your request."

    @staticmethod
    def _format_cards(card_yamls: list[dict[str, Any]]) -> str:
        """Format card YAML data into a concise text description for the prompt."""
        parts = []
        for i, card in enumerate(card_yamls, 1):
            name = card.get("name", card.get("id", f"Card {i}"))
            lines = [f"Card {i}: {name}"]

            if "rewards" in card and "base" in card["rewards"]:
                cats = []
                for cat, rate in card["rewards"]["base"].items():
                    cats.append(f"  {cat}: {rate}")
                if cats:
                    lines.append("  Rewards:")
                    lines.extend(cats)

            if "benefits" in card:
                active_benefits = [
                    b for b in card["benefits"]
                    if b.get("type", "").endswith("_credit")
                ]
                if active_benefits:
                    lines.append(f"  Credits ({len(active_benefits)}):")
                    for b in active_benefits:
                        freq = b.get("frequency", "")
                        amount = b.get("amount", "")
                        bname = b.get("name", "")
                        lines.append(f"    - {bname}: ${amount} {freq}")

            parts.append("\n".join(lines))

        return "\n\n".join(parts)
```

**Step 2: Commit**

```bash
git add [HA_CONFIG]/custom_components/credit_advisor/llm_client.py
git commit -m "feat: add OpenRouter LLM client for card queries"
```

---

### Task 4: Register Sensor Platform for Dashboard Integration

**Objective:** Create the sensor that feeds the LLM query response into a Lovelace-markdown-displayable entity.

**Files:**
- Create: `[HA_CONFIG]/custom_components/credit_advisor/sensor.py`

**Step 1: Write sensor platform**

```python
"""Sensor platform for Credit Advisor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN, ATTR_RESPONSE, ATTR_ERROR

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the credit advisor sensor."""
    async_add_entities([CreditResponseSensor(hass)])


class CreditResponseSensor(SensorEntity):
    """Sensor that holds the last LLM query response.

    Updated by automation calling credit_advisor.query service.
    Displayed in Lovelace via a markdown card.
    """

    _attr_name = "Credit Advisor Response"
    _attr_unique_id = "credit_advisor_response"
    _attr_icon = "mdi:credit-card-outline"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__()
        self._attr_native_value = "Ask a question to get started."
        self._attr_extra_state_attributes = {}

    async def async_set_response(self, response: str, attributes: dict[str, Any] | None = None) -> None:
        """Update the sensor state from a query result."""
        self._attr_native_value = response
        self._attr_extra_state_attributes = attributes or {}
        self.async_write_ha_state()
```

**Step 2: Update  `__init__.py` to expose the sensor**

Modify the `handle_query` in `__init__.py` to also update the sensor. Replace `async_setup`:

```python
# In __init__.py, add after the sensor is discovered:
# The sensor platform handles this via listening to events.
# We need to expose it so _async_query can push updates.

# Add this import at top of __init__.py
# (already there from sensor platform registration)
```

Actually, a simpler approach: the sensor platform registers the entity, and the query service updates it via a helper. Let me update the sensor to be discoverable by the service.

Modify `sensor.py` to add a simple registry:

```python
"""Sensor platform for Credit Advisor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSOR_INSTANCE: "CreditResponseSensor | None" = None


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the credit advisor sensor."""
    global SENSOR_INSTANCE  # noqa: PLW0603
    SENSOR_INSTANCE = CreditResponseSensor()
    async_add_entities([SENSOR_INSTANCE])


@callback
def update_response(response: str) -> None:
    """Update the sensor with a new LLM response."""
    global SENSOR_INSTANCE  # noqa: PLW0603
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

Now update `_async_query` in `__init__.py` to call `update_response`:

```python
# Add import
from .sensor import update_response

# In _async_query, before returning:
update_response(response)
```

**Step 3: Commit**

```bash
git add [HA_CONFIG]/custom_components/credit_advisor/sensor.py
git add [HA_CONFIG]/custom_components/credit_advisor/__init__.py
git commit -m "feat: add response sensor for Lovelace dashboard integration"
```

---

### Task 5: Configure Lovelace Dashboard

**Objective:** Set up the Lovelace view with input_text, button, and markdown card for the query interface.

**Files:**
- Modify: `[HA_CONFIG]/configuration.yaml` (add credit_advisor config + automation)
- Create: Lovelace dashboard configuration (via HA UI or YAML)

**Step 1: Add credit_advisor to `configuration.yaml`**

```yaml
# configuration.yaml

credit_advisor:
  openrouter_api_key: "sk-or-v1-YOUR_OPENROUTER_KEY_HERE"
  openrouter_model: "openai/gpt-4o-mini"
```

**Step 2: Add automation for the query button**

```yaml
# automations.yaml or a new file in automations/

- id: "credit_advisor_query"
  alias: "Credit Advisor — Process Query"
  trigger:
    - platform: state
      entity_id: input_button.credit_ask
  action:
    - service: credit_advisor.query
      data:
        text: "{{ states('input_text.credit_query') }}"
    - delay:
        seconds: 1
    - service: notify.notify
      data:
        message: "{{ state_attr('sensor.credit_advisor_response', 'native_value') }}"
```

Wait, the sensor's state IS the response. The user will see it in the markdown card. Let me simplify:

```yaml
# automations.yaml

- id: "credit_advisor_query"
  alias: "Credit Advisor — Process Query"
  trigger:
    - platform: state
      entity_id: input_button.credit_ask
      to: "pressed"
  action:
    - service: credit_advisor.query
      data:
        text: "{{ states('input_text.credit_query') }}"
```

**Step 3: Create Lovelace view**

Via the HA UI (Edit Dashboard → Add View) or via YAML dashboard:

```yaml
# In your dashboard YAML (raw config editor):
views:
  - title: Credit Advisor
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

But wait, we need to create the `input_text` and `input_button` entities first.

**Step 4: Add input helpers to `configuration.yaml`**

```yaml
# configuration.yaml

input_text:
  credit_query:
    name: What are you buying?
    icon: mdi:cart
    initial: ""

input_button:
  credit_ask:
    name: Ask the Advisor
    icon: mdi:send
```

**Step 5: Restart HA and test**

1. Restart Home Assistant
2. Open the Credit Advisor dashboard view
3. Type a query: "Chipotle $14"
4. Press "Ask the Advisor"
5. Observe the markdown card update with the recommendation

**Step 6: Commit**

```bash
git add [HA_CONFIG]/configuration.yaml
git add [HA_CONFIG]/automations.yaml
git commit -m "feat: add Lovelace dashboard for credit advisor queries"
```

---

## Configuration Summary

After all tasks, your `configuration.yaml` needs these additions:

```yaml
# Credit Advisor
credit_advisor:
  openrouter_api_key: "sk-or-v1-..."    # Replace with your actual key
  openrouter_model: "openai/gpt-4o-mini"

# Dashboard helpers
input_text:
  credit_query:
    name: What are you buying?
    icon: mdi:cart
    initial: ""

input_button:
  credit_ask:
    name: Ask the Advisor
    icon: mdi:send
```

Your HA automation (in `automations.yaml`):

```yaml
- id: "credit_advisor_query"
  alias: "Credit Advisor — Process Query"
  trigger:
    - platform: state
      entity_id: input_button.credit_ask
      to: "pressed"
  action:
    - service: credit_advisor.query
      data:
        text: "{{ states('input_text.credit_query') }}"
```

## Verification

After installation:
1. HA starts without errors in the logs
2. Developer Tools → Services shows `credit_advisor.query` and `credit_advisor.add_card`
3. Calling `credit_advisor.add_card` with `card_name: "Chase Sapphire Reserve"` creates a YAML file
4. Calling `credit_advisor.query` with `text: "flights to Tokyo"` returns a card recommendation
5. The Lovelace dashboard shows the query result in the markdown card
