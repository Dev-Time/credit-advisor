"""The Credit Card Advisor integration."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError

from .card_registry import CardRegistry
from .const import DOMAIN, SERVICE_ADD_CARD, SERVICE_QUERY, SERVICE_REMOVE_CARD

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

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    async def handle_add_card(service_call: ServiceCall) -> None:
        """Handle the add_card service.

        If ``card_data`` is provided, save it directly (no LLM call).
        Otherwise, use the configured conversation agent to research the card.
        """
        name = service_call.data["name"]

        # If pre-researched card_data is provided, save directly
        if "card_data" in service_call.data:
            card_data = service_call.data["card_data"]
            if not isinstance(card_data, dict):
                _LOGGER.warning("card_data must be a dict for card '%s'", name)
                return
            card_id = card_registry.slugify(name)
            await hass.async_add_executor_job(card_registry.save_card, card_id, card_data)
            _LOGGER.info("Successfully added card with pre-researched data: %s", name)
            return

        agent_id = service_call.data.get("agent_id") or entry.options.get("agent_id")

        if not agent_id:
            _LOGGER.warning(
                "No agent_id provided and no default configured for add_card '%s'", name
            )
            return

        prompt = (
            f"Research the credit card '{name}' and return a JSON object with this shape:\n"
            "{\n"
            '  "card_name": "official card name",\n'
            '  "issuer": "issuing bank or company",\n'
            '  "annual_fee": 250,\n'
            '  "reward_categories": [\n'
            '    {"category_name": "Dining", "rate": 4},\n'
            '    {"category_name": "Travel", "rate": 3}\n'
            "  ],\n"
            '  "base_reward_rate": 1,\n'
            '  "notes": "notable features"\n'
            "}"
        )

        try:
            service_data = {
                "text": prompt,
            }
            if agent_id:
                service_data["agent_id"] = agent_id
            result = await hass.services.async_call(
                "conversation",
                "process",
                service_data,
                blocking=True,
                return_response=True,
            )
        except HomeAssistantError as e:
            _LOGGER.warning("Failed to call conversation.process for card '%s': %s", name, e)
            return
        except Exception as e:
            _LOGGER.warning(
                "Unexpected error calling conversation.process for card '%s': %s", name, e
            )
            return

        try:
            response_text = result["response"]["response"]["speech"]["plain"]["speech"]
        except (KeyError, TypeError) as e:
            _LOGGER.warning("Failed to extract response text for card '%s': %s", name, e)
            return

        # Strip markdown code blocks if present
        response_text = response_text.strip()
        if response_text.startswith("```"):
            # Extract JSON from markdown code block
            start = response_text.find("{")
            end = response_text.rfind("}")
            if start != -1 and end != -1:
                response_text = response_text[start : end + 1]

        try:
            card_data = json.loads(response_text)
        except json.JSONDecodeError:
            _LOGGER.warning(
                "Failed to parse JSON for card '%s'. Raw response: %s", name, response_text
            )
            return

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
        schema=vol.Schema(
            {
                vol.Required("name"): str,
                vol.Optional("agent_id"): str,
                vol.Optional("card_data"): dict,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_CARD,
        handle_remove_card,
        schema=vol.Schema({vol.Required("card_name"): str}),
    )

    async def handle_query(service_call: ServiceCall) -> None:
        """Handle the query service — ask the LLM for a card recommendation."""
        agent_id = service_call.data.get("agent_id") or entry.options.get("agent_id")
        purchase = service_call.data.get("purchase", "")

        if not agent_id:
            _LOGGER.warning("No agent_id configured for query service")
            return

        cards = await hass.async_add_executor_job(card_registry.list_cards)
        if not cards:
            _LOGGER.warning("No cards in registry — add some cards before querying")
            return

        card_summary = "\n".join(
            f"- {c.get('card_name', c.get('card_id', 'unknown'))}" for c in cards
        )

        purchase_context = ""
        if purchase:
            purchase_context = f"\nPurchase to evaluate: {purchase}\n"

        prompt = (
            "You are a credit card advisor. Given the following cards in the user's wallet,\n"
            f"Cards available:\n{card_summary}\n\n"
            f"{purchase_context}"
            "Recommend the best card and explain your reasoning concisely."
        )

        try:
            service_data = {
                "text": prompt,
            }
            if agent_id:
                service_data["agent_id"] = agent_id
            result = await hass.services.async_call(
                "conversation",
                "process",
                service_data,
                blocking=True,
                return_response=True,
            )
        except HomeAssistantError as e:
            _LOGGER.warning("Failed to call conversation.process for query: %s", e)
            return
        except Exception as e:
            _LOGGER.warning("Unexpected error calling conversation.process for query: %s", e)
            return

        try:
            response_text = result["response"]["response"]["speech"]["plain"]["speech"]
        except (KeyError, TypeError) as e:
            _LOGGER.warning("Failed to extract response text from query: %s", e)
            return

        sensor = hass.data.get(DOMAIN, {}).get("sensor")
        if sensor:
            sensor.update_response(response_text)

    hass.services.async_register(
        DOMAIN,
        SERVICE_QUERY,
        handle_query,
        schema=vol.Schema(
            {
                vol.Optional("agent_id"): str,
                vol.Optional("purchase"): str,
            }
        ),
    )

    async def handle_list_cards(service_call: ServiceCall) -> dict:
        cards = await hass.async_add_executor_job(card_registry.list_cards)
        card_names = [c.get("card_name", c.get("card_id", "unknown")) for c in cards]
        _LOGGER.info("Cards in registry: %s", card_names)
        return {"cards": card_names}

    hass.services.async_register(
        DOMAIN,
        "list_cards",
        handle_list_cards,
        schema=vol.Schema({}),
        supports_response=SupportsResponse.ONLY,
    )

    _LOGGER.info("Credit Advisor integration started")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if DOMAIN in hass.data:
        hass.data.pop(DOMAIN)

    _LOGGER.info("Credit Advisor integration stopped")
    return True
