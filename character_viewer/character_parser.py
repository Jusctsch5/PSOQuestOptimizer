"""Parse .psochar character files (JS-aligned offsets)."""

from typing import Any, Dict, Optional, Sequence

from character_viewer.config import Mode, ViewerConfig
from character_viewer.inventory_parser import InventoryParser
from price_guide.price_guide import PriceGuideAbstract


class CharacterParser:
    def __init__(self, config: ViewerConfig, price_guide: Optional[PriceGuideAbstract] = None):
        self.config = config
        self.inventory_parser = InventoryParser(config, price_guide)

    def parse(self, character_data: Sequence[int], slot: int) -> Dict[str, Any]:
        data = list(character_data)
        mode = Mode.CLASSIC if data[7] == 0x40 else Mode.NORMAL
        name = self._parse_name(data[968:988])
        guild_card_number = self._parse_guild_card_number(data[888:896])
        character_class = self.config.CLASSES.get(data[937], "undefined")
        section_id = self.config.SECTION_IDS.get(data[936], "undefined")
        level = data[876] + 1
        experience = 0  # Not decoded by reference viewer either

        slot_label = str(slot)
        bank_label = f"{slot} Bank"

        inventory = self.inventory_parser.parse_items(data[20:860], 28, slot_label)
        self.inventory_parser.append_meseta(data[884:887], inventory, slot_label)

        bank = self.inventory_parser.parse_items(data[1800:6600], 24, bank_label)
        self.inventory_parser.append_meseta(data[1795:1799], bank, bank_label)

        inv_total = sum(float(entry[1].get("price") or 0) for entry in inventory)
        bank_total = sum(float(entry[1].get("price") or 0) for entry in bank)

        return {
            "slot": slot,
            "name": name,
            "mode": int(mode),
            "mode_name": "CLASSIC" if mode == Mode.CLASSIC else "NORMAL",
            "guild_card_number": guild_card_number,
            "character_class": character_class,
            "section_id": section_id,
            "level": level,
            "experience": experience,
            "inventory": inventory,
            "bank": bank,
            "inventory_pd": inv_total,
            "bank_pd": bank_total,
            "total_pd": inv_total + bank_total,
        }

    def _parse_name(self, array: Sequence[int]) -> str:
        name = ""
        for i in range(0, len(array), 2):
            if array[i] + array[i + 1] == 0:
                break
            name += chr((array[i + 1] << 8) | array[i])
        return name

    def _parse_guild_card_number(self, array: Sequence[int]) -> str:
        return "".join(str(value & 0x0F) for value in array)
