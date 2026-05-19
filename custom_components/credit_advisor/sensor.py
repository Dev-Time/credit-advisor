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
    """Set up the Credit Card Advisor sensor."""
    sensor = CreditResponseSensor(hass)
    async_add_entities([sensor], update_before_add=False)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["sensor"] = sensor


class CreditResponseSensor(SensorEntity):
    """Sensor that holds the last credit card query response."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:credit-card-outline"
    _attr_native_value = "No query yet"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the sensor."""
        super().__init__()
        self.hass = hass
        self._attr_unique_id = f"{DOMAIN}_response"
        self._attr_name = "Card Recommendation"
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