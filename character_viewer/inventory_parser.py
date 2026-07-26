"""Parse inventory / bank item strips from character binaries."""

from typing import Any, Dict, List, Optional, Sequence

from character_viewer.config import ItemType, ViewerConfig
from character_viewer.item_parser import ItemParser
from character_viewer.util import binary_array_to_hex, binary_array_to_int
from price_guide.price_guide import PriceGuideAbstract


class InventoryParser:
    def __init__(self, config: ViewerConfig, price_guide: Optional[PriceGuideAbstract] = None):
        self.config = config
        self.item_parser = ItemParser(config, price_guide)

    def parse_items(
        self,
        items_data: Sequence[int],
        item_length: int,
        slot_label: str,
    ) -> List[List[Any]]:
        """Return list of [hex_code, item_dict, slot_label]."""
        array: List[List[Any]] = []
        for i in range(0, len(items_data), item_length):
            item_data = list(items_data[i : i + item_length])
            if len(item_data) < item_length:
                break
            if self.is_blank(item_data):
                continue
            item_code = binary_array_to_int(item_data[:3])
            item_code_hex = binary_array_to_hex(item_data[:3])
            item = self.item_parser.parse(item_data, item_code)
            array.append([item_code_hex, item, slot_label])
        return array

    def append_meseta(
        self,
        meseta_data: Sequence[int],
        inventory: List[List[Any]],
        slot_label: str,
    ) -> None:
        meseta = ((meseta_data[2] << 8 | meseta_data[1]) << 8) | meseta_data[0]
        item: Dict[str, Any] = {
            "type": int(ItemType.MESETA),
            "name": "MESETA",
            "guide_name": None,
            "value": meseta,
            "display": f"{meseta} MESETA",
            "price": 0.0,
            "priced": False,
        }
        inventory.append(
            [
                "09" + str(meseta).zfill(7),
                item,
                slot_label,
            ]
        )

    def is_blank(self, item_data: Sequence[int]) -> bool:
        hex_data = binary_array_to_hex(item_data)
        return (
            sum(item_data[:20]) == 0
            or hex_data == "000000000000000000000000FFFFFFFF0000000000000000"
            or "00FF00000000000000000000FFFFFFFF" in hex_data
        )
