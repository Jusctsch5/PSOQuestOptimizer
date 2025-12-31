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
from price_guide import BasePriceStrategy, PriceGuideFixed
from price_guide.item_value_calculator import ItemValueCalculator


def calculate_item_value(
    item_name: str,
    price_guide: PriceGuideFixed,
    item_value_calculator: ItemValueCalculator,
    drop_area: Optional[str] = None,
) -> Optional[Tuple[str, float]]:
    """
    Infer item type and calculate its value by trying to find the item in each category.

    Args:
        item_name: Name of the item to look up
        price_guide: Price guide instance
        item_value_calculator: Unified calculator for item values
        drop_area: Drop area (only used for weapons, affects hit probability)

    Returns:
        Tuple of (item_type, value) or None if not found.
        item_type can be: 'weapon', 'frame', 'barrier', 'unit', 'cell', 'tool', 'mag', 'disk'
    """
    return item_value_calculator.calculate_item_value(item_name, drop_area)


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

    parser.add_argument("--price-guide", type=str, default=None, help="Path to price guide data directory (default: ./price_guide/data)")

    parser.add_argument(
        "--price-strategy",
        type=str,
        choices=[strategy.value for strategy in BasePriceStrategy],
        default=BasePriceStrategy.MINIMUM.value,
        help=f"Base price strategy for price range calculations (default: {BasePriceStrategy.MINIMUM.value})",
    )

    parser.add_argument(
        "--print-breakdown",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Print breakdown of the calculation (default: True, use --no-print-breakdown to disable)",
    )

    args = parser.parse_args()
    drop_area = args.area if args.area else None
    item_name = args.item
    print_breakdown = args.print_breakdown

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

    item_value_calculator = ItemValueCalculator(price_guide)

    # Infer item type and calculate value
    result = calculate_item_value(item_name, price_guide, item_value_calculator, drop_area)
    if result is None:
        print(f"Error: Could not find '{item_name}' in any item category")
        return 1

    item_type, value = result
    print(f"Item type: {item_type}, Value: {value}")
    if print_breakdown:
        item_value_calculator.print_calculation_breakdown(item_name, drop_area)
    return 0


if __name__ == "__main__":
    exit(main())
