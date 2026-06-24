"""Card registry storing credit cards as YAML files."""

from __future__ import annotations

import pathlib

import yaml
from homeassistant.core import HomeAssistant


class CardRegistry:
    """Registry to manage credit cards stored as YAML files."""

    def __init__(self, hass: HomeAssistant, storage_path: str) -> None:
        """Initialize the card registry."""
        self.hass = hass
        self._storage_path = pathlib.Path(storage_path)
        self._cards_dir = self._storage_path / "cards"
        self._cards_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, dict] | None = None

    def get_card_path(self, card_id: str) -> pathlib.Path:
        """Get the full path to a card's YAML file."""
        return self._cards_dir / f"{card_id}.yaml"

    def save_card(self, card_id: str, card_data: dict) -> None:
        """Save card data to a YAML file."""
        card_path = self.get_card_path(card_id)
        yaml_content = yaml.dump(
            card_data,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
        card_path.write_text(yaml_content, encoding="utf-8")

        if self._cache is not None:
            cached_data = card_data.copy()
            cached_data["card_id"] = card_id
            self._cache[card_id] = cached_data

    def load_card(self, card_id: str) -> dict | None:
        """Load card data from a YAML file."""
        if self._cache is not None:
            return self._cache.get(card_id)

        card_path = self.get_card_path(card_id)
        if not card_path.exists():
            return None
        with card_path.open(encoding="utf-8") as f:
            return yaml.safe_load(f)

    def delete_card(self, card_id: str) -> bool:
        """Delete a card's YAML file."""
        card_path = self.get_card_path(card_id)
        if card_path.exists():
            card_path.unlink()
            if self._cache is not None:
                self._cache.pop(card_id, None)
            return True
        return False

    def list_cards(self) -> list[dict]:
        """List all cards in the registry."""
        if self._cache is not None:
            return list(self._cache.values())

        if not self._cards_dir.exists():
            return []

        new_cache = {}
        for file_path in self._cards_dir.glob("*.yaml"):
            with file_path.open(encoding="utf-8") as f:
                card_data = yaml.safe_load(f)
            if card_data is not None:
                card_data["card_id"] = file_path.stem
                new_cache[file_path.stem] = card_data

        self._cache = new_cache
        return list(self._cache.values())
