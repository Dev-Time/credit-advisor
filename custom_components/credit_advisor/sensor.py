"""Sensor platform for the Credit Card Advisor integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN


def _truncate_state(state: str) -> str:
    """Truncate a sensor state to the Home Assistant 255 character limit.

    The string is truncated to 252 characters and an ellipsis is added
    so the final string length is 253 characters.
    """
    return state[:252] + "…" if len(state) > 252 else state


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Credit Card Advisor sensors."""
    response_sensor = CreditResponseSensor(hass)
    registry_sensor = CreditCardRegistrySensor(hass)
    async_add_entities([response_sensor, registry_sensor], update_before_add=False)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["sensor"] = response_sensor
    hass.data[DOMAIN]["registry_sensor"] = registry_sensor


class CreditResponseSensor(SensorEntity, RestoreEntity):
    """Sensor that holds the last credit card query response."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:credit-card-outline"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the sensor."""
        super().__init__()
        self.hass = hass
        self._attr_unique_id = f"{DOMAIN}_response"
        self._attr_name = "Card Recommendation"
        self._attr_native_value = "No query yet"
        self._attr_extra_state_attributes: dict[str, Any] | None = None

    def update_response(self, response_text: str, query_description: str = "") -> None:
        """Update the sensor with a new query response.

        The sensor state is truncated to 255 chars (HA limit). The full
        response is stored in the ``full_response`` attribute.
        """
        self._attr_native_value = _truncate_state(response_text)
        self._attr_extra_state_attributes = {"full_response": response_text}
        if query_description:
            self._attr_extra_state_attributes["last_query"] = query_description
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore last state on startup."""
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in ("unknown", "unavailable", None):
            self._attr_native_value = _truncate_state(last_state.state)
        if last_state is not None and last_state.attributes:
            self._attr_extra_state_attributes = dict(last_state.attributes)
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes."""
        return self._attr_extra_state_attributes


class CreditCardRegistrySensor(SensorEntity, RestoreEntity):
    """Sensor that holds the list of registered credit cards."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:credit-card-multiple"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the sensor."""
        super().__init__()
        self.hass = hass
        self._attr_unique_id = f"{DOMAIN}_registry"
        self._attr_name = "Registered Cards"
        self._attr_native_value = "No cards registered"
        self._attr_extra_state_attributes: dict[str, Any] | None = None

    def update_cards(self, card_names: list[str]) -> None:
        """Update the sensor with the list of registered cards."""
        if card_names:
            self._attr_native_value = "\n".join(f"• {n}" for n in card_names)
        else:
            self._attr_native_value = "No cards registered"
        self._attr_extra_state_attributes = {"cards": card_names}
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore last state on startup."""
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in ("unknown", "unavailable", None):
            self._attr_native_value = _truncate_state(last_state.state)
        if last_state is not None and last_state.attributes:
            self._attr_extra_state_attributes = dict(last_state.attributes)
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes."""
        return self._attr_extra_state_attributes
