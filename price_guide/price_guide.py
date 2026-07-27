"""
Front-end wrapper for the price guide data.
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from bisect import bisect
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class BasePriceStrategy(Enum):
    MINIMUM = "MINIMUM"
    AVERAGE = "AVERAGE"
    MAXIMUM = "MAXIMUM"


class ItemType(Enum):
    """Enumeration of item types in the price guide."""

    SRANK_WEAPON = "srank_weapon"
    WEAPON = "weapon"
    COMMON_WEAPON = "common_weapon"
    FRAME = "frame"
    BARRIER = "barrier"
    UNIT = "unit"
    MAG = "mag"
    CELL = "cell"
    DISK = "disk"
    TOOL = "tool"


FIT_INESTIMABLE_PRICE = True

HIGH_ATTRIBUTE_THRESHOLD = 50


class PriceGuideException(Exception):
    pass


class PriceGuideExceptionItemNameNotFound(PriceGuideException):
    pass


class PriceGuideExceptionAbilityNameNotFound(PriceGuideException):
    pass


class PriceGuideParseException(PriceGuideException):
    pass


class CannotInferBasePriceException(PriceGuideException):
    pass


class PriceGuideAbstract(ABC):
    def __init__(self, base_price_strategy: BasePriceStrategy = BasePriceStrategy.MINIMUM) -> None:
        self.bps = base_price_strategy
        self.srank_weapon_prices: Dict[str, Any] = {}
        self.weapon_prices: Dict[str, Any] = {}
        self.common_weapon_prices: Dict[str, Any] = {}
        self.frame_prices: Dict[str, Any] = {}
        self.barrier_prices: Dict[str, Any] = {}
        self.unit_prices: Dict[str, Any] = {}
        self.mag_prices: Dict[str, Any] = {}
        self.cell_prices: Dict[str, Any] = {}
        self.techniques_prices: Dict[str, Any] = {}
        self.tool_prices: Dict[str, Any] = {}
        self.meseta_prices: Dict[str, Any] = {}

    @staticmethod
    # Parse out the price range value from the price range dictionary
    def get_price_from_range(price_range: Union[str, int, float, None], bps: BasePriceStrategy) -> float:
        # JSON occasionally stores bare numbers (e.g. JIZAI base: 2)
        if isinstance(price_range, (int, float)) and not isinstance(price_range, bool):
            return float(price_range)

        # Handle None or empty string
        if not price_range or str(price_range).strip() == "":
            return 0.0

        price_range = str(price_range).strip()

        # Handle special values first
        if price_range.upper() in ["N/A", "NA", "INESTIMABLE", "INEST"]:
            return 0.0

        # Handle "4800+" format - use the base value
        if price_range.endswith("+"):
            try:
                price_value = float(price_range.rstrip("+").strip())
                return price_value
            except ValueError:
                return 0.0

        # Handle range format "min-max"
        if "-" in price_range:
            parts = price_range.split("-")
            if len(parts) == 2:
                min_str, max_str = parts[0].strip(), parts[1].strip()
                # Check for empty strings
                if not min_str or not max_str:
                    return 0.0
                try:
                    min_price = float(min_str)
                    max_price = float(max_str)
                    average_price = (min_price + max_price) / 2

                    # Perform the price calculation based on the BasePriceStrategy
                    if bps == BasePriceStrategy.MINIMUM:
                        return min_price
                    elif bps == BasePriceStrategy.MAXIMUM:
                        return max_price
                    else:  # AVERAGE
                        return average_price
                except ValueError:
                    return 0.0
            else:
                # Malformed range (multiple dashes or empty parts)
                return 0.0

        # Try to parse as a single number
        try:
            price_value = float(price_range)
            return price_value
        except ValueError:
            # If all else fails, return 0.0 instead of raising exception
            return 0.0

    @staticmethod
    def get_price_for_item_range(price_range: str, number: int, bps: BasePriceStrategy) -> float:
        return PriceGuideAbstract.get_price_from_range(price_range, bps) * number

    @abstractmethod
    def build_prices(self) -> None:
        """Build the price database from the source"""
        pass

    @staticmethod
    def _ci_key(mapping: Dict[str, Any], name: str) -> Optional[str]:
        """Case-insensitive lookup returning the actual key from the mapping.

        Also treats ``FOO:BAR`` and ``FOO: BAR`` as the same (Ephinea guide spacing).
        """
        if name in mapping:
            return name
        candidates = {name.upper(), re.sub(r":\s*", ": ", name.upper()), re.sub(r":\s*", ":", name.upper())}
        for key in mapping.keys():
            key_u = key.upper()
            if key_u in candidates:
                return key
            key_spaced = re.sub(r":\s*", ": ", key_u)
            key_tight = re.sub(r":\s*", ":", key_u)
            if key_spaced in candidates or key_tight in candidates:
                return key
        return None

    def get_price_srank_weapon(
        self,
        name: str,
        ability: str,
        grinder: int,
        element: str,
    ) -> float:
        """Get price for S-rank / ES weapon.

        ``name`` may be an ES guide key (``ES NEEDLE``), a bare kind (``NEEDLE``),
        or a character-viewer display name (``S-RANK ARREST NEEDLE``).
        ``ability`` / ``element`` are special names looked up in modifiers (case-insensitive).
        """

        weapon_key = self._normalize_srank_weapon_name(name)
        actual_key = self._ci_key(self.srank_weapon_prices["weapons"], weapon_key)

        if actual_key is None:
            raise PriceGuideExceptionItemNameNotFound(f"Item name {name} not found in srank_weapon_prices")

        base_price = self.get_price_from_range(
            str(self.srank_weapon_prices["weapons"][actual_key]["base"]),
            self.bps,
        )

        ability_price = 0.0
        special = self._normalize_srank_special(ability or element or "")
        if special and special.lower() not in ("undefined", "unchanged/nothing", "nothing"):
            actual_ability = self._ci_key(self.srank_weapon_prices["modifiers"], special)
            if actual_ability is None:
                raise PriceGuideExceptionAbilityNameNotFound(f"Ability {special} not found in srank_weapon_prices")
            ability_price = self.get_price_from_range(
                str(self.srank_weapon_prices["modifiers"][actual_ability]["base"]),
                self.bps,
            )

        return float(base_price) + float(ability_price)

    # Common-weapon specials that use the guide's "Elemental" bucket when not listed by name.
    _COMMON_ELEMENTAL_SPECIALS = frozenset(
        {
            "ICE",
            "FROST",
            "FREEZE",
            "BLIZZARD",
            "HEAT",
            "FIRE",
            "FLAME",
            "BURNING",
            "SHOCK",
            "THUNDER",
            "STORM",
            "TEMPEST",
            "DIM",
            "SHADOW",
            "DARK",
        }
    )

    def get_price_common_weapon(self, name: str, special: str, hit: int) -> float:
        """Price a common weapon from common_weapons.json (name + special + hit)."""
        logger.info(f"get_price_common_weapon: {name} {special} {hit}")
        weapon_specials = self._find_common_weapon_specials(name)
        if weapon_specials is None:
            raise PriceGuideExceptionItemNameNotFound(f"Item name {name} not found in common_weapon_prices")

        special_key = self._resolve_common_weapon_special(weapon_specials, special)
        if special_key is None:
            raise PriceGuideExceptionAbilityNameNotFound(
                f"Special {special!r} not found for common weapon {name}"
            )

        hit_values = weapon_specials[special_key]
        if not hit_values:
            return 0.0

        sorted_thresholds = sorted(map(int, hit_values.keys()))
        index = bisect(sorted_thresholds, int(hit)) - 1
        if index < 0:
            return 0.0

        threshold = sorted_thresholds[index]
        return float(self.get_price_from_range(str(hit_values[str(threshold)]), self.bps))

    def _find_common_weapon_specials(self, name: str) -> Optional[Dict[str, Any]]:
        """Locate a common weapon's special→hit map across category buckets."""
        for category_weapons in self.common_weapon_prices.values():
            if not isinstance(category_weapons, dict):
                continue
            key = self._ci_key(category_weapons, name)
            if key is not None:
                entry = category_weapons[key]
                return entry if isinstance(entry, dict) else None
        return None

    def _resolve_common_weapon_special(self, specials: Dict[str, Any], special: str) -> Optional[str]:
        """Match a game special name onto a common_weapons.json special key."""
        raw = (special or "").strip()
        if raw.lower() in ("", "undefined", "unchanged/nothing", "nothing"):
            return self._ci_key(specials, "None or Any")

        key = self._ci_special_key(specials, raw)
        if key is not None:
            return key

        if raw.upper() in self._COMMON_ELEMENTAL_SPECIALS:
            key = self._ci_key(specials, "Elemental")
            if key is not None:
                return key

        return self._ci_key(specials, "None or Any")

    @staticmethod
    def _ci_special_key(mapping: Dict[str, Any], name: str) -> Optional[str]:
        """Case-insensitive special lookup; apostrophes optional (Demon's / Demons)."""
        key = PriceGuideAbstract._ci_key(mapping, name)
        if key is not None:
            return key
        target = re.sub(r"['’]", "", name.upper())
        for candidate in mapping.keys():
            if re.sub(r"['’]", "", candidate.upper()) == target:
                return candidate
        return None

    @staticmethod
    def _normalize_srank_special(special: str) -> str:
        """Map game S-rank special labels onto srankweapons.json modifier keys."""
        raw = (special or "").strip()
        if not raw:
            return raw
        upper = raw.upper()
        # Game element codes say "HP Regeneration"; guide uses "HP REVIVAL"
        return upper.replace("REGENERATION", "REVIVAL")

    @staticmethod
    def _normalize_srank_weapon_name(name: str) -> str:
        """Map display / kind names onto srankweapons.json keys like ``ES NEEDLE``."""
        raw = (name or "").strip()
        if not raw:
            return raw

        upper = raw.upper()
        # "S-RANK ARREST NEEDLE" / "S-RANK NEEDLE" -> last token(s) as kind
        if upper.startswith("S-RANK "):
            parts = upper[len("S-RANK ") :].split()
            if not parts:
                return raw
            # Custom special is usually one token; weapon kind is the remainder
            # e.g. ARREST NEEDLE, HP REVIVAL would be unusual as multi-word custom
            kind = parts[-1]
            # Multi-token kinds in codes: J-BLADE, J-CUTTER (hyphenated single token)
            if len(parts) >= 2 and parts[-2] in ("J",):
                kind = f"{parts[-2]}-{parts[-1]}"
            upper = kind

        if upper.startswith("ES "):
            return upper
        return f"ES {upper}"

    def get_price_weapon(
        self,
        name: str,
        weapon_attributes: Dict,
        hit: int,
        grinder: int,
        element: str,
        item_data: Optional[Dict] = None,
    ) -> float:
        """Get price for normal weapon"""

        special = (element or "").strip().strip("[]").strip()
        # Type* weapons store special as a name prefix in the guide
        # (e.g. CHARGE TYPEGU/HAND), so prefer that key when present.
        candidates = []
        if special and special.lower() not in ("undefined", "unchanged/nothing", "nothing"):
            candidates.append(f"{special} {name}")
        candidates.append(name)

        actual_key = None
        for candidate in candidates:
            actual_key = self._ci_key(self.weapon_prices, candidate)
            if actual_key is not None:
                break

        if actual_key is None:
            raise PriceGuideExceptionItemNameNotFound(f"Item name {name} not found in weapon_prices")

        base_price_str = self.weapon_prices[actual_key].get("base")
        hit_values = self.weapon_prices[actual_key].get("hit_values", {})

        if base_price_str is None:
            # If no base price, use 0-hit price as base when present; otherwise
            # hit-tier rows alone provide value (e.g. HANDGUN: MILLA starts at 15).
            if hit_values and "0" in hit_values:
                base_price = self.get_price_from_range(hit_values["0"], self.bps)
            elif hit_values:
                base_price = 0.0
            else:
                raise CannotInferBasePriceException(
                    f"Cannot infer base price for weapon '{name}': base is null and no hit values found"
                )
        else:
            base_price = self.get_price_from_range(base_price_str, self.bps)

        if weapon_attributes:
            modifiers = self.weapon_prices[actual_key].get("modifiers", {})
            for attribute, value in weapon_attributes.items():
                if value > HIGH_ATTRIBUTE_THRESHOLD and attribute in modifiers:
                    ability_price_str = modifiers[attribute]
                    if ability_price_str and ability_price_str.upper() != "N/A":
                        ability_price = self.get_price_from_range(ability_price_str, self.bps)
                        base_price += ability_price

        if hit_values and hit > 0:
            # Convert string keys to integers and sort
            sorted_thresholds = sorted(map(int, hit_values.keys()))

            # Find the largest threshold <= actual hit value
            index = bisect(sorted_thresholds, hit) - 1

            if index >= 0:
                threshold = sorted_thresholds[index]
                price_range = hit_values[str(threshold)]
                hit_price = self.get_price_from_range(price_range, self.bps)
                base_price += hit_price

        return base_price

    def get_price_frame(
        self,
        name: str,
        addition: Dict[str, int],
        max_addition: Dict[str, int],
        slot: int,
        item_data: Optional[Dict] = None,
    ) -> float:
        """Get price for frame"""
        logger.info(f"get_price_frame: {name} {addition} {max_addition} {slot}")
        actual_key = self._ci_key(self.frame_prices, name)
        if actual_key is None:
            raise PriceGuideExceptionItemNameNotFound(f"Item name {name} not found in frame_prices")
        price_range = self.frame_prices[actual_key]["base"]
        base_price = self.get_price_from_range(price_range, self.bps)
        if slot > 0:
            base_price += self.get_price_tool("AddSlot", slot)

        return base_price

    def get_price_barrier(self, name: str, addition: Dict[str, int], max_addition: Dict[str, int]) -> float:
        """Get price for barrier"""
        logger.info(f"get_price_barrier: {name} {addition} {max_addition}")
        actual_key = self._ci_key(self.barrier_prices, name)
        if actual_key is None:
            raise PriceGuideExceptionItemNameNotFound(f"Item name {name} not found in barrier_prices")
        price_range = self.barrier_prices[actual_key]["base"]
        base_price = self.get_price_from_range(price_range, self.bps)

        return base_price

    def get_price_unit(self, name: str) -> float:
        """Get price for unit"""
        logger.info(f"get_price_unit: {name}")
        actual_key = self._ci_key(self.unit_prices, name)
        if actual_key is None:
            raise PriceGuideExceptionItemNameNotFound(f"Item name {name} not found in unit_prices")
        price_range = self.unit_prices[actual_key]["base"]
        return self.get_price_for_item_range(price_range, 1, self.bps)

    def get_price_mag(self, name: str, level: int) -> float:
        """Get price for mag"""
        logger.info(f"get_price_mag: {name} {level}")
        actual_key = self._ci_key(self.mag_prices, name)
        if actual_key is None:
            raise PriceGuideExceptionItemNameNotFound(f"Item name {name} not found in mag_prices")
        price_range = self.mag_prices[actual_key]["base"]
        return self.get_price_for_item_range(price_range, 1, self.bps)

    def get_price_disk(self, name: str, level: int) -> float:
        logger.info(f"get_price_disk: {name} {level}")

        # Look up technique in techniques_prices (techniques are disks)
        actual_key = self._ci_key(self.techniques_prices, name)
        if actual_key is None:
            raise PriceGuideExceptionItemNameNotFound(f"Item name {name} not found in techniques_prices")

        levels = self.techniques_prices[actual_key]
        # Convert string keys to integers and sort
        sorted_thresholds = sorted(map(int, levels.keys()))

        if not sorted_thresholds:
            # No levels defined for this technique
            return 0.0

        # Get the maximum level for this technique
        max_level = sorted_thresholds[-1]

        # If requested level is above the maximum, raise an exception
        if level > max_level:
            raise PriceGuideExceptionItemNameNotFound(f"Level {level} for technique '{name}' exceeds maximum level {max_level}")
        if level < 1:
            raise PriceGuideExceptionItemNameNotFound(f"Level {level} for technique '{name}' is below minimum level 1")

        # Find the largest threshold <= actual level value
        index = bisect(sorted_thresholds, level) - 1

        if index >= 0:
            threshold = sorted_thresholds[index]
            # Only return price if the level exactly matches a threshold
            # If level is between thresholds or below the first threshold, return 0 (worthless)
            if level != threshold:
                return 0.0
            price_range = levels[str(threshold)]
            price = self.get_price_from_range(price_range, self.bps)
            return price

        # If level not found but is within valid range (e.g., Foie level 10, which is between 0 and 15), return 0
        return 0.0

    def get_price_cell(self, name: str) -> float:
        """Get price for mag cells / cells.json items."""
        logger.info(f"get_price_cell: {name}")
        actual_key = self._ci_key(self.cell_prices, name)
        if actual_key is None:
            raise PriceGuideExceptionItemNameNotFound(f"Item name {name} not found in cell_prices")
        price_range = self.cell_prices[actual_key]["base"]
        return self.get_price_from_range(price_range, self.bps)

    def get_price_tool(self, name: str, number: int) -> float:
        """Get price for tool"""
        logger.info(f"get_price_tool: {name} {number}")
        # Check if the tool exists in the price database
        actual_key = self._ci_key(self.tool_prices, name)
        if actual_key is None:
            raise PriceGuideExceptionItemNameNotFound(f"Item name {name} not found in tool_prices")

        # Get the price range string
        price_range = self.tool_prices[actual_key]["base"]
        return self.get_price_for_item_range(price_range, number, self.bps)

    def get_price_other(self, name: str, number: int) -> float:
        """Get price for miscellaneous items (falls back to tools/cells)."""
        logger.info(f"get_price_other: {name} {number}")
        qty = number if number and number > 0 else 1
        try:
            return self.get_price_tool(name, qty)
        except PriceGuideExceptionItemNameNotFound:
            pass
        try:
            return self.get_price_cell(name) * qty
        except PriceGuideExceptionItemNameNotFound:
            pass
        raise PriceGuideExceptionItemNameNotFound(f"Item name {name} not found in tool/cell/other prices")

    def get_meseta_per_pd(self) -> float:
        """Meseta required for one PD from meseta.json (respects base price strategy)."""
        raw = str(self.meseta_prices.get("meseta_per_pd", "")).replace(",", "")
        return float(self.get_price_from_range(raw, self.bps))

    def get_price_meseta(self, amount: int) -> float:
        """Convert a meseta amount to PD using meseta.json exchange rate."""
        logger.info(f"get_price_meseta: {amount}")
        rate = self.get_meseta_per_pd()
        if rate <= 0:
            return 0.0
        return float(amount) / rate

    def identify_item_type(self, item_name: str) -> Optional[str]:
        """
        Identify the type of an item by checking all price guide categories.

        Args:
            item_name: Name of the item to check

        Returns:
            String representation of ItemType enum value, or None if not found
        """
        item_norm = item_name.strip()

        if self._ci_key(self.srank_weapon_prices["weapons"], item_norm):
            return ItemType.SRANK_WEAPON.value
        if self._find_common_weapon_specials(item_norm) is not None:
            return ItemType.COMMON_WEAPON.value
        if self._ci_key(self.weapon_prices, item_norm):
            return ItemType.WEAPON.value
        if self._ci_key(self.frame_prices, item_norm):
            return ItemType.FRAME.value
        if self._ci_key(self.barrier_prices, item_norm):
            return ItemType.BARRIER.value
        if self._ci_key(self.unit_prices, item_norm):
            return ItemType.UNIT.value
        if self._ci_key(self.mag_prices, item_norm):
            return ItemType.MAG.value
        if self._ci_key(self.cell_prices, item_norm):
            return ItemType.CELL.value
        if self._ci_key(self.tool_prices, item_norm):
            return ItemType.TOOL.value
        if self._ci_key(self.techniques_prices, item_norm):
            return ItemType.DISK.value
        return None

    def get_weapon_data(self, name: str) -> Dict[str, Any]:
        """Fetch for weapon price entry."""
        key = self._ci_key(self.weapon_prices, name)
        if key is None:
            raise PriceGuideExceptionItemNameNotFound(f"Item name {name} not found in weapon_prices")
        return self.weapon_prices[key]

    def get_common_weapon_data(self, name: str) -> Dict[str, Any]:
        """Fetch for common weapon price entry (special → hit map)."""
        entry = self._find_common_weapon_specials(name)
        if entry is None:
            raise PriceGuideExceptionItemNameNotFound(f"Item name {name} not found in common_weapon_prices")
        return entry


class PriceGuideFixed(PriceGuideAbstract):
    def __init__(self, directory: str, base_price_strategy: BasePriceStrategy = BasePriceStrategy.MINIMUM):
        super().__init__(base_price_strategy)
        self.directory = Path(directory)
        self.build_prices()

    def _extract_price_value(self, price_str: str) -> Optional[float]:
        """Extract a numeric price value from a price string for curve fitting."""
        if not price_str or price_str.strip() == "":
            return None

        price_str = price_str.strip()

        # Handle special values
        if price_str.upper() in ["N/A", "NA", "INESTIMABLE", "INEST"]:
            return None

        # Handle "4800+" format - use the base value
        if price_str.endswith("+"):
            try:
                return float(price_str.rstrip("+").strip())
            except ValueError:
                return None

        # Handle range format "min-max" - use average for curve fitting
        if "-" in price_str:
            parts = price_str.split("-")
            if len(parts) == 2:
                min_str, max_str = parts[0].strip(), parts[1].strip()
                if not min_str or not max_str:
                    return None
                try:
                    min_price = float(min_str)
                    max_price = float(max_str)
                    return (min_price + max_price) / 2
                except ValueError:
                    return None

        # Try to parse as a single number
        try:
            return float(price_str)
        except ValueError:
            return None

    def _fit_price_curve(self, x_values: list[int], y_values: list[float]) -> Optional[Callable[[int], float]]:
        """Fit a linear curve to the given data points. Returns a function f(x) = a*x + b."""
        if len(x_values) < 2 or len(y_values) < 2:
            return None

        # Simple linear regression: y = a*x + b
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)

        denominator = n * sum_x2 - sum_x * sum_x
        if abs(denominator) < 1e-10:  # Avoid division by zero
            return None

        a = (n * sum_xy - sum_x * sum_y) / denominator
        b = (sum_y - a * sum_x) / n

        # Return a function that computes the price for a given x
        def price_func(x: int) -> float:
            return a * x + b

        return price_func

    def _fit_inestimable_hit_values(self, hit_values: Dict[str, str]) -> None:
        """Fit inestimable prices in hit_values dictionary."""
        if not hit_values:
            return

        # Convert keys to integers and sort
        sorted_keys = sorted(map(int, hit_values.keys()))

        # Find the first inestimable index
        first_inestimable_idx = None
        for i, key in enumerate(sorted_keys):
            price_str = hit_values[str(key)]
            if price_str and price_str.strip().upper() in ["INESTIMABLE", "INEST"]:
                first_inestimable_idx = i
                break

        if first_inestimable_idx is None:
            return  # No inestimable values found

        # Collect prior fixed values
        prior_x = []
        prior_y = []
        for i in range(first_inestimable_idx):
            key = sorted_keys[i]
            price_str = hit_values[str(key)]
            price_value = self._extract_price_value(price_str)
            if price_value is not None:
                prior_x.append(key)
                prior_y.append(price_value)

        if not prior_x:
            return  # No prior fixed values to work with

        # Check if values are increasing
        is_increasing = len(prior_y) > 1 and all(prior_y[i] <= prior_y[i + 1] for i in range(len(prior_y) - 1))

        # Fit prices for inestimable values
        last_fitted_price = prior_y[-1] if prior_y else 0.0
        for i in range(first_inestimable_idx, len(sorted_keys)):
            key = sorted_keys[i]
            price_str = hit_values[str(key)]

            if price_str and price_str.strip().upper() in ["INESTIMABLE", "INEST"]:
                if is_increasing and len(prior_x) >= 2:
                    # Fit a curve
                    price_func = self._fit_price_curve(prior_x, prior_y)
                    if price_func:
                        estimated_price = price_func(key)
                        # Ensure price doesn't go negative
                        estimated_price = max(0, estimated_price)
                        # CRITICAL: Ensure monotonicity - price must be >= last fitted price
                        estimated_price = max(estimated_price, last_fitted_price)
                        # Round to reasonable precision
                        estimated_price = round(estimated_price, 2)
                        if estimated_price == int(estimated_price):
                            hit_values[str(key)] = str(int(estimated_price))
                        else:
                            hit_values[str(key)] = str(estimated_price)
                        last_fitted_price = estimated_price
                    else:
                        # Fallback to last fixed price (or last fitted price if we've fitted some)
                        if last_fitted_price == int(last_fitted_price):
                            hit_values[str(key)] = str(int(last_fitted_price))
                        else:
                            hit_values[str(key)] = str(last_fitted_price)
                else:
                    # Use last fixed price (or last fitted price if we've fitted some)
                    if last_fitted_price == int(last_fitted_price):
                        hit_values[str(key)] = str(int(last_fitted_price))
                    else:
                        hit_values[str(key)] = str(last_fitted_price)

    def _fit_inestimable_weapon_prices(self) -> None:
        """Process weapon prices to fit inestimable values."""
        for weapon_name, weapon_data in self.weapon_prices.items():
            if "hit_values" in weapon_data and weapon_data["hit_values"]:
                self._fit_inestimable_hit_values(weapon_data["hit_values"])

    def _fit_inestimable_common_weapon_prices(self) -> None:
        """Fit inestimable hit tiers in nested common_weapons.json entries."""
        for category_weapons in self.common_weapon_prices.values():
            if not isinstance(category_weapons, dict):
                continue
            for specials in category_weapons.values():
                if not isinstance(specials, dict):
                    continue
                for hit_values in specials.values():
                    if isinstance(hit_values, dict) and hit_values:
                        self._fit_inestimable_hit_values(hit_values)

    def build_prices(self) -> None:
        """Build price database from local JSON files"""
        logger.info(f"Building price database from {self.directory}")
        self.srank_weapon_prices = self._load_json_file("srankweapons.json")
        self.weapon_prices = self._load_json_file("weapons.json")
        if FIT_INESTIMABLE_PRICE:
            self._fit_inestimable_weapon_prices()
        self.common_weapon_prices = self._load_json_file("common_weapons.json")
        if FIT_INESTIMABLE_PRICE:
            self._fit_inestimable_common_weapon_prices()
        self.frame_prices = self._load_json_file("frames.json")
        self.barrier_prices = self._load_json_file("barriers.json")
        self.unit_prices = self._load_json_file("units.json")
        self.mag_prices = self._load_json_file("mags.json")
        self.cell_prices = self._load_json_file("cells.json")
        self.techniques_prices = self._load_json_file("techniques.json")
        self.tool_prices = self._load_json_file("tools.json")
        self.meseta_prices = self._load_json_file("meseta.json")
        logger.info(f"Price database built from {self.directory}")

    def _load_json_file(self, filename: str) -> Dict[str, Any]:
        """Load and parse a JSON file from the directory"""
        file_path = self.directory / filename
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading {filename} from {file_path}: {e}")
            raise PriceGuideException(f"Error loading {filename} from {file_path}: {e}")


class PriceGuideDynamic(PriceGuideAbstract):
    def __init__(self, api_url: str, base_price_strategy: BasePriceStrategy = BasePriceStrategy.MINIMUM):
        super().__init__(base_price_strategy)
        self.api_url = api_url
        # build_prices is async but doesn't do anything yet (placeholder)
        # For now, just call it synchronously if possible, or skip initialization
        pass

    def build_prices(self) -> None:
        """Build price database from web API"""
        pass
        """
        # This is a placeholder for the actual implementation
        async with aiohttp.ClientSession() as session:
            try:
                # Example of how it might work:
                # async with session.get(f"{self.api_url}/prices") as response:
                #     data = await response.json()
                #     self.srank_weapon_prices = data.get("srankweapons", {})
                #     self.weapon_prices = data.get("weapons", {})
                #     # etc...
                pass
            except aiohttp.ClientError as e:
                print(f"Error fetching prices: {e}")
        """


# Example usage:
if __name__ == "__main__":
    # Using fixed prices from JSON files
    data_dir = Path(__file__).parent / "data"
    fixed_guide = PriceGuideFixed(str(data_dir))

    # Using dynamic prices from web API
    dynamic_guide = PriceGuideDynamic("https://api.pioneer2.net/prices")
