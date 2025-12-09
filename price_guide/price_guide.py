from abc import ABC, abstractmethod
from bisect import bisect
from typing import Dict, Any, Optional, List
from pathlib import Path
import asyncio
import json
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class BasePriceStrategy(ABC):
    MINIMUM = 0
    AVERAGE = 1
    MAXIMUM = 2


MESESTA_PER_PD = 500000
HIGH_ATTRIBUTE_THRESHOLD = 50
ASSUME_MISSING_PRICE_MEANS_ZERO = True


class PriceGuideException(Exception):
    pass


class PriceGuideExceptionItemNameNotFound(PriceGuideException):
    pass


class PriceGuideExceptionAbilityNameNotFound(PriceGuideException):
    pass


class PriceGuideParseException(PriceGuideException):
    pass


class PriceGuideAbstract(ABC):
    def __init__(self):
        self.bps = BasePriceStrategy.MINIMUM
        self.srank_weapon_prices: Dict[str, Any] = {}
        self.weapon_prices: Dict[str, Any] = {}
        self.frame_prices: Dict[str, Any] = {}
        self.barrier_prices: Dict[str, Any] = {}
        self.unit_prices: Dict[str, Any] = {}
        self.mag_prices: Dict[str, Any] = {}
        self.disk_prices: Dict[str, Any] = {}
        self.tool_prices: Dict[str, Any] = {}

    @staticmethod
    # Parse out the price range value from the price range dictionary
    def get_price_from_range(price_range: str, bps: BasePriceStrategy) -> float:
        # Handle None or empty string
        if not price_range or price_range.strip() == "":
            return 0.0
        
        price_range = price_range.strip()
        
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
    def get_price_for_item_range(
        price_range: str, number: int, bps: BasePriceStrategy
    ) -> float:
        return PriceGuideAbstract.get_price_from_range(price_range, bps) * number

    @abstractmethod
    async def build_prices(self) -> None:
        """Build the price database from the source"""
        pass

    def get_price_srank_weapon(
        self,
        name: str,
        ability: str,
        grinder: int,
        element: str,
    ) -> float:
        """Get price for S-rank weapon"""

        actual_key = next(
            (
                key
                for key in self.srank_weapon_prices["weapons"].keys()
                if key.lower() == name.lower()
            ),
            None,
        )

        if actual_key is None:
            if ASSUME_MISSING_PRICE_MEANS_ZERO:
                return 0
            else:
                raise PriceGuideExceptionItemNameNotFound(
                    f"Item name {name} not found in srank_weapon_prices"
                )

        base_price = self.srank_weapon_prices["weapons"][actual_key]["base"]

        ability_price = 0
        if ability:
            actual_ability = next(
                (
                    key
                    for key in self.srank_weapon_prices["modifiers"].keys()
                    if key.lower() == ability.lower()
                ),
                None,
            )

            if actual_ability is None:
                raise PriceGuideExceptionAbilityNameNotFound(
                    f"Ability {ability} not found in srank_weapon_prices"
                )

            ability_price = self.srank_weapon_prices["modifiers"][actual_ability][
                "base"
            ]

        total_price = float(base_price) + float(ability_price)

        return total_price

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

        actual_key = next(
            (key for key in self.weapon_prices.keys() if key.lower() == name.lower()),
            None,
        )

        if actual_key is None:
            if ASSUME_MISSING_PRICE_MEANS_ZERO:
                return 0
            else:
                raise PriceGuideExceptionItemNameNotFound(
                    f"Item name {name} not found in weapon_prices"
                )

        base_price_str = self.weapon_prices[actual_key].get("base")
        if base_price_str is None:
            base_price = 0.0
        else:
            base_price = self.get_price_from_range(
                base_price_str, self.bps
            )

        if weapon_attributes:
            modifiers = self.weapon_prices[actual_key].get("modifiers", {})
            for attribute, value in weapon_attributes.items():
                if value > HIGH_ATTRIBUTE_THRESHOLD and attribute in modifiers:
                    ability_price_str = modifiers[attribute]
                    if ability_price_str and ability_price_str.upper() != "N/A":
                        ability_price = self.get_price_from_range(
                            ability_price_str, self.bps
                        )
                        base_price += ability_price

        hit_values = self.weapon_prices[actual_key].get("hit_values", {})

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
        if name not in self.frame_prices:
            if ASSUME_MISSING_PRICE_MEANS_ZERO:
                return 0
            else:
                raise PriceGuideExceptionItemNameNotFound(
                    f"Item name {name} not found in frame_prices"
                )
        price_range = self.frame_prices[name]["base"]
        base_price = self.get_price_from_range(price_range, self.bps)
        if slot > 0:
            base_price += self.get_price_tool("AddSlot", slot)

        return base_price

    def get_price_barrier(
        self, name: str, addition: Dict[str, int], max_addition: Dict[str, int]
    ) -> float:
        """Get price for barrier"""
        logger.info(f"get_price_barrier: {name} {addition} {max_addition}")
        if name not in self.barrier_prices:
            if ASSUME_MISSING_PRICE_MEANS_ZERO:
                return 0
            else:
                raise PriceGuideExceptionItemNameNotFound(
                    f"Item name {name} not found in barrier_prices"
                )
        price_range = self.barrier_prices[name]["base"]
        base_price = self.get_price_from_range(price_range, self.bps)

        return base_price

    def get_price_unit(self, name: str) -> float:
        """Get price for unit"""
        logger.info(f"get_price_unit: {name}")
        if name not in self.unit_prices:
            if ASSUME_MISSING_PRICE_MEANS_ZERO:
                return 0
            else:
                raise PriceGuideExceptionItemNameNotFound(
                    f"Item name {name} not found in unit_prices"
                )
        price_range = self.unit_prices[name]["base"]
        return self.get_price_for_item_range(price_range, 1, self.bps)

    def get_price_mag(self, name: str, level: int) -> float:
        """Get price for mag"""
        logger.info(f"get_price_mag: {name} {level}")
        if name not in self.mag_prices:
            if ASSUME_MISSING_PRICE_MEANS_ZERO:
                return 0
            else:
                raise PriceGuideExceptionItemNameNotFound(
                    f"Item name {name} not found in mag_prices"
                )
        price_range = self.mag_prices[name]["base"]
        return self.get_price_for_item_range(price_range, 1, self.bps)

    def get_price_disk(self, name: str, level: int) -> float:
        logger.info(f"get_price_disk: {name} {level}")
        if name not in self.disk_prices:
            if ASSUME_MISSING_PRICE_MEANS_ZERO:
                return 0
            else:
                raise PriceGuideExceptionItemNameNotFound(
                    f"Item name {name} not found in disk_prices"
                )
        levels = self.disk_prices[name]
        # Convert string keys to integers and sort
        sorted_thresholds = sorted(map(int, levels.keys()))

        # Find the largest threshold <= actual level value
        index = bisect(sorted_thresholds, level) - 1

        if index >= 0:
            threshold = sorted_thresholds[index]
            price_range = levels[str(threshold)]
            price = self.get_price_from_range(price_range, self.bps)
            return price

        # If not found, it's not worth anything.
        return 0

    def get_price_tool(self, name: str, number: int) -> float:
        """Get price for tool"""
        logger.info(f"get_price_tool: {name} {number}")
        # Check if the tool exists in the price database
        if name not in self.tool_prices:
            if ASSUME_MISSING_PRICE_MEANS_ZERO:
                return 0
            else:
                raise PriceGuideExceptionItemNameNotFound(
                    f"Item name {name} not found in tool_prices"
                )

        # Get the price range string
        price_range = self.tool_prices[name]["base"]
        return self.get_price_for_item_range(price_range, number, self.bps)

    def get_price_other(self, name: str, number: int) -> float:
        """Get price for other items"""
        logger.info(f"get_price_other: {name} {number}")
        return 0
    
    def get_weapon_expected_value(
        self,
        weapon_name: str,
        drop_area: Optional[str] = None,
    ) -> float:
        """
        Calculate expected weapon value based on pattern probabilities.
        
        For rare weapons: Always uses Pattern 5 for all attributes.
        For common weapons: Uses area-specific patterns.
        
        Args:
            weapon_name: Name of the weapon
            drop_area: Area where weapon drops (for hit probability calculation)
        
        Returns:
            Expected PD value
        """
        from .weapon_value_calculator import WeaponValueCalculator
        
        calculator = WeaponValueCalculator(self)
        return calculator.calculate_weapon_expected_value(weapon_name, drop_area)
    
    def get_weapon_value_breakdown(
        self,
        weapon_name: str,
        drop_area: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get detailed breakdown of weapon value calculation.
        
        Args:
            weapon_name: Name of the weapon
            drop_area: Area where weapon drops
        
        Returns:
            Dictionary with breakdown:
            {
                "base_price": float,
                "attribute_contribution": float,
                "hit_contribution": float,
                "total": float,
                "weapon_data": Dict,
                "attr_results": Dict,
                "hit_breakdown": List[Dict],
            }
        """
        from .weapon_value_calculator import WeaponValueCalculator
        
        calculator = WeaponValueCalculator(self)
        return calculator.get_weapon_value_breakdown(weapon_name, drop_area)


class PriceGuideFixed(PriceGuideAbstract):
    def __init__(self, directory: str):
        super().__init__()
        self.directory = Path(directory)
        asyncio.run(self.build_prices())

    async def build_prices(self) -> None:
        """Build price database from local JSON files"""
        logger.info(f"Building price database from {self.directory}")
        self.srank_weapon_prices = self._load_json_file("srankweapons.json")
        self.weapon_prices = self._load_json_file("weapons.json")
        self.frame_prices = self._load_json_file("frames.json")
        self.barrier_prices = self._load_json_file("barriers.json")
        self.unit_prices = self._load_json_file("units.json")
        self.mag_prices = self._load_json_file("mags.json")
        self.disk_prices = self._load_json_file("disks.json")
        self.tool_prices = self._load_json_file("tools.json")
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
    def __init__(self, api_url: str):
        super().__init__()
        self.api_url = api_url
        asyncio.run(self.build_prices())

    async def build_prices(self) -> None:
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
    from pathlib import Path
    # Using fixed prices from JSON files
    data_dir = Path(__file__).parent / "data"
    fixed_guide = PriceGuideFixed(str(data_dir))

    # Using dynamic prices from web API
    dynamic_guide = PriceGuideDynamic("https://api.pioneer2.net/prices")
