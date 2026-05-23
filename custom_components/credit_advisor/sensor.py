"""Sensor platform for the Credit Card Advisor integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


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


class CreditResponseSensor(SensorEntity):
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
        """Update the sensor with a new query response."""
        self._attr_native_value = response_text
        self._attr_extra_state_attributes = {}
        if query_description:
            self._attr_extra_state_attributes["last_query"] = query_description
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes."""
        return self._attr_extra_state_attributes


class CreditCardRegistrySensor(SensorEntity):
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

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes."""
        return self._attr_extra_state_attributes
