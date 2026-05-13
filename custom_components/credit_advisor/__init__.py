"""The Credit Card Advisor integration."""

from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .card_registry import CardRegistry
from .const import DOMAIN, SERVICE_ADD_CARD, SERVICE_REMOVE_CARD

_LOGGER = logging.getLogger(__name__)


def _create_dir(path: Path) -> None:
    """Create directory safely."""
    path.mkdir(parents=True, exist_ok=True)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Credit Card Advisor from a config entry."""
    storage_path = (
        entry.data.get("storage_path")
        or entry.options.get("storage_path")
        or hass.config.path(DOMAIN)
    )

    path = Path(storage_path)
    await hass.async_add_executor_job(_create_dir, path)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["storage_path"] = str(path)

    card_registry = CardRegistry(hass, storage_path)
    hass.data[DOMAIN]["card_registry"] = card_registry

    async def handle_add_card(service_call: ServiceCall) -> None:
        """Handle the add_card service."""
        name = service_call.data["name"]

        try:
            result = await hass.services.async_call(
                "ai_task",
                "generate_data",
                {
                    "description": f"Research the credit card '{name}' and return a structured card profile.",
                    "structure": {
                        "card_name": "string — official issuer name (e.g. American Express Gold Card)",
                        "issuer": "string — bank or issuer name",
                        "annual_fee": "number — annual fee in USD, 0 if none",
                        "reward_categories": [
                            {
                                "category_name": "string — e.g. Dining, Travel, Groceries",
                                "rate": "number — e.g. 4 for 4x points per dollar",
                            }
                        ],
                        "base_reward_rate": "number — base earning rate (e.g. 1 for 1x points per dollar)",
                        "notes": "string — any other notable features",
                    },
                    "timeout": 30,
                },
                blocking=True,
                return_response=True,
            )
        except Exception as e:
            _LOGGER.warning("Failed to call ai_task for card '%s': %s", name, e)
            return

        card_data = dict(result)
        card_id = card_registry.slugify(name)
        await hass.async_add_executor_job(card_registry.save_card, card_id, card_data)
        _LOGGER.info("Successfully added card: %s", name)

    async def handle_remove_card(service_call: ServiceCall) -> None:
        """Handle the remove_card service."""
        card_name = service_call.data["card_name"]
        card_id = card_registry.slugify(card_name)

        deleted = await hass.async_add_executor_job(card_registry.delete_card, card_id)
        if deleted:
            _LOGGER.info("Successfully removed card: %s", card_name)
        else:
            _LOGGER.info("Card not found, could not remove: %s", card_name)

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_CARD,
        handle_add_card,
        schema=vol.Schema({vol.Required("name"): str}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_CARD,
        handle_remove_card,
        schema=vol.Schema({vol.Required("card_name"): str}),
    )

    _LOGGER.info("Credit Advisor integration started")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if DOMAIN in hass.data:
        hass.data.pop(DOMAIN)

    _LOGGER.info("Credit Advisor integration stopped")
    return True
