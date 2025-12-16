"""
Script to find the best quest and Section ID for hunting a specific weapon.

Searches through all quests and Section IDs to find which combination
has the highest drop probability for the specified weapon.
"""

import argparse
from pathlib import Path
from typing import Optional

from quest_optimizer.quest_calculator import QuestCalculator, WeeklyBoost


def display_enemy_drops(enemy_drops, weapon_name, rbr_active: bool, weekly_boost):
    """Display enemies that drop the weapon."""
    if not enemy_drops:
        print(f"\nNo enemies found that drop '{weapon_name}'.")
        return

    print(f"\n{'=' * 80}")
    print(f"Enemies that drop: {weapon_name}")
    if rbr_active or weekly_boost:
        print(f"  (RBR: {'Yes' if rbr_active else 'No'}, Weekly Boost: {weekly_boost.value if weekly_boost else 'None'})")
    print(f"{'=' * 80}\n")

    for i, enemy_info in enumerate(enemy_drops, 1):
        print(f"{i}. {enemy_info['enemy']} (Episode {enemy_info['episode']})")
        print(f"   Section ID: {enemy_info['section_id']}")
        dar_str = f"{enemy_info['dar']:.4f}"
        rdr_str = f"{enemy_info['rdr']:.6f}"
        if enemy_info["adjusted_dar"] != enemy_info["dar"]:
            dar_str += f" -> {enemy_info['adjusted_dar']:.4f}"
        if enemy_info["adjusted_rdr"] != enemy_info["rdr"]:
            rdr_str += f" -> {enemy_info['adjusted_rdr']:.6f}"
        print(f"   DAR: {dar_str}, RDR: {rdr_str}")
        print(f"   Drop Rate: {enemy_info['drop_rate_percent']:.6f}% per kill")
        print(f"   (1 in {1 / enemy_info['drop_rate']:.1f} kills)")
        print()


def display_box_drops(box_drops, weapon_name):
    """Display boxes that drop the weapon."""
    if not box_drops:
        print(f"\nNo boxes found that drop '{weapon_name}'.")
        return

    print(f"\n{'=' * 80}")
    print(f"Boxes that drop: {weapon_name}")
    print(f"  (Note: Box drops are NOT affected by DAR, RDR, or any drop rate bonuses)")
    print(f"{'=' * 80}\n")

    for i, box_info in enumerate(box_drops, 1):
        print(f"{i}. {box_info['area']} (Episode {box_info['episode']})")
        print(f"   Section ID: {box_info['section_id']}")
        print(f"   Drop Rate: {box_info['drop_rate_percent']:.6f}% per box")
        print(f"   (1 in {1 / box_info['drop_rate']:.1f} boxes)")
        print()


def display_results(results, weapon_name, top_n: Optional[int] = 10):
    """Display the search results in a formatted way."""
    if not results:
        print(f"\nNo quests found that drop '{weapon_name}'.")
        return

    print(f"\n{'=' * 80}")
    print(f"Best quests for hunting: {weapon_name}")
    print(f"{'=' * 80}\n")

    # Show top 10 results
    if top_n:
        top_results = results[:top_n]
    else:
        top_results = results

    for i, result in enumerate(top_results, 1):
        print(f"{i}. Quest: {result['quest_name']} ({result['long_name']})")
        print(f"   Section ID: {result['section_id']}")
        print(f"   Drop Probability: {result['percentage']:.6f}% per quest run")
        print(f"   (1 in {1 / result['probability']:.1f} quest runs)")
        print(f"   Contributions:")

        for contrib in result["contributions"]:
            if contrib.get("source") == "Box":
                # Box contribution
                print(f"     - Box ({contrib['area']}): {contrib['box_count']} boxes")
                print(f"       Drop Rate: {contrib['drop_rate']:.6f}")
                print(f"       Contribution: {contrib['probability'] * 100:.6f}%")
            else:
                # Enemy contribution
                print(f"     - {contrib['enemy']}: {contrib['count']} kills")
                dar_str = f"{contrib['dar']:.4f}"
                rdr_str = f"{contrib['rdr']:.6f}"
                if "adjusted_dar" in contrib and contrib["adjusted_dar"] != contrib["dar"]:
                    dar_str += f" -> {contrib['adjusted_dar']:.4f}"
                if "adjusted_rdr" in contrib and contrib["adjusted_rdr"] != contrib["rdr"]:
                    rdr_str += f" -> {contrib['adjusted_rdr']:.6f}"
                print(f"       DAR: {dar_str}, RDR: {rdr_str}")
                print(f"       Contribution: {contrib['probability'] * 100:.6f}%")

        print()

    if top_n and len(results) > top_n:
        print(f"... and {len(results) - 10} more results.\n")

    # Show best overall
    best = results[0]
    print(f"{'=' * 80}")
    print(f"BEST OPTION:")
    print(f"  Quest: {best['quest_name']} ({best['long_name']})")
    print(f"  Section ID: {best['section_id']}")
    print(f"  Drop Chance: {best['percentage']:.6f}% per quest run")
    print(f"  Expected runs: {1 / best['probability']:.1f}")
    print(f"{'=' * 80}\n")


def main():
    """Main function to run the weapon hunting optimizer."""
    parser = argparse.ArgumentParser(description="Find the best quest and Section ID for hunting a specific weapon")
    parser.add_argument("weapon", help="Name of the weapon to search for")
    parser.add_argument("--rbr", action="store_true", help="Enable RBR boost (+25%% DAR, +25%% RDR)")
    parser.add_argument(
        "--weekly-boost",
        type=str,
        choices=[boost.value for boost in WeeklyBoost],
        default=None,
        help="Weekly boost type: DAR, RDR, RareEnemy, XP, or None (default: None)",
    )
    parser.add_argument(
        "--quests",
        type=str,
        nargs="+",
        default=None,
        help="Filter to specific quests by name (e.g., 'MU1 SU2 EN3')",
    )
    parser.add_argument(
        "--christmas-boost",
        action="store_true",
        help="Enable Christmas boost (doubles weekly boost values)",
    )
    parser.add_argument(
        "--exclude-event-quests",
        action="store_true",
        help="Exclude event quests from the search (quests marked with is_event_quest: true)",
    )
    args = parser.parse_args()
    if args.weekly_boost:
        weekly_boost = WeeklyBoost(args.weekly_boost)
    else:
        weekly_boost = None

    weapon = args.weapon

    # Set up paths
    script_dir = Path(__file__).parent
    drop_table_path = script_dir / "drop_tables" / "drop_tables_ultimate.json"
    price_guide_path = script_dir / "price_guide" / "data"
    quest_data_path = script_dir / "quests" / "quests.json"

    # Check if files exist
    if not drop_table_path.exists():
        print(f"Error: Drop table file not found at {drop_table_path}")
        return

    if not quest_data_path.exists():
        print(f"Error: Quest file not found at {quest_data_path}")
        return

    # Initialize calculator
    print("Loading quest and drop table data...")
    calculator = QuestCalculator(drop_table_path, price_guide_path, quest_data_path)
    print(f"Loaded {len(calculator.quest_data)} quests.")

    # Filter out event quests if requested
    if args.exclude_event_quests:
        original_count = len(calculator.quest_data)
        calculator.quest_data = [quest for quest in calculator.quest_data if not calculator._is_event_quest(quest)]
        filtered_count = original_count - len(calculator.quest_data)
        if filtered_count > 0:
            print(f"Excluded {filtered_count} event quest(s)")
            print(f"Processing {len(calculator.quest_data)} quest(s)")
    print()

    # Find best quests
    print(f"Searching for '{weapon}' across all quests and Section IDs...")
    if args.rbr:
        print(f"  RBR Active: Yes")
    if weekly_boost:
        print(f"  Weekly Boost: {weekly_boost}")
    print(f"  Christmas Boost: {args.christmas_boost}")
    if args.quests:
        print(f"  Quest Filter: {', '.join(args.quests)}")
    if args.exclude_event_quests:
        print(f"  Exclude Event Quests: Yes")
    print()

    # Find enemies that drop the weapon
    enemy_drops = calculator.find_enemies_that_drop_weapon(
        weapon, rbr_active=args.rbr, weekly_boost=weekly_boost, christmas_boost=args.christmas_boost
    )

    # Display enemy drops first
    display_enemy_drops(enemy_drops, weapon, args.rbr, weekly_boost)

    # Find boxes that drop the weapon
    box_drops = calculator.find_boxes_that_drop_weapon(weapon)

    # Display box drops
    display_box_drops(box_drops, weapon)

    # Find best quests
    results = calculator.find_best_quests_for_weapon(
        weapon, rbr_active=args.rbr, weekly_boost=weekly_boost, quest_filter=args.quests, christmas_boost=args.christmas_boost
    )

    # Display quest results
    display_results(results, weapon)


if __name__ == "__main__":
    main()
