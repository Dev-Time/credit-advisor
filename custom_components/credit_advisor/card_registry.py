import pathlib
import re

from homeassistant.core import HomeAssistant
from homeassistant.util.yaml import dump, load_yaml


class CardRegistry:
    """Registry to manage credit cards stored as YAML files."""

    def __init__(self, hass: HomeAssistant, storage_path: str) -> None:
        """Initialize the card registry."""
        self.hass = hass
        self._storage_path = pathlib.Path(storage_path)
        self._cards_dir = self._storage_path / "cards"
        self._cards_dir.mkdir(parents=True, exist_ok=True)

    def slugify(self, name: str) -> str:
        """Convert a name into a valid card id/filename slug."""
        name = name.lower().strip()
        name = name.replace(" ", "_")
        name = re.sub(r"[^a-z0-9_\-]", "", name)
        name = re.sub(r"[_\-]+", "_", name)
        return name

    def get_card_path(self, card_id: str) -> pathlib.Path:
        """Get the full path to a card's YAML file."""
        return self._cards_dir / f"{card_id}.yaml"

    def save_card(self, card_id: str, card_data: dict) -> None:
        """Save card data to a YAML file."""
        card_path = self.get_card_path(card_id)
        yaml_content = dump(
            card_data,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
        card_path.write_text(yaml_content, encoding="utf-8")

    def load_card(self, card_id: str) -> dict | None:
        """Load card data from a YAML file."""
        card_path = self.get_card_path(card_id)
        if not card_path.exists():
            return None
        return load_yaml(str(card_path))

    def delete_card(self, card_id: str) -> bool:
        """Delete a card's YAML file."""
        card_path = self.get_card_path(card_id)
        if card_path.exists():
            card_path.unlink()
            return True
        return False

    def list_cards(self) -> list[dict]:
        """List all cards in the registry."""
        if not self._cards_dir.exists():
            return []

        cards = []
        for file_path in self._cards_dir.glob("*.yaml"):
            card_data = load_yaml(str(file_path))
            if card_data is not None:
                card_data["card_id"] = file_path.stem
                cards.append(card_data)
        return cards
