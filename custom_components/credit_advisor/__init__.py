"""The Credit Card Advisor integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _create_dir(path: Path) -> None:
    """Create directory safely."""
    path.mkdir(parents=True, exist_ok=True)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Credit Card Advisor from a config entry."""
    storage_path = entry.options.get("storage_path")
    if not storage_path:
        storage_path = hass.config.path(DOMAIN)

    path = Path(storage_path)
    await hass.async_add_executor_job(_create_dir, path)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["storage_path"] = str(path)

    _LOGGER.info("Credit Advisor integration started")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if DOMAIN in hass.data:
        hass.data.pop(DOMAIN)

    _LOGGER.info("Credit Advisor integration stopped")
    return True
