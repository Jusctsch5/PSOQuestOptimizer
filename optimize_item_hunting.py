"""
Script to find the best quest and Section ID for hunting a specific item.

Searches through all quests and Section IDs to find which combination
has the highest drop probability for the specified item (enemy drops + box drops).
"""

import argparse
import math
from pathlib import Path
from typing import Optional

from quest_optimizer.quest_calculator import QuestCalculator, WeeklyBoost


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
        return float('inf')
    if drop_rate >= 1:
        return 1.0
    if target_probability >= 1:
        return float('inf')
    
    # N = ln(1 - target_probability) / ln(1 - drop_rate)
    numerator = math.log(1 - target_probability)
    denominator = math.log(1 - drop_rate)
    
    if denominator == 0:
        return float('inf')
    
    return numerator / denominator


def display_enemy_drops(enemy_drops, item_name, rbr_active: bool, weekly_boost):
    """Display enemies that drop the item."""
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
        print(f"   Section ID: {enemy_info['section_id']}")
        dar_str = f"{enemy_info['dar']:.4f}"
        rdr_str = f"{enemy_info['rdr']:.6f}"
        if enemy_info["adjusted_dar"] != enemy_info["dar"]:
            dar_str += f" -> {enemy_info['adjusted_dar']:.4f}"
        if enemy_info["adjusted_rdr"] != enemy_info["rdr"]:
            rdr_str += f" -> {enemy_info['adjusted_rdr']:.6f}"
        print(f"   DAR: {dar_str}, RDR: {rdr_str}")
        print(f"   Drop Rate: {enemy_info['drop_rate_percent']:.6f}% per kill")
        drop_rate = enemy_info['drop_rate']
        expected_kills = 1 / drop_rate
        print(f"   (1 in {expected_kills:.1f} kills)")
        # Euler's number: probability of at least 1 drop after N kills = 1 - (1 - p)^N
        # For N = 1/p (expected kills), probability ≈ 1 - 1/e ≈ 63.21%
        euler_probability = 1 - math.exp(-1)
        print(f"   Probability after {expected_kills:.0f} kills: {euler_probability * 100:.2f}% (1 - 1/e)")
        # Calculate runs for 95% probability
        runs_95 = calculate_runs_for_probability(drop_rate, 0.95)
        print(f"   Kills for 95% probability: {runs_95:.1f}")
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
        print(f"   Section ID: {box_info['section_id']}")
        print(f"   Drop Rate: {box_info['drop_rate_percent']:.6f}% per box")
        drop_rate = box_info['drop_rate']
        expected_boxes = 1 / drop_rate
        print(f"   (1 in {expected_boxes:.1f} boxes)")
        # Euler's number: probability of at least 1 drop after N boxes = 1 - (1 - p)^N
        # For N = 1/p (expected boxes), probability ≈ 1 - 1/e ≈ 63.21%
        euler_probability = 1 - math.exp(-1)
        print(f"   Probability after {expected_boxes:.0f} boxes: {euler_probability * 100:.2f}% (1 - 1/e)")
        # Calculate runs for 95% probability
        runs_95 = calculate_runs_for_probability(drop_rate, 0.95)
        print(f"   Boxes for 95% probability: {runs_95:.1f}")
        print()


def display_results(results, item_name, top_n: Optional[int] = 10):
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
        probability = result['probability']
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
        print(f"... and {len(results) - top_n} more results.\n")

    # Show best overall
    best = results[0]
    best_probability = best['probability']
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
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Show only top N results (default: 10, 0 for all)",
    )
    args = parser.parse_args()
    weekly_boost = WeeklyBoost(args.weekly_boost) if args.weekly_boost else None

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

    # Find best quests
    print(f"Searching for '{item}' across all quests and Section IDs...")
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

    # Find enemies that drop the item
    enemy_drops = calculator.find_enemies_that_drop_weapon(
        item, rbr_active=args.rbr, weekly_boost=weekly_boost, christmas_boost=args.christmas_boost
    )

    # Display enemy drops first
    display_enemy_drops(enemy_drops, item, args.rbr, weekly_boost)

    # Find boxes that drop the item
    box_drops = calculator.find_boxes_that_drop_weapon(item)

    # Display box drops
    display_box_drops(box_drops, item)

    # Find best quests
    results = calculator.find_best_quests_for_weapon(
        item, rbr_active=args.rbr, weekly_boost=weekly_boost, quest_filter=args.quests, christmas_boost=args.christmas_boost
    )

    # Display quest results
    display_results(results, item, top_n=args.top_n)


if __name__ == "__main__":
    main()
