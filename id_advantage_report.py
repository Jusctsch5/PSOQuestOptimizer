"""
Generate a weekly comparative-advantage brief for one or all Section IDs.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from optimize_quests import QuestOptimizer, load_quest_times
from quest_optimizer.id_advantage import advantage_rows, advantage_rows_all_ids
from quest_optimizer.quest_calculator import EventType, QuestCalculator, SectionIds, WeeklyBoost


def _section_id_choices() -> List[str]:
    return [sid.value for sid in SectionIds]


def _print_rows(rows: List[Dict], top_n: Optional[int]) -> None:
    if top_n:
        rows = rows[:top_n]

    if not rows:
        print("No results.")
        return

    print(
        f"{'Rank':<5} {'Quest':<44} {'Focus ID':<12} {'Score':<10} {'ID Rank':<8} "
        f"{'Best ID':<12} {'Edge Ref':<12} {'Edge':<10} {'Top Item':<30}"
    )
    print("-" * 160)

    for index, row in enumerate(rows, start=1):
        top_item = row.get("top_item", {})
        top_item_name = top_item.get("item", "-") if isinstance(top_item, dict) else "-"
        top_item_name = str(top_item_name)[:30]

        print(
            f"{index:<5} "
            f"{row.get('quest_display', row['quest_name'])[:44]:<44} "
            f"{row['focus_id']:<12} "
            f"{row['focus_score']:<10.4f} "
            f"{row['rank_among_ids']:<8} "
            f"{row['best_id']:<12} "
            f"{row['edge_reference_id']:<12} "
            f"{row['edge_score']:<10.4f} "
            f"{top_item_name:<30}"
        )


def _print_scenario_header(args: argparse.Namespace) -> None:
    print("ID advantage brief")
    print(f"  Focus ID: {args.focus_id or 'All (per-ID top N)'}")
    print(f"  Baseline: {args.baseline}")
    print(f"  Weekly Boost: {args.weekly_boost or 'None'}")
    print(f"  Event Active: {args.event_active or 'None'}")
    print(f"  Daily Luck: {args.daily_luck}%")
    print()


def _json_payload(
    focus_id: Optional[str],
    baseline: str,
    rows: Optional[List[Dict]] = None,
    by_id: Optional[Dict[str, List[Dict]]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "focus_id": focus_id,
        "baseline": baseline,
    }
    if focus_id is not None:
        payload["rows"] = rows or []
    else:
        payload["by_id"] = by_id or {}
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find quests where a Section ID has comparative advantage versus other IDs."
    )
    parser.add_argument(
        "--focus-id",
        default=None,
        choices=_section_id_choices(),
        help="Section ID to evaluate. Omit to print top --top-n quests for every Section ID.",
    )
    parser.add_argument("--baseline", default="second_best", choices=["second_best", "median"], help="Edge baseline.")

    # Reuse familiar optimize_quests toggles
    rbr_group = parser.add_mutually_exclusive_group()
    rbr_group.add_argument("--rbr-active", action="store_true", help="Enable RBR boost for all quests.")
    rbr_group.add_argument("--rbr-list", nargs="+", metavar="QUEST", help="Enable RBR boost only for listed short names.")

    parser.add_argument(
        "--weekly-boost",
        type=str,
        choices=[boost.value for boost in WeeklyBoost],
        default=None,
        help="Weekly boost type.",
    )
    parser.add_argument(
        "--event-active",
        type=str,
        choices=[event.value for event in EventType],
        default=None,
        help="Active event type.",
    )
    parser.add_argument("--daily-luck", type=int, default=0, help="Percent added to RDR multiplier.")
    parser.add_argument("--episode", type=int, choices=[1, 2, 4], default=None, help="Episode filter.")
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="With --focus-id: cap to top N quests. Without --focus-id: top N per Section ID.",
    )
    parser.add_argument("--quest", type=str, nargs="+", default=None, help="Filter by one or more short quest names.")
    parser.add_argument("--exclude-event-quests", action="store_true", help="Exclude event quests.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    parser.add_argument("--quest-times", type=str, default=None, help="Path to quest_times.json.")
    parser.add_argument("--drop-table", type=str, default=None, help="Path to drop_tables_ultimate.json.")
    parser.add_argument("--price-guide", type=str, default=None, help="Path to price guide directory.")
    parser.add_argument("--quests-data", type=str, default=None, help="Path to quests.json.")

    args = parser.parse_args()

    weekly_boost = WeeklyBoost(args.weekly_boost) if args.weekly_boost else None
    event_type = EventType(args.event_active) if args.event_active else None

    base_path = Path(__file__).parent
    drop_table_path = Path(args.drop_table) if args.drop_table else base_path / "drop_tables" / "drop_tables_ultimate.json"
    price_guide_path = Path(args.price_guide) if args.price_guide else base_path / "price_guide" / "data"
    quests_file_path = Path(args.quests_data) if args.quests_data else base_path / "quests" / "quests.json"
    times_path = Path(args.quest_times) if args.quest_times else base_path / "quest_times.json"

    if not drop_table_path.exists():
        print(f"Error: Drop table not found at {drop_table_path}")
        return 1
    if not price_guide_path.exists():
        print(f"Error: Price guide directory not found at {price_guide_path}")
        return 1
    if not quests_file_path.exists():
        print(f"Error: Quests file not found at {quests_file_path}")
        return 1

    calculator = QuestCalculator(drop_table_path, price_guide_path, quests_file_path)
    optimizer = QuestOptimizer(calculator)

    quests_data = calculator.quest_data
    if args.quest:
        quest_filters = {q.lower() for q in args.quest}
        quests_data = [q for q in quests_data if q.get("quest_name", "").lower() in quest_filters]

    if args.exclude_event_quests:
        quests_data = [q for q in quests_data if not calculator._is_event_quest(q)]

    quest_times = load_quest_times(times_path)

    rank_by_section = optimizer.rank_by_section_id(
        quests_data,
        rbr_active=args.rbr_active,
        rbr_list=args.rbr_list,
        weekly_boost=weekly_boost,
        quest_times=quest_times,
        episode_filter=args.episode,
        event_type=event_type,
        exclude_event_quests=args.exclude_event_quests,
        daily_luck=args.daily_luck,
    )

    if args.focus_id is not None:
        rows = advantage_rows(rank_by_section, focus_id=args.focus_id, baseline=args.baseline)
        rows = rows[: args.top_n]
        if args.json:
            print(json.dumps(_json_payload(args.focus_id, args.baseline, rows=rows), indent=2))
        else:
            _print_scenario_header(args)
            _print_rows(rows, top_n=None)
    else:
        by_id = advantage_rows_all_ids(
            rank_by_section,
            _section_id_choices(),
            baseline=args.baseline,
            top_n=args.top_n,
        )
        if args.json:
            print(json.dumps(_json_payload(None, args.baseline, by_id=by_id), indent=2))
        else:
            _print_scenario_header(args)
            for sid in _section_id_choices():
                print(f"=== {sid} (top {args.top_n}) ===")
                print()
                _print_rows(by_id[sid], top_n=None)
                print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
