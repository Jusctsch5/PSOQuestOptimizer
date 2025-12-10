#!/usr/bin/env python3
"""
Script to calculate average weapon value based on drop location and patterns.

This script demonstrates the weapon value calculation and shows
the probability distributions for different attribute/hit combinations.
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from drop_tables.weapon_patterns import (
    AREAS,
)
from price_guide import BasePriceStrategy, PriceGuideFixed
from price_guide.weapon_value_calculator import WeaponValueCalculator


def print_weapon_rankings(weapon_results: List[Dict[str, Any]], drop_area: Optional[str] = None) -> None:
    """Print weapon rankings in a readable table format."""
    if not weapon_results:
        print("No weapons to display.")
        return

    # Calculate column widths
    max_weapon_width = max(len(result["weapon"]) for result in weapon_results)
    max_weapon_width = max(max_weapon_width, len("Weapon"))

    # Print header
    header = f"{'Rank':<6} {'Weapon':<{max_weapon_width}} {'Avg Value (PD)':<15}"
    if drop_area:
        header += f" {'Drop Area':<20}"
    print(header)
    print("-" * len(header))

    # Print rows
    for idx, result in enumerate(weapon_results, 1):
        row = f"{idx:<6} {result['weapon']:<{max_weapon_width}} {result['avg_value']:<15.4f}"
        if drop_area:
            row += f" {drop_area:<20}"
        print(row)

    print()


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Calculate average weapon value based on drop location and Pattern 5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Calculate VJAYA value (uses Pattern 5 for rare weapons)
  python calculate_weapon_value.py VJAYA

  # Calculate EXCALIBUR value
  python calculate_weapon_value.py EXCALIBUR

  # Rank all weapons by average value
  python calculate_weapon_value.py

  # Rank all weapons with area filter
  python calculate_weapon_value.py --area "Forest 1"

  # Show top 10 weapons
  python calculate_weapon_value.py --top-n 10

  # Use average price strategy instead of minimum
  python calculate_weapon_value.py --price-strategy average

  # Use maximum price strategy
  python calculate_weapon_value.py --price-strategy maximum

  # Use custom price guide directory
  python calculate_weapon_value.py VJAYA --price-guide ../PSOPriceGuide/pso_price_guide/data
        """,
    )

    parser.add_argument(
        "weapon",
        type=str,
        nargs="?",
        default=None,
        help="Weapon name (e.g., VJAYA, EXCALIBUR). If omitted, calculates and ranks all weapons.",
    )

    parser.add_argument(
        "--area",
        type=str,
        choices=AREAS,
        default=None,
        help="Drop area (e.g., 'Forest 1', 'Ruins 3', 'VR Temple Alpha'). Affects hit probability.",
    )

    parser.add_argument(
        "--price-guide", type=str, default=None, help="Path to price guide data directory (default: ./price_guide/data)"
    )

    parser.add_argument("--top-n", type=int, default=None, help="Show only top N weapons when ranking all (default: show all)")

    parser.add_argument(
        "--price-strategy",
        type=str,
        choices=[strategy.value for strategy in BasePriceStrategy],
        default=BasePriceStrategy.MINIMUM.value,
        help=f"Base price strategy for price range calculations (default: {BasePriceStrategy.MINIMUM.value})",
    )

    args = parser.parse_args()
    drop_area = args.area if args.area else None
    weapon_name = args.weapon

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

    # If weapon is provided, show detailed breakdown for that weapon
    if weapon_name:
        # Print detailed breakdown
        weapon_value_calculator.print_calculation_breakdown(weapon_name, drop_area)
    else:
        # Calculate and rank all weapons
        print(f"Calculating average weapon values...")
        print(f"  Price Strategy: {args.price_strategy}")
        if drop_area:
            print(f"  Drop Area: {drop_area}")
        else:
            print(f"  Drop Area: None (default hit probability)")
        print()

        # Get all weapons from price guide
        all_weapons = list(price_guide.weapon_prices.keys())
        print(f"Found {len(all_weapons)} weapons in price guide")
        print()

        # Calculate value for each weapon
        weapon_results: List[Dict[str, Any]] = []
        for weapon in all_weapons:
            try:
                avg_value: float = weapon_value_calculator.calculate_weapon_expected_value(weapon, drop_area)
                # Exclude weapons with 0 value
                if avg_value > 0.0:
                    weapon_results.append({"weapon": weapon, "avg_value": avg_value})
            except Exception as e:
                # Skip weapons that can't be calculated (e.g., missing data)
                print(f"Warning: Could not calculate value for {weapon}: {e}", file=sys.stderr)
                continue

        # Sort by average value (descending)
        weapon_results.sort(key=lambda x: float(x["avg_value"]), reverse=True)

        # Apply top-n filter if specified
        if args.top_n:
            weapon_results = weapon_results[: args.top_n]

        # Print rankings table
        print_weapon_rankings(weapon_results, drop_area)

    return 0


if __name__ == "__main__":
    exit(main())
