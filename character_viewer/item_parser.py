"""Parse individual PSO item binary records and attach price-guide values."""

from typing import Any, Dict, List, Optional, Sequence, Union

from character_viewer.config import AdditionType, AttributeType, ItemType, ViewerConfig
from character_viewer.util import binary_array_to_hex, int_to_hex, to_signed_byte
from price_guide.price_guide import PriceGuideAbstract, PriceGuideException


class ItemParser:
    def __init__(self, config: ViewerConfig, price_guide: Optional[PriceGuideAbstract] = None):
        self.config = config
        self.price_guide = price_guide

    def parse(self, item_data: Sequence[int], item_code: int) -> Dict[str, Any]:
        item_type = self.get_item_type(item_code)
        return self._parse_item(item_data, item_code, item_type)

    def get_item_type(self, item_code: int) -> int:
        if self.is_s_rank_weapon(item_code):
            return ItemType.SRANK_WEAPON
        if self.is_weapon(item_code):
            return ItemType.WEAPON
        if self.is_frame(item_code):
            return ItemType.FRAME
        if self.is_barrier(item_code):
            return ItemType.BARRIER
        if self.is_unit(item_code):
            return ItemType.UNIT
        if self.is_mag(item_code):
            return ItemType.MAG
        if self.is_disk(item_code):
            return ItemType.DISK
        if self.is_tool(item_code):
            return ItemType.TOOL
        return ItemType.OTHER

    def is_s_rank_weapon(self, item_code: int) -> bool:
        return (item_code & 0xFFF0) in self.config.SRANK_WEAPON_CODES

    def is_weapon(self, item_code: int) -> bool:
        return self.config.WEAPON_RANGE[0] <= item_code <= self.config.WEAPON_RANGE[1]

    def is_common_weapon(self, item_code: int) -> bool:
        return item_code in self.config.COMMON_WEAPON_CODES

    def is_frame(self, item_code: int) -> bool:
        return self.config.FRAME_RANGE[0] <= item_code <= self.config.FRAME_RANGE[1]

    def is_barrier(self, item_code: int) -> bool:
        return self.config.BARRIER_RANGE[0] <= item_code <= self.config.BARRIER_RANGE[1]

    def is_unit(self, item_code: int) -> bool:
        return self.config.UNIT_RANGE[0] <= item_code <= self.config.UNIT_RANGE[1]

    def is_mag(self, item_code: int) -> bool:
        return self.config.MAG_RANGE[0] <= item_code <= self.config.MAG_RANGE[1]

    def is_disk(self, item_code: int) -> bool:
        return (item_code >> 8) == self.config.DISK_CODE

    def is_tool(self, item_code: int) -> bool:
        if self.config.TOOL_RANGE[0] <= item_code <= self.config.TOOL_RANGE[1]:
            return True
        return self.config.EPHINEA_TOOL_RANGE[0] <= item_code <= self.config.EPHINEA_TOOL_RANGE[1]

    def _parse_item(self, item_data: Sequence[int], item_code: int, item_type: int) -> Dict[str, Any]:
        if item_type == ItemType.SRANK_WEAPON:
            return self.s_rank_weapon(item_code, item_data)
        if item_type == ItemType.WEAPON:
            return self.weapon(item_code, item_data)
        if item_type == ItemType.FRAME:
            return self.frame(item_code, item_data)
        if item_type == ItemType.BARRIER:
            return self.barrier(item_code, item_data)
        if item_type == ItemType.UNIT:
            return self.unit(item_code, item_data)
        if item_type == ItemType.MAG:
            return self.mag(item_code, item_data)
        if item_type == ItemType.DISK:
            return self.disk(item_code, item_data)
        if item_type == ItemType.TOOL:
            return self.tool(item_code, item_data)
        if item_type == ItemType.OTHER:
            return self.other(item_code, item_data)
        return {
            "name": f"unknown. ({int_to_hex(item_code)})",
            "guide_name": None,
            "type": int(ItemType.OTHER),
            "itemdata": binary_array_to_hex(item_data),
            "display": f"unknown. ({int_to_hex(item_code)})",
            "price": 0.0,
            "priced": False,
        }

    def weapon(self, item_code: int, item_data: Sequence[int]) -> Dict[str, Any]:
        name = self.get_item_name(item_code)
        grinder = item_data[3]
        native = self.get_native(item_data)
        a_beast = self.get_a_beast(item_data)
        machine = self.get_machine(item_data)
        dark = self.get_dark(item_data)
        hit = self.get_hit(item_data)
        is_common = self.is_common_weapon(item_code)

        element = ""
        if item_data[4] not in (0x00, 0x80):
            element = f" [{self.get_element(item_data)}]"

        tekked_mode = self.is_tekked(item_data)
        tekked_text = ""
        if not tekked_mode:
            tekked_text = "???? " if is_common else "? "

        weapon_attributes = {
            "N": native,
            "AB": a_beast,
            "M": machine,
            "D": dark,
        }
        price, priced = self._safe_price(
            lambda: self.price_guide.get_price_weapon(  # type: ignore[union-attr]
                name, weapon_attributes, hit, grinder, element.strip()
            )
        )

        return {
            "name": name,
            "guide_name": name,
            "type": int(ItemType.WEAPON),
            "itemdata": binary_array_to_hex(item_data),
            "element": element,
            "grinder": grinder,
            "attribute": {
                "native": native,
                "a_beast": a_beast,
                "machine": machine,
                "dark": dark,
                "hit": hit,
            },
            "tekked": tekked_mode,
            "rare": not is_common,
            "display": (
                f"{tekked_text}{name}{self.grinder_label(grinder)}{element} "
                f"[{native}/{a_beast}/{machine}/{dark}|{hit}]"
            ),
            "price": price,
            "priced": priced,
        }

    def frame(self, item_code: int, item_data: Sequence[int]) -> Dict[str, Any]:
        name = self.get_item_name(item_code)
        slot = item_data[5]
        defense = item_data[6]
        defense_max = self.get_addition(name, self.config.FRAME_ADDITIONS, AdditionType.DEF)
        avoid = item_data[8]
        avoid_max = self.get_addition(name, self.config.FRAME_ADDITIONS, AdditionType.AVOID)
        addition = {"def": defense, "avoid": avoid}
        max_addition = {"def": defense_max, "avoid": avoid_max}

        price, priced = self._safe_price(
            lambda: self.price_guide.get_price_frame(  # type: ignore[union-attr]
                name, addition, max_addition, slot
            )
        )

        return {
            "name": name,
            "guide_name": name,
            "type": int(ItemType.FRAME),
            "itemdata": binary_array_to_hex(item_data),
            "slot": slot,
            "status": {"def": defense, "avoid": avoid},
            "addition": addition,
            "max_addition": max_addition,
            "display": f"{name} [{defense}/{defense_max}|{avoid}/{avoid_max}] [{slot}S]",
            "price": price,
            "priced": priced,
        }

    def barrier(self, item_code: int, item_data: Sequence[int]) -> Dict[str, Any]:
        name = self.get_item_name(item_code)
        defense = item_data[6]
        defense_max = self.get_addition(name, self.config.BARRIER_ADDITIONS, AdditionType.DEF)
        avoid = item_data[8]
        avoid_max = self.get_addition(name, self.config.BARRIER_ADDITIONS, AdditionType.AVOID)
        addition = {"def": defense, "avoid": avoid}
        max_addition = {"def": defense_max, "avoid": avoid_max}

        price, priced = self._safe_price(
            lambda: self.price_guide.get_price_barrier(  # type: ignore[union-attr]
                name, addition, max_addition
            )
        )

        return {
            "name": name,
            "guide_name": name,
            "type": int(ItemType.BARRIER),
            "itemdata": binary_array_to_hex(item_data),
            "addition": addition,
            "max_addition": max_addition,
            "display": f"{name} [{defense}/{defense_max}|{avoid}/{avoid_max}]",
            "price": price,
            "priced": priced,
        }

    def unit(self, item_code: int, item_data: Sequence[int]) -> Dict[str, Any]:
        name = self.get_item_name(item_code)
        price, priced = self._safe_price(lambda: self.price_guide.get_price_unit(name))  # type: ignore[union-attr]
        return {
            "name": name,
            "guide_name": name,
            "type": int(ItemType.UNIT),
            "display": name,
            "itemdata": binary_array_to_hex(item_data),
            "price": price,
            "priced": priced,
        }

    def mag(self, item_code: int, item_data: Sequence[int]) -> Dict[str, Any]:
        name = self.get_item_name(item_code & 0xFFFF00)
        level = item_data[2]
        sync = item_data[16]
        iq = item_data[17]
        color_entry = self.config.MAG_COLOR_CODES.get(item_data[19], ["#000000", "undefined"])
        color_rgb, color_name = color_entry[0], color_entry[1]
        defense = (item_data[5] << 8 | item_data[4]) / 100
        pow_ = (item_data[7] << 8 | item_data[6]) / 100
        dex = (item_data[9] << 8 | item_data[8]) / 100
        mind = (item_data[11] << 8 | item_data[10]) / 100
        pbs = self.get_pbs(binary_array_to_hex([item_data[3], item_data[18]]))
        price, priced = self._safe_price(
            lambda: self.price_guide.get_price_mag(name, level)  # type: ignore[union-attr]
        )

        return {
            "name": f"{name} LV{level} [{color_name}]",
            "guide_name": name,
            "type": int(ItemType.MAG),
            "itemdata": binary_array_to_hex(item_data),
            "level": level,
            "sync": sync,
            "iq": iq,
            "color": color_name,
            "rgb": color_rgb,
            "status": {"def": defense, "pow": pow_, "dex": dex, "mind": mind},
            "pbs": [pbs[0], pbs[1], pbs[2]],
            "display": (
                f"{name} LV{level} [{color_name}] [{defense}/{pow_}/{dex}/{mind}] "
                f"[{pbs[2]}|{pbs[0]}|{pbs[1]}]"
            ),
            "price": price,
            "priced": priced,
        }

    def disk(self, item_code: int, item_data: Sequence[int]) -> Dict[str, Any]:
        name = self.config.DISK_NAME_CODES.get(item_data[4], "undefined")
        level = item_data[2] + 1
        display_text = f"{name} LV{level} {self.config.DISK_NAME_LANGUAGE}"
        price, priced = self._safe_price(
            lambda: self.price_guide.get_price_disk(name, level)  # type: ignore[union-attr]
        )
        return {
            "name": display_text,
            "guide_name": name,
            "type": int(ItemType.DISK),
            "itemdata": binary_array_to_hex(item_data),
            "level": level,
            "display": display_text,
            "price": price,
            "priced": priced,
        }

    def s_rank_weapon(self, item_code: int, item_data: Sequence[int]) -> Dict[str, Any]:
        custom_name = self.get_custom_name(list(item_data[6:12]))
        weapon_kind = self.config.SRANK_WEAPON_CODES.get(item_code & 0xFFFF00, "UNKNOWN")
        name = f"S-RANK {custom_name} {weapon_kind}".strip()
        grinder = item_data[3]
        element = self.get_srank_element(item_data)
        # Price guide keys are "ES NEEDLE" + modifier from the S-rank special byte
        # (element), not the player-engraved custom name.
        guide_weapon = f"ES {weapon_kind}"
        ability = element
        price, priced = self._safe_price(
            lambda: self.price_guide.get_price_srank_weapon(  # type: ignore[union-attr]
                guide_weapon, ability, grinder, element
            )
        )
        return {
            "name": name,
            "guide_name": guide_weapon,
            "type": int(ItemType.SRANK_WEAPON),
            "itemdata": binary_array_to_hex(item_data),
            "grinder": grinder,
            "element": element,
            "ability": ability,
            "display": f"{name}{self.grinder_label(grinder)} [{element}]",
            "price": price,
            "priced": priced,
        }

    def tool(self, item_code: int, item_data: Sequence[int]) -> Dict[str, Any]:
        name = self.get_item_name(item_code)
        number = item_data[5] if len(item_data) == 28 else item_data[20]
        qty = number if number and number > 0 else 1
        price, priced = self._price_stackable(name, qty)
        return {
            "name": name,
            "guide_name": name,
            "type": int(ItemType.TOOL),
            "itemdata": binary_array_to_hex(item_data),
            "number": number,
            "display": f"{name}{self.number_label(number)}",
            "price": price,
            "priced": priced,
        }

    def other(self, item_code: int, item_data: Sequence[int]) -> Dict[str, Any]:
        name = self.get_item_name(item_code)
        number = item_data[5] if len(item_data) == 28 else item_data[20]
        # Ephinea currencies / materials (0x031xxx) fall outside classic TOOL_RANGE
        qty = number if number and number > 0 else 1
        price, priced = self._price_stackable(name, qty)
        return {
            "name": name,
            "guide_name": name,
            "type": int(ItemType.OTHER),
            "itemdata": binary_array_to_hex(item_data),
            "number": number,
            "display": f"{name}{self.number_label(number)}",
            "price": price,
            "priced": priced,
        }

    def _price_stackable(self, name: str, qty: int) -> tuple[float, bool]:
        """Price a stackable via tools, then cells (price guide only)."""
        price, priced = self._safe_price(
            lambda: self.price_guide.get_price_tool(name, qty)  # type: ignore[union-attr]
        )
        if priced:
            return price, True
        price, priced = self._safe_price(
            lambda: self.price_guide.get_price_cell(name) * qty  # type: ignore[union-attr]
        )
        return price, priced

    def get_item_name(self, item_code: int) -> str:
        if item_code in self.config.ITEM_CODES:
            return self.config.ITEM_CODES[item_code]
        return f"undefined. ({int_to_hex(item_code)})"

    def get_element(self, item_data: Sequence[int]) -> str:
        return self.config.ELEMENT_CODES.get(item_data[4], "undefined")

    def get_srank_element(self, item_data: Sequence[int]) -> str:
        return self.config.SRANK_ELEMENT_CODES.get(item_data[2], "undefined")

    def get_native(self, item_data: Sequence[int]) -> int:
        return self.get_attribute(AttributeType.NATIVE, item_data)

    def get_a_beast(self, item_data: Sequence[int]) -> int:
        return self.get_attribute(AttributeType.A_BEAST, item_data)

    def get_machine(self, item_data: Sequence[int]) -> int:
        return self.get_attribute(AttributeType.MACHINE, item_data)

    def get_dark(self, item_data: Sequence[int]) -> int:
        return self.get_attribute(AttributeType.DARK, item_data)

    def get_hit(self, item_data: Sequence[int]) -> int:
        return self.get_attribute(AttributeType.HIT, item_data)

    def get_attribute(self, attribute_type: int, item_data: Sequence[int]) -> int:
        attributes = [
            item_data[6:8],
            item_data[8:10],
            item_data[10:12],
        ]
        for attribute in attributes:
            if attribute[0] == attribute_type:
                return to_signed_byte(attribute[1])
        return 0

    def get_addition(self, name: str, additions: Dict, type_: int) -> Union[int, str]:
        if name in additions:
            return additions[name][type_]
        return "undefined"

    def is_tekked(self, item_data: Sequence[int]) -> bool:
        return item_data[4] < 0x80

    def get_pbs(self, pbs_code: str) -> List[str]:
        if pbs_code in self.config.PBS:
            return list(self.config.PBS[pbs_code])
        return ["undefined", "undefined", "undefined"]

    def number_label(self, number: int) -> str:
        if number == 1:
            return ""
        if number > 0:
            return f" x{number}"
        return ""

    def grinder_label(self, number: int) -> str:
        if number > 0:
            return f" +{number}"
        return ""

    def get_custom_name(self, custom_name_data: List[int]) -> str:
        data = list(custom_name_data)
        if not data or data[0] == 0:
            return ""
        data[0] -= 0x04
        temp: List[int] = []
        temp.extend(self.three_letters(data[0:2]))
        temp.extend(self.three_letters(data[2:4]))
        temp.extend(self.three_letters(data[4:6]))
        return "".join(chr(value + 64) for value in temp if value != 0)

    def three_letters(self, array: List[int]) -> List[int]:
        arr = list(array)
        arr[0] = arr[0] - 0x80
        first = arr[0] // 0x04
        second = ((arr[0] % 0x04) << 8 | arr[1]) // 0x20
        third = arr[1] % 0x20
        return [first, second, third]

    def _safe_price(self, fn) -> tuple[float, bool]:
        if self.price_guide is None:
            return 0.0, False
        try:
            value = fn()
            return float(value or 0.0), True
        except PriceGuideException:
            return 0.0, False
        except Exception:
            return 0.0, False
