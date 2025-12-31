"""
Script to find the best quest and Section ID for hunting a specific item.

Searches through all quests and Section IDs to find which combination
has the highest drop probability for the specified item (enemy drops + box drops).
"""

import argparse
import math
from collections import defaultdict
from pathlib import Path
from typing import Optional

from quest_optimizer.quest_calculator import (
    EventType,
    QuestCalculator,
    WeeklyBoost,
)


def calculate_runs_for_probability(drop_rate: float, target_probability: float = 0.95) -> float:
    """
    Calculate the number of runs needed to reach a target probability of at least one drop.

    Formula: P(at least 1 drop in N runs) = 1 - (1 - p)^N
    Solving for N: N = ln(1 - target_probability) / ln(1 - drop_rate)

    Args:
        drop_rate: Probability of drop per run (0.0 to 1.0)
        target_probability: Target probability of at least one drop (default: 0.95 for 95%)

    Returns:
        Number of runs needed (float)
    """
    if drop_rate <= 0:
        return float("inf")
    if drop_rate >= 1:
        return 1.0
    if target_probability >= 1:
        return float("inf")

    # N = ln(1 - target_probability) / ln(1 - drop_rate)
    numerator = math.log(1 - target_probability)
    denominator = math.log(1 - drop_rate)

    if denominator == 0:
        return float("inf")

    return numerator / denominator


def display_disk_drops(enemy_drops, item_name, rbr_active: bool, weekly_boost):
    """
    Display disk (technique) drops, grouped by area.
    Shows drop chance per enemy and 10/100/1000 enemy killed drop chances.
    """
    if not enemy_drops:
        print(f"\nNo enemies found that drop '{item_name}'.")
        return

    print(f"\n{'=' * 80}")
    print(f"Technique Disk Drops: {item_name}")
    if rbr_active or weekly_boost:
        print(f"  (RBR: {'Yes' if rbr_active else 'No'}, Weekly Boost: {weekly_boost.value if weekly_boost else 'None'})")
    print(f"{'=' * 80}\n")

    # Group by area
    area_groups = defaultdict(list)
    for enemy_info in enemy_drops:
        area = enemy_info.get("area", "Unknown")
        area_groups[area].append(enemy_info)

    # Display each area
    for area_name in sorted(area_groups.keys()):
        area_enemies = area_groups[area_name]
        print(f"Area: {area_name}")
        print(f"  Eligible Enemies: {len(area_enemies)} enemy type(s)")

        # Calculate aggregate probabilities for 10/100/1000 kills
        # Use the highest drop rate in the area as representative
        if area_enemies:
            max_drop_rate = max(e["drop_rate"] for e in area_enemies)
            if max_drop_rate > 0:
                print(f"  Aggregate Probabilities (using highest drop rate in area):")
                for num_kills in [10, 100, 1000]:
                    prob = 1 - (1 - max_drop_rate) ** num_kills
                    print(f"    {num_kills} enemies killed: {prob * 100:.2f}% chance of at least 1 drop")
        print()


def display_enemy_drops(enemy_drops, item_name, rbr_active: bool, weekly_boost):
    """Display enemies that drop the item (for non-tool, non-disk items)."""
    if not enemy_drops:
        print(f"\nNo enemies found that drop '{item_name}'.")
        return

    print(f"\n{'=' * 80}")
    print(f"Enemies that drop: {item_name}")
    if rbr_active or weekly_boost:
        print(f"  (RBR: {'Yes' if rbr_active else 'No'}, Weekly Boost: {weekly_boost.value if weekly_boost else 'None'})")
    print(f"{'=' * 80}\n")

    for i, enemy_info in enumerate(enemy_drops, 1):
        print(f"{i}. {enemy_info['enemy']} (Episode {enemy_info['episode']})")
        if enemy_info.get("section_id") is not None:
            print(f"   Section ID: {enemy_info['section_id']}")
        dar_str = f"{enemy_info['dar']:.4f}"
        rdr_str = f"{enemy_info['rdr']:.6f}"
        if enemy_info["adjusted_dar"] != enemy_info["dar"]:
            dar_str += f" -> {enemy_info['adjusted_dar']:.4f}"
        if enemy_info.get("adjusted_rdr") and enemy_info["adjusted_rdr"] != enemy_info["rdr"]:
            rdr_str += f" -> {enemy_info['adjusted_rdr']:.6f}"
        print(f"   DAR: {dar_str}, RDR: {rdr_str}")
        print(f"   Drop Rate: {enemy_info['drop_rate_percent']:.6f}% per kill")
        drop_rate = enemy_info["drop_rate"]
        if drop_rate > 0:
            expected_kills = 1 / drop_rate
            print(f"   (1 in {expected_kills:.1f} kills)")
            # Euler's number: probability of at least 1 drop after N kills = 1 - (1 - p)^N
            # For N = 1/p (expected kills), probability ≈ 1 - 1/e ≈ 63.21%
            euler_probability = 1 - math.exp(-1)
            print(f"   Probability after {expected_kills:.0f} kills: {euler_probability * 100:.2f}% (1 - 1/e)")
            # Calculate runs for 95% probability
            runs_95 = calculate_runs_for_probability(drop_rate, 0.95)
            print(f"   Kills for 95% probability: {runs_95:.1f}")
        else:
            print(f"   (Drop rate is 0 - item may not be in price guide or area not eligible)")
        print()


def display_box_drops(box_drops, item_name):
    """Display boxes that drop the item."""
    if not box_drops:
        print(f"\nNo boxes found that drop '{item_name}'.")
        return

    print(f"\n{'=' * 80}")
    print(f"Boxes that drop: {item_name}")
    print(f"  (Note: Box drops are NOT affected by DAR, RDR, or any drop rate bonuses)")
    print(f"{'=' * 80}\n")

    for i, box_info in enumerate(box_drops, 1):
        print(f"{i}. {box_info['area']} (Episode {box_info['episode']})")
        if box_info.get("section_id") is not None:
            print(f"   Section ID: {box_info['section_id']}")
        else:
            print(f"   (technique drop - not Section ID dependent)")
        print(f"   Drop Rate: {box_info['drop_rate_percent']:.6f}% per box")
        drop_rate = box_info["drop_rate"]
        if drop_rate > 0:
            expected_boxes = 1 / drop_rate
            print(f"   (1 in {expected_boxes:.1f} boxes)")
            # Euler's number: probability of at least 1 drop after N boxes = 1 - (1 - p)^N
            # For N = 1/p (expected boxes), probability ≈ 1 - 1/e ≈ 63.21%
            euler_probability = 1 - math.exp(-1)
            print(f"   Probability after {expected_boxes:.0f} boxes: {euler_probability * 100:.2f}% (1 - 1/e)")
            # Calculate runs for 95% probability
            runs_95 = calculate_runs_for_probability(drop_rate, 0.95)
            print(f"   Boxes for 95% probability: {runs_95:.1f}")
        else:
            print(f"   (Drop rate is 0 - item may not be in price guide or area not eligible)")
        print()


def display_results(results, item_name, top_n: Optional[int] = 10, is_disk: bool = False, show_details: bool = False):
    """Display the search results in a formatted way."""
    if not results:
        print(f"\nNo quests found that drop '{item_name}'.")
        return

    print(f"\n{'=' * 80}")
    print(f"Best quests for hunting: {item_name}")
    print(f"{'=' * 80}\n")

    # Show top N results
    top_results = results[:top_n] if top_n else results

    for i, result in enumerate(top_results, 1):
        print(f"{i}. Quest: {result['quest_name']} ({result['long_name']})")
        print(f"   Section ID: {result['section_id']}")
        print(f"   Drop Probability: {result['percentage']:.6f}% per quest run")
        probability = result["probability"]
        expected_runs = 1 / probability
        print(f"   (1 in {expected_runs:.1f} quest runs)")
        # Euler's number: probability of at least 1 drop after N runs = 1 - (1 - p)^N
        # For N = 1/p (expected runs), probability ≈ 1 - 1/e ≈ 63.21%
        euler_probability = 1 - math.exp(-1)
        print(f"   Probability after {expected_runs:.0f} runs: {euler_probability * 100:.2f}% (1 - 1/e)")
        # Calculate runs for 95% probability
        runs_95 = calculate_runs_for_probability(probability, 0.95)
        print(f"   Runs for 95% probability: {runs_95:.1f}")
        print(f"   Contributions:")

        # For disks, group by area if not showing details
        if is_disk and not show_details:
            # Group technique contributions by area
            area_contributions = defaultdict(lambda: {"total_prob": 0.0, "enemies": [], "total_count": 0.0})
            box_contributions = []

            for contrib in result["contributions"]:
                if contrib.get("source") == "Box":
                    box_contributions.append(contrib)
                elif contrib.get("source") == "Technique":
                    area = contrib.get("area", "Unknown")
                    area_contributions[area]["total_prob"] += contrib["probability"]
                    area_contributions[area]["enemies"].append(contrib)
                    area_contributions[area]["total_count"] += contrib.get("count", 0.0)

            # Display area-grouped contributions
            for area in sorted(area_contributions.keys()):
                area_data = area_contributions[area]
                print(f"     - Area: {area}")
                print(f"       Total Contribution: {area_data['total_prob'] * 100:.6f}%")
                enemy_types = len(area_data["enemies"])
                total_enemies = area_data["total_count"]
                print(f"       ({total_enemies:.0f} total enemies in this area, of {enemy_types} enemy type(s))")

            # Display box contributions
            for contrib in box_contributions:
                print(f"     - Box ({contrib['area']}): {contrib['box_count']} boxes")
                print(f"       Drop Rate: {contrib['drop_rate']:.6f}")
                if contrib.get("technique"):
                    print(f"       (technique drop)")
                print(f"       Contribution: {contrib['probability'] * 100:.6f}%")
        else:
            # Show detailed contributions
            for contrib in result["contributions"]:
                if contrib.get("source") == "Box":
                    # Box contribution
                    print(f"     - Box ({contrib['area']}): {contrib['box_count']} boxes")
                    print(f"       Drop Rate: {contrib['drop_rate']:.6f}")
                    if contrib.get("technique"):
                        print(f"       (technique drop)")
                    print(f"       Contribution: {contrib['probability'] * 100:.6f}%")
                elif contrib.get("source") == "Technique":
                    # Technique drop from enemy
                    print(f"     - {contrib['enemy']} (Area: {contrib.get('area', 'Unknown')}): {contrib['count']} kills")
                    dar_str = f"{contrib['dar']:.4f}"
                    if "adjusted_dar" in contrib and contrib["adjusted_dar"] != contrib["dar"]:
                        dar_str += f" -> {contrib['adjusted_dar']:.4f}"
                    print(f"       DAR: {dar_str} (technique drop - RDR not applicable)")
                    print(f"       Contribution: {contrib['probability'] * 100:.6f}%")
                else:
                    # Enemy contribution (regular weapon)
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
        print(f"... and {len(results) - top_n} more results.\n")

    # Show best overall
    best = results[0]
    best_probability = best["probability"]
    best_expected_runs = 1 / best_probability
    euler_probability = 1 - math.exp(-1)
    best_runs_95 = calculate_runs_for_probability(best_probability, 0.95)
    print(f"{'=' * 80}")
    print(f"BEST OPTION:")
    print(f"  Quest: {best['quest_name']} ({best['long_name']})")
    print(f"  Section ID: {best['section_id']}")
    print(f"  Drop Chance: {best['percentage']:.6f}% per quest run")
    print(f"  Expected runs: {best_expected_runs:.1f}")
    print(f"  Probability after {best_expected_runs:.0f} runs: {euler_probability * 100:.2f}% (1 - 1/e)")
    print(f"  Runs for 95% probability: {best_runs_95:.1f}")
    print(f"\n  Note: Killing more enemies/opening more boxes increases the likelihood of")
    print(f"  receiving an item, but it will never be 100% guaranteed. The probability")
    print(f"  of at least 1 drop after N attempts (where N = 1/drop_rate) is always")
    print(f"  approximately 63.21% (1 - 1/e, where e = Euler's number ≈ 2.718).")
    print(f"{'=' * 80}\n")


def main():
    """Main function to run the item hunting optimizer."""
    parser = argparse.ArgumentParser(description="Find the best quest and Section ID for hunting a specific item")
    parser.add_argument("item", help="Name of the item to search for")
    # RBR arguments - mutually exclusive
    rbr_group = parser.add_mutually_exclusive_group()
    rbr_group.add_argument(
        "--rbr-active",
        action="store_true",
        help="Enable RBR boost (+25%% DAR, +25%% RDR) for all quests",
    )
    rbr_group.add_argument(
        "--rbr-list",
        type=str,
        nargs="+",
        default=None,
        help="Enable RBR boost only for specified quests (provide quest short names, e.g., --rbr-list MU1 MU2 MU3)",
    )
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
        "--event-active",
        type=str,
        choices=[event.value for event in EventType],
        default=None,
        help="Active event type: Easter, Halloween, Christmas, ValentinesDay, or Anniversary (default: None)",
    )
    parser.add_argument(
        "--exclude-event-quests",
        action="store_true",
        help="Exclude event quests from the search (quests marked with is_event_quest: true)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Show only top N results (default: 10, 0 for all)",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Show detailed contribution breakdown",
    )
    args = parser.parse_args()
    weekly_boost = WeeklyBoost(args.weekly_boost) if args.weekly_boost else None
    event_type = EventType(args.event_active) if args.event_active else None

    item = args.item

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

    # Determine RBR settings
    rbr_active = args.rbr_active
    rbr_list = args.rbr_list if args.rbr_list else None

    # Find best quests
    print(f"Searching for '{item}' across all quests and Section IDs...")
    if rbr_active:
        print(f"  RBR Active: Yes (all quests)")
    elif rbr_list:
        print(f"  RBR Active: Yes (quests: {', '.join(rbr_list)})")
    else:
        print(f"  RBR Active: No")
    if weekly_boost:
        print(f"  Weekly Boost: {weekly_boost}")
    print(f"  Event Active: {event_type.value if event_type else 'None'}")
    if args.quests:
        print(f"  Quest Filter: {', '.join(args.quests)}")
    if args.exclude_event_quests:
        print(f"  Exclude Event Quests: Yes")
    print()

    # Identify item type
    item_type = calculator.price_guide.identify_item_type(item)

    # Find enemies that drop the item
    enemy_drops = calculator.find_enemies_that_drop_weapon(item, rbr_active=rbr_active, rbr_list=rbr_list, weekly_boost=weekly_boost, event_type=event_type)

    # Display enemy drops based on item type
    if item_type == "disk":
        # For disks (techniques), show area-grouped display
        display_disk_drops(enemy_drops, item, rbr_active or (rbr_list is not None and len(rbr_list) > 0), weekly_boost)
    else:
        # For regular items, show standard display
        display_enemy_drops(enemy_drops, item, rbr_active or (rbr_list is not None and len(rbr_list) > 0), weekly_boost)

    # Find boxes that drop the item
    box_drops = calculator.find_boxes_that_drop_weapon(item)

    # Display box drops
    display_box_drops(box_drops, item)

    # Find best quests
    results = calculator.find_best_quests_for_item(
        item,
        rbr_active=rbr_active,
        rbr_list=rbr_list,
        weekly_boost=weekly_boost,
        quest_filter=args.quests,
        event_type=event_type,
    )

    # Display quest results
    display_results(results, item, top_n=args.top_n, is_disk=(item_type == "disk"), show_details=args.details)


if __name__ == "__main__":
    main()
