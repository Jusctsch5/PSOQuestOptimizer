"""
Unified item value calculator that routes to appropriate specialized calculators.

This module provides a single interface for calculating item values across all
item types, internally using WeaponValueCalculator and ArmorValueCalculator
for complex calculations.
"""

from typing import Any, Dict, Optional, Tuple

from price_guide import PriceGuideAbstract
from price_guide.armor_value_calculator import ArmorValueCalculator
from price_guide.weapon_value_calculator import WeaponValueCalculator


class ItemValueCalculator:
    """
    Unified calculator for item values across all item types.

    This class wraps WeaponValueCalculator and ArmorValueCalculator,
    providing a single interface to calculate values for any item type.
    """

    def __init__(self, price_guide: PriceGuideAbstract):
        """
        Initialize calculator with a price guide instance.

        Args:
            price_guide: PriceGuideAbstract instance for price lookups
        """
        self.price_guide = price_guide
        self.weapon_calculator = WeaponValueCalculator(price_guide)
        self.armor_calculator = ArmorValueCalculator(price_guide)

    def calculate_item_value(
        self,
        item_name: str,
        drop_area: Optional[str] = None,
    ) -> Optional[Tuple[str, float]]:
        """
        Calculate the value of an item by inferring its type and routing to the appropriate calculator.

        Args:
            item_name: Name of the item to look up
            drop_area: Drop area (only used for weapons, affects hit probability)

        Returns:
            Tuple of (item_type, value) or None if not found.
            item_type can be: 'weapon', 'frame', 'barrier', 'unit', 'cell', 'tool', 'mag', 'disk'
        """
        item_type = self.price_guide.identify_item_type(item_name)

        if item_type is None:
            return None

        if item_type == "weapon":
            self.price_guide.get_weapon_data(item_name)
            value = self.weapon_calculator.calculate_weapon_expected_value(item_name, drop_area)
            return ("weapon", value)
        elif item_type == "frame":
            value = self.armor_calculator.calculate_frame_expected_value(item_name)
            return ("frame", value)
        elif item_type == "barrier":
            value = self.armor_calculator.calculate_barrier_expected_value(item_name)
            return ("barrier", value)
        elif item_type == "unit":
            value = self.price_guide.get_price_unit(item_name)
            return ("unit", value)
        elif item_type == "cell":
            value = self.price_guide.get_price_cell(item_name)
            return ("cell", value)
        elif item_type == "tool":
            value = self.price_guide.get_price_tool(item_name, 1)
            return ("tool", value)
        elif item_type == "mag":
            value = self.price_guide.get_price_mag(item_name, 0)
            return ("mag", value)
        elif item_type == "disk":
            value = self.price_guide.get_price_disk(item_name, 30)
            return ("disk", value)
        else:
            raise ValueError(f"Item type {item_type} not supported")

    def get_calculation_breakdown(
        self,
        item_name: str,
        drop_area: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed breakdown of the calculation for an item as structured data.

        Args:
            item_name: Name of the item
            drop_area: Drop area (only used for weapons)

        Returns:
            Dictionary with comprehensive breakdown data, or None if item type doesn't support breakdown
        """
        item_type = self.price_guide.identify_item_type(item_name)

        if item_type == "weapon":
            return self.weapon_calculator.get_calculation_breakdown(item_name, drop_area)
        elif item_type == "frame":
            return self.armor_calculator.get_frame_calculation_breakdown(item_name)
        elif item_type == "barrier":
            return self.armor_calculator.get_barrier_calculation_breakdown(item_name)
        # Other item types don't have detailed breakdowns
        return None

    def print_calculation_breakdown(
        self,
        item_name: str,
        drop_area: Optional[str] = None,
    ) -> None:
        """
        Print detailed breakdown of the calculation for an item.

        Args:
            item_name: Name of the item
            drop_area: Drop area (only used for weapons)
        """
        item_type = self.price_guide.identify_item_type(item_name)

        if item_type == "weapon":
            self.weapon_calculator.print_calculation_breakdown(item_name, drop_area)
        elif item_type == "frame":
            self.armor_calculator.print_frame_calculation_breakdown(item_name)
        elif item_type == "barrier":
            self.armor_calculator.print_barrier_calculation_breakdown(item_name)
        # Other item types don't have detailed breakdowns
