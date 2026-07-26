"""Parse .psobank / .psoclassicbank share bank files."""

from typing import Any, Dict, Optional, Sequence

from character_viewer.config import Mode, ViewerConfig
from character_viewer.inventory_parser import InventoryParser
from price_guide.price_guide import PriceGuideAbstract


class BankParser:
    def __init__(self, config: ViewerConfig, price_guide: Optional[PriceGuideAbstract] = None):
        self.config = config
        self.inventory_parser = InventoryParser(config, price_guide)

    def parse(self, bank_data: Sequence[int], mode: Mode) -> Dict[str, Any]:
        data = list(bank_data)
        slot_label = "ShareBank" if mode == Mode.NORMAL else "ShareBank(Classic)"
        items = self.inventory_parser.parse_items(data[8:4808], 24, slot_label)
        self.inventory_parser.append_meseta(data[4:7], items, slot_label)
        total_pd = sum(float(entry[1].get("price") or 0) for entry in items)
        return {
            "slot": slot_label,
            "mode": int(mode),
            "mode_name": "CLASSIC" if mode == Mode.CLASSIC else "NORMAL",
            "bank": items,
            "total_pd": total_pd,
        }
