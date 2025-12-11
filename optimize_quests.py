"""
Quest optimizer for ranking RBR quests by PD efficiency.

Ranks quests by PD per minute/hour, with filtering options.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Import from same directory
from quest_optimizer.quest_calculator import QuestCalculator, WeeklyBoost


class QuestOptimizer:
    """Optimize quest selection based on PD value and time."""

    def __init__(self, calculator: QuestCalculator):
        """
        Initialize optimizer with a quest calculator.

        Args:
            calculator: QuestCalculator instance
        """
        self.calculator = calculator

    def _get_top_items(self, enemy_breakdown: Dict, top_n: int = 3) -> List[Dict]:
        """
        Calculate the top N items by PD value contribution.

        Args:
            enemy_breakdown: Dictionary of enemy breakdown data
            top_n: Number of top items to return

        Returns:
            List of dictionaries with item_name, enemy, pd_value, and pd_per_quest
            sorted by PD value (descending)
        """
        item_data = {}  # item_name -> {pd_value, enemies: [list of enemies]}

        for enemy, data in enemy_breakdown.items():
            if "error" in data:
                continue

            item = data.get("item", "Unknown")
            pd_value = data.get("pd_value", 0.0)

            if item not in item_data:
                item_data[item] = {"pd_value": 0.0, "enemies": []}

            item_data[item]["pd_value"] += pd_value
            # Track which enemy drops this item (for display)
            if enemy not in item_data[item]["enemies"]:
                item_data[item]["enemies"].append(enemy)

        # Convert to list of dicts and sort by PD value (descending)
        result = []
        for item_name, data in item_data.items():
            result.append({"item": item_name, "pd_value": data["pd_value"], "enemies": data["enemies"]})

        # Sort by PD value (descending) and return top N
        result.sort(key=lambda x: x["pd_value"], reverse=True)
        return result[:top_n]

    def rank_quests(
        self,
        quests_data: List[Dict],
        section_id: str,
        rbr_active: bool = False,
        weekly_boost: Optional[WeeklyBoost] = None,
        quest_times: Optional[Dict[str, float]] = None,
        episode_filter: Optional[int] = None,
    ) -> List[Dict]:
        """
        Rank quests by PD efficiency.

        Args:
            quests_data: List of quest dictionaries
            section_id: Section ID to use for calculations
            rbr_active: Whether RBR boost is active
            weekly_boost: Type of weekly boost (WeeklyBoost enum or None)
            quest_times: Dictionary mapping quest names to time in minutes
            episode_filter: Filter by episode (1, 2, or 4), or None for all

        Returns:
            List of quest results sorted by PD per minute (descending)
        """
        results = []

        for quest_data in quests_data:
            # Apply episode filter
            if episode_filter is not None:
                if quest_data.get("episode") != episode_filter:
                    continue

            # Calculate quest value
            value_result = self.calculator.calculate_quest_value(quest_data, section_id, rbr_active, weekly_boost)

            # Get quest time
            quest_name = quest_data.get("quest_name", "Unknown")
            quest_time = quest_times.get(quest_name) if quest_times else None

            # Calculate PD per minute
            pd_per_minute = None
            if quest_time and quest_time > 0:
                pd_per_minute = value_result["total_pd"] / quest_time

            # Calculate top items by PD value (get up to 10 to have enough for display)
            top_items = self._get_top_items(value_result["enemy_breakdown"], top_n=10)

            result = {
                "quest_name": quest_name,
                "long_name": quest_data.get("long_name"),
                "episode": quest_data.get("episode"),
                "areas": quest_data.get("areas", []),  # List of areas for this quest
                "total_pd": value_result["total_pd"],
                "total_pd_drops": value_result.get("total_pd_drops", 0.0),
                "total_enemies": value_result["total_enemies"],
                "quest_time_minutes": quest_time,
                "pd_per_minute": pd_per_minute,
                "section_id": section_id,
                "rbr_active": rbr_active,
                "weekly_boost": weekly_boost,
                "enemy_breakdown": value_result["enemy_breakdown"],
                "pd_drop_breakdown": value_result.get("pd_drop_breakdown", {}),
                "completion_items_breakdown": value_result.get("completion_items_breakdown", {}),
                "completion_items_pd": value_result.get("completion_items_pd", 0.0),
                "top_items": top_items,
            }

            results.append(result)

        # Sort by PD per minute (descending), or by total PD if no time data
        results.sort(key=lambda x: x["pd_per_minute"] if x["pd_per_minute"] is not None else x["total_pd"], reverse=True)

        return results

    def rank_by_section_id(
        self,
        quests_data: List[Dict],
        rbr_active: bool = False,
        weekly_boost: Optional[WeeklyBoost] = None,
        quest_times: Optional[Dict[str, float]] = None,
        episode_filter: Optional[int] = None,
    ) -> Dict[str, List[Dict]]:
        """
        Rank quests for all Section IDs.

        Returns:
            Dictionary mapping Section ID to ranked quest list
        """
        section_ids = [
            "Viridia",
            "Greenill",
            "Skyly",
            "Bluefull",
            "Purplenum",
            "Pinkal",
            "Redria",
            "Oran",
            "Yellowboze",
            "Whitill",
        ]

        results = {}
        for section_id in section_ids:
            results[section_id] = self.rank_quests(
                quests_data, section_id, rbr_active, weekly_boost, quest_times, episode_filter
            )

        return results

    def print_rankings(
        self, rankings: List[Dict], top_n: Optional[int] = None, show_details: bool = False, notable_items_count: int = 5
    ):
        """
        Print quest rankings in a readable format.

        Args:
            rankings: List of ranked quest results
            top_n: Show only top N quests (None for all)
            show_details: Show detailed enemy breakdown
            notable_items_count: Number of notable item columns to show (default: 5)
        """
        if top_n:
            rankings = rankings[:top_n]

        # Calculate maximum width needed for each notable item column
        max_item_width = 0
        for result in rankings:
            top_items = result.get("top_items", [])
            for item_data in top_items[:notable_items_count]:
                if isinstance(item_data, dict):
                    item_name = item_data.get("item", "Unknown")
                    enemy = item_data.get("enemies", ["Unknown"])[0] if item_data.get("enemies") else "Unknown"
                    pd_value = item_data.get("pd_value", 0.0)
                    # Format: "Item (Enemy: PD)"
                    item_str = f"{item_name} ({enemy}: {pd_value:.4f})"
                    max_item_width = max(max_item_width, len(item_str), len("Notable Item X"))
                else:
                    # Legacy format support
                    max_item_width = max(max_item_width, len(str(item_data)), len("Notable Item X"))

        # Ensure minimum width
        max_item_width = max(max_item_width, 20)

        # Check if we're showing multiple Section IDs (need to add Section ID column)
        show_section_id = len(rankings) > 0 and any(
            result.get("section_id") != rankings[0].get("section_id") for result in rankings
        )

        # Check if any quests have areas defined
        has_areas = any(result.get("areas") for result in rankings)

        # Calculate maximum width needed for areas column
        max_areas_width = len("Areas")  # At least as wide as header
        if has_areas:
            for result in rankings:
                areas = result.get("areas", [])
                if areas:
                    areas_str = ", ".join(areas)
                    max_areas_width = max(max_areas_width, len(areas_str))
                else:
                    max_areas_width = max(max_areas_width, len("N/A"))

        # Check if any quests have completion items
        has_completion_items = any(result.get("completion_items_pd", 0.0) > 0 for result in rankings)

        # Calculate maximum width needed for quest reward column
        max_reward_width = len("Quest Reward")  # At least as wide as header
        if has_completion_items:
            for result in rankings:
                completion_items_breakdown = result.get("completion_items_breakdown", {})
                reward_pd = result.get("completion_items_pd", 0.0)
                if reward_pd > 0 and completion_items_breakdown:
                    # Format: "Item1 (PD), Item2 (PD)" or "Item (PD)"
                    item_strs = []
                    for item_name, data in completion_items_breakdown.items():
                        item_pd = data.get("total_pd", 0.0)
                        item_strs.append(f"{item_name} ({item_pd:.4f})")
                    reward_str = ", ".join(item_strs)
                else:
                    reward_str = ""
                max_reward_width = max(max_reward_width, len(reward_str), len("Quest Reward"))

        # Calculate total table width
        reward_column_width = max_reward_width if has_completion_items else 0
        divider_width = 1 if has_completion_items else 0  # Space for divider "|"
        if show_section_id:
            if has_areas:
                fixed_width = (
                    6 + 30 + 12 + max_areas_width + 8 + 12 + 12 + 10 + 15 + reward_column_width + divider_width
                )  # Rank + Quest Name + Section ID + Areas + Episode + PD + PD/min + Enemies + Raw PD/Quest + Quest Reward + Divider
            else:
                fixed_width = (
                    6 + 30 + 12 + 8 + 12 + 12 + 10 + 15 + reward_column_width + divider_width
                )  # Rank + Quest Name + Section ID + Episode + PD + PD/min + Enemies + Raw PD/Quest + Quest Reward + Divider
        else:
            if has_areas:
                fixed_width = (
                    6 + 30 + max_areas_width + 8 + 12 + 12 + 10 + 15 + reward_column_width + divider_width
                )  # Rank + Quest Name + Areas + Episode + PD + PD/min + Enemies + Raw PD/Quest + Quest Reward + Divider
            else:
                fixed_width = (
                    6 + 30 + 8 + 12 + 12 + 10 + 15 + reward_column_width + divider_width
                )  # Rank + Quest Name + Episode + PD + PD/min + Enemies + Raw PD/Quest + Quest Reward + Divider
        total_width = fixed_width + (max_item_width * notable_items_count)

        # Print header
        header_parts = [f"{'Rank':<6}", f"{'Quest Name':<30}"]
        if show_section_id:
            header_parts.append(f"{'Section ID':<12}")
        if has_areas:
            header_parts.append(f"{'Areas':<{max_areas_width}}")
        header_parts.extend(
            [f"{'Episode':<8}", f"{'PD/Quest':<12}", f"{'PD/min':<12}", f"{'Enemies':<10}", f"{'Raw PD/Quest':<15}"]
        )
        # Add Quest Reward column if any quest has completion items
        if has_completion_items:
            header_parts.append(f"{'Quest Reward':<{max_reward_width}}")
        # Add divider and spacing before notable items
        if has_completion_items:
            header_parts.append("|")  # Divider
        # Add notable item columns
        for i in range(1, notable_items_count + 1):
            header_parts.append(f"{f'Notable Item {i}':<{max_item_width}}")
        print("\n" + " ".join(header_parts))
        print("-" * total_width)

        for idx, result in enumerate(rankings, 1):
            # Format quest name: "Long Name (Short Name)" or just "Short Name"
            short_name = result["quest_name"]
            long_name = result.get("long_name")
            if long_name:
                quest_name = f"{long_name} ({short_name})"
            else:
                quest_name = short_name
            quest_name = quest_name[:28]  # Truncate if too long

            episode = result["episode"]
            section_id = result.get("section_id", "Unknown")
            areas = result.get("areas", [])
            total_pd = result["total_pd"]
            pd_per_min = result["pd_per_minute"]
            enemies = result["total_enemies"]
            raw_pd_drops = result.get("total_pd_drops", 0.0)
            top_items = result.get("top_items", [])

            pd_str = f"{total_pd:.4f}"
            pd_per_min_str = f"{pd_per_min:.4f}" if pd_per_min else "N/A"
            raw_pd_str = f"{raw_pd_drops:.4f}"

            # Format areas: "Area1, Area2" or "N/A" if not present
            if areas:
                areas_str = ", ".join(areas)
            else:
                areas_str = "N/A"

            # Build row parts
            row_parts = [f"{idx:<6}", f"{quest_name:<30}"]
            if show_section_id:
                row_parts.append(f"{section_id:<12}")
            if has_areas:
                row_parts.append(f"{areas_str:<{max_areas_width}}")
            row_parts.extend([f"{episode:<8}", f"{pd_str:<12}", f"{pd_per_min_str:<12}", f"{enemies:<10}", f"{raw_pd_str:<15}"])

            # Add Quest Reward column if any quest has completion items
            if has_completion_items:
                completion_items_breakdown = result.get("completion_items_breakdown", {})
                reward_pd = result.get("completion_items_pd", 0.0)
                if reward_pd > 0 and completion_items_breakdown:
                    # Format: "Item1 (PD), Item2 (PD)" or "Item (PD)"
                    item_strs = []
                    for item_name, data in completion_items_breakdown.items():
                        item_pd = data.get("total_pd", 0.0)
                        item_strs.append(f"{item_name} ({item_pd:.4f})")
                    reward_str = ", ".join(item_strs)
                else:
                    reward_str = ""
                row_parts.append(f"{reward_str:<{max_reward_width}}")
                row_parts.append("|")  # Divider

            # Add notable item columns
            for i in range(notable_items_count):
                if i < len(top_items) and top_items[i]:
                    item_data = top_items[i]
                    if isinstance(item_data, dict):
                        item_name = item_data.get("item", "Unknown")
                        enemy = item_data.get("enemies", ["Unknown"])[0] if item_data.get("enemies") else "Unknown"
                        pd_value = item_data.get("pd_value", 0.0)
                        # Format: "Item (Enemy: PD)"
                        item_str = f"{item_name} ({enemy}: {pd_value:.4f})"
                    else:
                        # Legacy format support
                        item_str = str(item_data)
                    row_parts.append(f"{item_str:<{max_item_width}}")
                else:
                    row_parts.append(f"{'':<{max_item_width}}")

            print(" ".join(row_parts))

            if show_details and result.get("enemy_breakdown"):
                print("  Enemy Breakdown:")

                # Create table header
                print(
                    f"  {'Enemy':<20} {'Drop':<30} {'DAR':<10} {'RDR':<12} {'Rate':<12} {'Count':<8} {'Exp Drops':<12} {'PD Value':<12} {'Exp Value':<12}"
                )
                print("  " + "-" * 138)

                for enemy, data in result["enemy_breakdown"].items():
                    if "error" in data:
                        error_msg = data["error"][:28]  # Truncate long error messages
                        print(
                            f"  {enemy:<20} {error_msg:<30} {'-':<10} {'-':<12} {'-':<12} {data.get('count', 0):<8} {'-':<12} {'-':<12} {'-':<12}"
                        )
                    else:
                        item = data.get("item", "Unknown")
                        count = data.get("count", 0)
                        dar = data.get("dar", 0.0)
                        adjusted_dar = data.get("adjusted_dar", dar)
                        rdr = data.get("rdr", 0.0)
                        adjusted_rdr = data.get("adjusted_rdr", rdr)
                        # Rate = DAR * RDR (with boosts applied)
                        actual_rate = adjusted_dar * adjusted_rdr
                        expected_drops = data.get("expected_drops", 0.0)  # rate * count
                        item_price_pd = data.get("item_price_pd", 0.0)  # PD value per item
                        exp_value = data.get("pd_value", 0.0)  # expected_drops * item_price_pd

                        # Truncate long item names
                        item_display = item[:28] if len(item) <= 28 else item[:25] + "..."
                        enemy_display = enemy[:18] if len(enemy) <= 18 else enemy[:15] + "..."

                        print(
                            f"  {enemy_display:<20} {item_display:<30} {adjusted_dar:<10.6f} {adjusted_rdr:<12.8f} {actual_rate:<12.8f} {count:<8} {expected_drops:<12.8f} {item_price_pd:<12.8f} {exp_value:<12.8f}"
                        )
                print()

                # PD Drop Breakdown table
                if result.get("pd_drop_breakdown"):
                    print("  PD Drop Breakdown:")
                    print(f"  {'Enemy':<20} {'DAR':<10} {'PD Rate':<12} {'Count':<8} {'Exp PD Drops':<15}")
                    print("  " + "-" * 75)

                    total_pd_drops = result.get("total_pd_drops", 0.0)
                    for enemy, data in result["pd_drop_breakdown"].items():
                        enemy_display = enemy[:18] if len(enemy) <= 18 else enemy[:15] + "..."
                        adjusted_dar = data.get("adjusted_dar", 0.0)
                        pd_drop_rate = data.get("pd_drop_rate", 0.0)
                        count = data.get("count", 0)
                        expected_pd_drops = data.get("expected_pd_drops", 0.0)

                        print(
                            f"  {enemy_display:<20} {adjusted_dar:<10.6f} {pd_drop_rate:<12.8f} {count:<8} {expected_pd_drops:<15.8f}"
                        )

                    print(f"  {'Total':<20} {'':<10} {'':<12} {'':<8} {total_pd_drops:<15.8f}")
                    print()


def load_quest_times(times_path: Path) -> Dict[str, float]:
    """
    Load quest time estimates from JSON file.

    Expected format:
    {
        "quest_name": minutes,
        ...
    }
    """
    if not times_path.exists():
        return {}

    with open(times_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    """Main function with argparse support."""
    parser = argparse.ArgumentParser(
        description="Rank RBR quests by PD efficiency",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Rank all quests for Redria with RBR active and RDR boost
  python quest_optimizer.py --section-id Redria --rbr --weekly-boost RDR

  # Show top 10 quests for Episode 1 only
  python quest_optimizer.py --section-id Skyly --episode 1 --top-n 10

  # Show detailed breakdown for a specific quest
  python quest_optimizer.py --section-id Oran --quest MU1 --details

  # Rank across all Section IDs
  python quest_optimizer.py --section-id All --episode 1 --top-n 20
        """,
    )

    parser.add_argument(
        "--section-id",
        type=str,
        default="All",
        choices=[
            "Viridia",
            "Greenill",
            "Skyly",
            "Bluefull",
            "Purplenum",
            "Pinkal",
            "Redria",
            "Oran",
            "Yellowboze",
            "Whitill",
            "All",
        ],
        help="Section ID to use for drop calculations, or 'All' to rank across all IDs (default: All)",
    )

    parser.add_argument("--rbr", action="store_true", help="Enable RBR boost (+25%% DAR, +25%% RDR)")

    parser.add_argument(
        "--weekly-boost",
        type=str,
        choices=[boost.value for boost in WeeklyBoost],
        default=None,
        help="Weekly boost type: DAR, RDR, RareEnemy, XP, or None (default: None)",
    )

    parser.add_argument(
        "--episode", type=int, choices=[1, 2, 4], default=None, help="Filter by episode (1, 2, or 4). Omit for all episodes"
    )

    parser.add_argument("--top-n", type=int, default=None, help="Show only top N quests (default: show all)")

    parser.add_argument("--details", action="store_true", help="Show detailed enemy breakdown and PD drop tables")

    parser.add_argument("--notable-items", type=int, default=5, help="Number of notable item columns to show (default: 5)")

    parser.add_argument(
        "--quest-times",
        type=str,
        default=None,
        help="Path to quest_times.json file (default: quest_times.json in script directory)",
    )

    parser.add_argument(
        "--drop-table",
        type=str,
        default=None,
        help="Path to drop_tables_ultimate.json (default: drop_tables/drop_tables_ultimate.json)",
    )

    parser.add_argument(
        "--price-guide", type=str, default=None, help="Path to price guide directory (default: ../price_guide/data)"
    )

    parser.add_argument("--quests-data", type=str, default=None, help="Path to quests.json file (default: quests/quests.json)")

    parser.add_argument(
        "--quest", type=str, default=None, help="Filter to a specific quest by exact match on quest_name (shortname)"
    )

    args = parser.parse_args()
    weekly_boost = WeeklyBoost(args.weekly_boost) if args.weekly_boost else None

    # Set up paths
    base_path = Path(__file__).parent

    drop_table_path = Path(args.drop_table) if args.drop_table else base_path / "drop_tables" / "drop_tables_ultimate.json"
    price_guide_path = Path(args.price_guide) if args.price_guide else base_path / "price_guide" / "data"
    quests_file_path = Path(args.quests_data) if args.quests_data else base_path / "quests" / "quests.json"
    times_path = Path(args.quest_times) if args.quest_times else base_path / "quest_times.json"

    # Validate paths
    if not drop_table_path.exists():
        print(f"Error: Drop table not found at {drop_table_path}")
        print("Please run drop_table_parser.py first to generate the drop table.")
        return 1

    if not price_guide_path.exists():
        print(f"Error: Price guide directory not found at {price_guide_path}")
        return 1

    if not quests_file_path.exists():
        print(f"Error: Quests file not found at {quests_file_path}")
        return 1

    calculator = QuestCalculator(drop_table_path, price_guide_path, quests_file_path)
    optimizer = QuestOptimizer(calculator)

    # Filter to specific quest if requested
    if args.quest:
        quest_filter = args.quest.lower()
        quests_data = [quest for quest in calculator.quest_data if quest["quest_name"].lower() == quest_filter]
        print(f"Filtered to {len(quests_data)} quest(s) matching '{args.quest}'")
    else:
        quests_data = calculator.quest_data
        print(f"Loaded {len(quests_data)} quests")

    # Load quest times (optional)
    quest_times = load_quest_times(times_path)

    # Rank quests
    print(f"Ranking quests by PD efficiency...")
    if args.section_id == "All":
        print(f"  Section ID: All (ranking across all Section IDs)")
    else:
        print(f"  Section ID: {args.section_id}")
    print(f"  RBR Active: {args.rbr}")
    print(f"  Weekly Boost: {weekly_boost if weekly_boost else 'None'}")
    if args.episode:
        print(f"  Episode Filter: {args.episode}")
    if args.quest:
        print(f"  Quest Filter: {args.quest}")
    print()

    # Check if we should rank across all Section IDs
    if args.section_id == "All":
        # Rank for all Section IDs and combine results
        all_rankings = []
        section_ids = [
            "Viridia",
            "Greenill",
            "Skyly",
            "Bluefull",
            "Purplenum",
            "Pinkal",
            "Redria",
            "Oran",
            "Yellowboze",
            "Whitill",
        ]

        for section_id in section_ids:
            section_rankings = optimizer.rank_quests(
                quests_data,
                section_id=section_id,
                rbr_active=args.rbr,
                weekly_boost=weekly_boost,
                quest_times=quest_times,
                episode_filter=args.episode,
            )
            all_rankings.extend(section_rankings)

        # Sort combined results by PD per minute (or total PD if no time data)
        all_rankings.sort(key=lambda x: x["pd_per_minute"] if x["pd_per_minute"] is not None else x["total_pd"], reverse=True)

        rankings = all_rankings
    else:
        rankings = optimizer.rank_quests(
            quests_data,
            section_id=args.section_id,
            rbr_active=args.rbr,
            weekly_boost=args.weekly_boost,
            quest_times=quest_times,
            episode_filter=args.episode,
        )

    # Print results
    optimizer.print_rankings(rankings, top_n=args.top_n, show_details=args.details, notable_items_count=args.notable_items)

    return 0


if __name__ == "__main__":
    sys.exit(main())
