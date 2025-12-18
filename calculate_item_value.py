#!/usr/bin/env python3
"""
Script to calculate average item value based on drop location and patterns.

This script demonstrates the item value calculation and shows
the probability distributions for different item types:
- Weapons: based on drop location and Pattern 5
- Frames (Armor): based on stat tier probabilities
- Barriers (Shields): based on stat tier probabilities
- Other items: units, cells, tools, mags, disks (base price only)
"""

import argparse
from pathlib import Path
from typing import Optional, Tuple

from drop_tables.weapon_patterns import AREAS
from price_guide import BasePriceStrategy, PriceGuideExceptionItemNameNotFound, PriceGuideFixed
from price_guide.armor_value_calculator import ArmorValueCalculator
from price_guide.weapon_value_calculator import WeaponValueCalculator


def calculate_item_value(
    item_name: str,
    price_guide: PriceGuideFixed,
    weapon_value_calculator: WeaponValueCalculator,
    armor_value_calculator: ArmorValueCalculator,
    drop_area: Optional[str] = None,
) -> Optional[Tuple[str, float]]:
    """
    Infer item type and calculate its value by trying to find the item in each category.

    Args:
        item_name: Name of the item to look up
        price_guide: Price guide instance
        weapon_value_calculator: Calculator for weapon values
        armor_value_calculator: Calculator for armor/shield values
        drop_area: Drop area (only used for weapons, affects hit probability)

    Returns:
        Tuple of (item_type, value) or None if not found.
        item_type can be: 'weapon', 'frame', 'barrier', 'unit', 'cell', 'tool', 'mag', 'disk'
    """
    # Try weapons first
    try:
        price_guide.get_weapon_data(item_name)
        value = weapon_value_calculator.calculate_weapon_expected_value(item_name, drop_area)
        return ("weapon", value)
    except PriceGuideExceptionItemNameNotFound:
        pass

    # Try frames
    frame_key = price_guide._ci_key(price_guide.frame_prices, item_name)
    if frame_key is not None:
        value = armor_value_calculator.calculate_frame_expected_value(item_name)
        return ("frame", value)

    # Try barriers
    barrier_key = price_guide._ci_key(price_guide.barrier_prices, item_name)
    if barrier_key is not None:
        value = armor_value_calculator.calculate_barrier_expected_value(item_name)
        return ("barrier", value)

    # Try units
    try:
        value = price_guide.get_price_unit(item_name)
        return ("unit", value)
    except PriceGuideExceptionItemNameNotFound:
        pass

    # Try cells
    try:
        value = price_guide.get_price_cell(item_name)
        return ("cell", value)
    except PriceGuideExceptionItemNameNotFound:
        pass

    # Try tools
    try:
        value = price_guide.get_price_tool(item_name, 1)
        return ("tool", value)
    except PriceGuideExceptionItemNameNotFound:
        pass

    # Try mags
    try:
        value = price_guide.get_price_mag(item_name, 0)
        return ("mag", value)
    except PriceGuideExceptionItemNameNotFound:
        pass

    # Try disks
    try:
        value = price_guide.get_price_disk(item_name, 30)
        return ("disk", value)
    except PriceGuideExceptionItemNameNotFound:
        pass

    return None


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Calculate average item value based on drop location and patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Calculate weapon value (type inferred automatically)
  python calculate_item_value.py VJAYA

  # Calculate frame value (type inferred automatically)
  python calculate_item_value.py "Brightness Circle"

  # Calculate barrier value (type inferred automatically)
  python calculate_item_value.py "DF Shield"

  # Calculate unit value (type inferred automatically)
  python calculate_item_value.py "God/Ability"

  # Calculate weapon with area filter (affects hit probability)
  python calculate_item_value.py VJAYA --area "Forest 1"

  # Use average price strategy instead of minimum
  python calculate_item_value.py VJAYA --price-strategy average

  # Use custom price guide directory
  python calculate_item_value.py VJAYA --price-guide ../PSOPriceGuide/pso_price_guide/data
        """,
    )

    parser.add_argument(
        "item",
        type=str,
        help="Item name (e.g., VJAYA, 'Brightness Circle', 'DF Shield', 'God/Ability'). Type is inferred automatically.",
    )

    parser.add_argument(
        "--area",
        type=str,
        choices=AREAS,
        default=None,
        help="Drop area (e.g., 'Forest 1', 'Ruins 3', 'VR Temple Alpha'). Only affects weapons (hit probability).",
    )

    parser.add_argument(
        "--price-guide", type=str, default=None, help="Path to price guide data directory (default: ./price_guide/data)"
    )

    parser.add_argument(
        "--price-strategy",
        type=str,
        choices=[strategy.value for strategy in BasePriceStrategy],
        default=BasePriceStrategy.MINIMUM.value,
        help=f"Base price strategy for price range calculations (default: {BasePriceStrategy.MINIMUM.value})",
    )

    args = parser.parse_args()
    drop_area = args.area if args.area else None
    item_name = args.item

    # Set up paths
    base_path = Path(__file__).parent

    if args.price_guide:
        price_guide_path = Path(args.price_guide)
    else:
        price_guide_path = base_path / "price_guide" / "data"

    if not price_guide_path.exists():
        print(f"Error: Price guide directory not found at {price_guide_path}")
        print(f"Please specify the correct path with --price-guide")
        return 1

    # Initialize price guide with price strategy
    base_price_strategy = BasePriceStrategy(args.price_strategy.upper())
    price_guide = PriceGuideFixed(str(price_guide_path), base_price_strategy=base_price_strategy)

    weapon_value_calculator = WeaponValueCalculator(price_guide)
    armor_value_calculator = ArmorValueCalculator(price_guide)

    # Infer item type and calculate value
    item_info = calculate_item_value(item_name, price_guide, weapon_value_calculator, armor_value_calculator, drop_area)
    if item_info is None:
        print(f"Error: Could not find '{item_name}' in any item category")
        return 1

    item_type, item_value = item_info
    print(f"Inferred item type: {item_type}")
    if drop_area and item_type != "weapon":
        print(f"Note: --area is only used for weapons (affects hit probability)")
    print()

    # Show detailed breakdown or simple value based on item type
    if item_type == "weapon":
        # Print detailed breakdown for weapon
        weapon_value_calculator.print_calculation_breakdown(item_name, drop_area)
    elif item_type == "frame":
        # Print detailed breakdown for frame
        armor_value_calculator.print_frame_calculation_breakdown(item_name)
    elif item_type == "barrier":
        # Print detailed breakdown for barrier
        armor_value_calculator.print_barrier_calculation_breakdown(item_name)
    else:
        # For other item types (unit, cell, tool, mag, disk), just show the value
        print(f"{'=' * 80}")
        print(f"ITEM VALUE")
        print(f"{'=' * 80}")
        print(f"Item: {item_name}")
        print(f"Type: {item_type}")
        print(f"Value: {item_value:.4f} PD")
        print(f"{'=' * 80}\n")

    return 0


if __name__ == "__main__":
    exit(main())
