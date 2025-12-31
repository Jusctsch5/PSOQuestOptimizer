"""
API wrapper for optimize_quests functionality.
Designed to be called from JavaScript via Pyodide.
"""

import json
import traceback
from pathlib import Path
from typing import Any, Dict, List

from calculate_item_value import calculate_item_value as calc_item_value
from optimize_quests import QuestOptimizer
from price_guide import BasePriceStrategy, PriceGuideFixed
from price_guide.item_value_calculator import ItemValueCalculator
from quest_optimizer.quest_calculator import EventType, QuestCalculator, WeeklyBoost


def optimize_quests(
    drop_table_data: Dict,
    quests_data: List[Dict],
    price_guide_data: Dict[str, Dict],  # Dict mapping filename to JSON data
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Optimize quests based on form parameters.

    Args:
        drop_table_data: Drop table JSON data
        quests_data: List of quest dictionaries
        price_guide_data: Dict mapping filename (e.g., 'weapons.json') to JSON data
        params: Form parameters dict with keys:
            - section_id: str (default: "All")
            - rbr_active: bool (default: False)
            - rbr_list: Optional[List[str]] (default: None)
            - weekly_boost: Optional[str] (e.g., "DAR", "RDR", "RareEnemy", "XP")
            - event_active: Optional[str] (e.g., "Easter", "Halloween", "Christmas", etc.)
            - episode: Optional[int] (1, 2, or 4)
            - quest_filter: Optional[str] (quest short name to filter)
            - top_n: Optional[int] (limit results)
            - notable_items: int (default: 5)
            - show_details: bool (default: False)
            - exclude_event_quests: bool (default: False)
            - quest_times: Optional[Dict[str, float]] (quest name to minutes)

    Returns:
        Dict with keys:
            - rankings: List[Dict] of quest results
            - error: Optional[str] error message
    """

    # Create temporary directory structure in Pyodide filesystem
    base_path = Path("/tmp/pso_data")
    base_path.mkdir(parents=True, exist_ok=True)

    drop_table_path = base_path / "drop_tables_ultimate.json"
    quests_path = base_path / "quests.json"
    price_guide_dir = base_path / "price_guide" / "data"
    price_guide_dir.mkdir(parents=True, exist_ok=True)

    # Write drop table data
    with open(drop_table_path, "w", encoding="utf-8") as f:
        json.dump(drop_table_data, f)

    # Write quests data
    with open(quests_path, "w", encoding="utf-8") as f:
        json.dump(quests_data, f)

    # Write price guide data files
    for filename, data in price_guide_data.items():
        file_path = price_guide_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    # Initialize calculator and optimizer
    try:
        calculator = QuestCalculator(
            drop_table_path=drop_table_path,
            price_guide_path=price_guide_dir,
            quest_data_path=quests_path,
        )
        optimizer = QuestOptimizer(calculator)
    except Exception as e:
        tb = traceback.format_exc()
        return {"error": f"Failed to initialize calculator: {e}\n\nTraceback:\n{tb}", "rankings": []}

    # Parse parameters
    section_id = params.get("section_id", "All")
    rbr_active = params.get("rbr_active", False)
    rbr_list = params.get("rbr_list", None)

    # Parse weekly boost
    weekly_boost_str = params.get("weekly_boost")
    weekly_boost = None
    if weekly_boost_str:
        try:
            weekly_boost = WeeklyBoost(weekly_boost_str)
        except ValueError:
            return {"error": f"Invalid weekly_boost: {weekly_boost_str}", "rankings": []}

    # Parse event type
    event_active_str = params.get("event_active")
    event_type = None
    if event_active_str:
        try:
            event_type = EventType(event_active_str)
        except ValueError:
            return {"error": f"Invalid event_active: {event_active_str}", "rankings": []}

    quest_filter = params.get("quest_filter")
    show_details = params.get("show_details", False)
    exclude_event_quests = params.get("exclude_event_quests", False)
    quest_times = params.get("quest_times", {})

    # Filter quests if needed (quest_filter can be a list of quest names)
    quests_to_process = calculator.quest_data
    if quest_filter:
        # Handle both single string (backward compatibility) and list
        if isinstance(quest_filter, str):
            quest_filters = [quest_filter.lower()]
        else:
            quest_filters = [q.lower() for q in quest_filter]

        quests_to_process = [q for q in quests_to_process if q.get("quest_name", "").lower() in quest_filters]

    if exclude_event_quests:
        quests_to_process = [q for q in quests_to_process if not calculator._is_event_quest(q)]

    # Rank quests
    try:
        if section_id == "All":
            # Rank across all Section IDs
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

            for sid in section_ids:
                section_rankings = optimizer.rank_quests(
                    quests_to_process,
                    section_id=sid,
                    rbr_active=rbr_active,
                    rbr_list=rbr_list,
                    weekly_boost=weekly_boost,
                    quest_times=quest_times,
                    episode_filter=None,
                    event_type=event_type,
                    exclude_event_quests=False,  # Already filtered above
                )
                all_rankings.extend(section_rankings)

            # Sort combined results
            all_rankings.sort(key=lambda x: x["pd_per_minute"] if x["pd_per_minute"] is not None else x["total_pd"], reverse=True)
            rankings = all_rankings
        else:
            rankings = optimizer.rank_quests(
                quests_to_process,
                section_id=section_id,
                rbr_active=rbr_active,
                rbr_list=rbr_list,
                weekly_boost=weekly_boost,
                quest_times=quest_times,
                episode_filter=None,
                event_type=event_type,
                exclude_event_quests=False,  # Already filtered above
            )

        # Convert to JSON-serializable format
        # Note: Some fields might not be JSON serializable, so we'll handle that
        serializable_rankings = []
        for ranking in rankings:
            serializable_ranking = {
                "quest_name": ranking.get("quest_name"),
                "long_name": ranking.get("long_name"),
                "episode": ranking.get("episode"),
                "section_id": ranking.get("section_id"),
                "total_pd": float(ranking.get("total_pd", 0.0)),
                "total_pd_drops": float(ranking.get("total_pd_drops", 0.0)),
                "total_enemies": ranking.get("total_enemies", 0),
                "quest_time_minutes": ranking.get("quest_time_minutes"),
                "pd_per_minute": float(ranking.get("pd_per_minute")) if ranking.get("pd_per_minute") is not None else None,
                "rbr_active": ranking.get("rbr_active", False),
                "weekly_boost": ranking.get("weekly_boost").value if ranking.get("weekly_boost") else None,
                "top_items": ranking.get("top_items", []),
                "completion_items_breakdown": ranking.get("completion_items_breakdown", {}),
                "completion_items_pd": float(ranking.get("completion_items_pd", 0.0)),
            }

            # Add detailed breakdown if show_details is True
            if show_details:
                serializable_ranking["enemy_breakdown"] = ranking.get("enemy_breakdown", {})
                serializable_ranking["box_breakdown"] = ranking.get("box_breakdown", {})
                serializable_ranking["pd_drop_breakdown"] = ranking.get("pd_drop_breakdown", {})

            serializable_rankings.append(serializable_ranking)

        return {
            "rankings": serializable_rankings,
            "error": None,
        }

    except Exception as e:
        return {"error": f"Error ranking quests: {e}", "rankings": []}


def optimize_item_hunting(
    drop_table_data: Dict,
    quests_data: List[Dict],
    price_guide_data: Dict[str, Dict],  # Dict mapping filename to JSON data
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Find the best quests for hunting a specific item.

    Args:
        drop_table_data: Drop table JSON data
        quests_data: List of quest dictionaries
        price_guide_data: Dict mapping filename (e.g., 'weapons.json') to JSON data
        params: Form parameters dict with keys:
            - item_name: str (required) - Name of the item to search for
            - rbr_active: bool (default: False) - Enable RBR for all quests
            - rbr_list: Optional[str] - Space-separated quest names to apply RBR to (mutually exclusive with rbr_active)
            - weekly_boost: Optional[str] (e.g., "DAR", "RDR", "RareEnemy", "XP")
            - event_active: Optional[str] (e.g., "Easter", "Halloween", "Christmas", etc.)
            - quest_filter: Optional[List[str]] (list of quest names to filter)
            - exclude_event_quests: bool (default: False)
            - top_n: Optional[int] (limit results, default: 10)
            - show_details: bool (default: False)

    Returns:
        Dict with keys:
            - quest_results: List[Dict] of quest results sorted by drop probability
            - enemy_drops: List[Dict] of enemies that drop the item
            - box_drops: List[Dict] of boxes that drop the item
            - item_type: str (item type: "weapon", "disk", "tool", etc.)
            - error: Optional[str] error message
    """

    # Create temporary directory structure in Pyodide filesystem
    base_path = Path("/tmp/pso_data")
    base_path.mkdir(parents=True, exist_ok=True)

    drop_table_path = base_path / "drop_tables_ultimate.json"
    quests_path = base_path / "quests.json"
    price_guide_dir = base_path / "price_guide" / "data"
    price_guide_dir.mkdir(parents=True, exist_ok=True)

    # Write drop table data
    with open(drop_table_path, "w", encoding="utf-8") as f:
        json.dump(drop_table_data, f)

    # Write quests data
    with open(quests_path, "w", encoding="utf-8") as f:
        json.dump(quests_data, f)

    # Write price guide data files
    for filename, data in price_guide_data.items():
        file_path = price_guide_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    # Initialize calculator
    try:
        calculator = QuestCalculator(
            drop_table_path=drop_table_path,
            price_guide_path=price_guide_dir,
            quest_data_path=quests_path,
        )
    except Exception as e:
        tb = traceback.format_exc()
        return {
            "error": f"Failed to initialize calculator: {e}\n\nTraceback:\n{tb}",
            "quest_results": [],
            "enemy_drops": [],
            "box_drops": [],
            "item_type": None,
        }

    # Parse parameters
    item_name = params.get("item_name")
    if not item_name:
        return {
            "error": "item_name parameter is required",
            "quest_results": [],
            "enemy_drops": [],
            "box_drops": [],
            "item_type": None,
        }

    rbr_active = params.get("rbr_active", False)
    rbr_list = params.get("rbr_list")
    # Convert rbr_list from string to list if it's a string (from form input)
    if isinstance(rbr_list, str):
        rbr_list = [q.strip() for q in rbr_list.split()] if rbr_list.strip() else None
    elif rbr_list is None or (isinstance(rbr_list, list) and len(rbr_list) == 0):
        rbr_list = None

    # Parse weekly boost
    weekly_boost_str = params.get("weekly_boost")
    weekly_boost = None
    if weekly_boost_str:
        try:
            weekly_boost = WeeklyBoost(weekly_boost_str)
        except ValueError:
            return {
                "error": f"Invalid weekly_boost: {weekly_boost_str}",
                "quest_results": [],
                "enemy_drops": [],
                "box_drops": [],
                "item_type": None,
            }

    # Parse event type
    event_active_str = params.get("event_active")
    event_type = None
    if event_active_str:
        try:
            event_type = EventType(event_active_str)
        except ValueError:
            return {
                "error": f"Invalid event_active: {event_active_str}",
                "quest_results": [],
                "enemy_drops": [],
                "box_drops": [],
                "item_type": None,
            }

    quest_filter = params.get("quest_filter")
    exclude_event_quests = params.get("exclude_event_quests", False)
    top_n = params.get("top_n", 10)

    # Filter quests if needed
    if exclude_event_quests:
        calculator.quest_data = [q for q in calculator.quest_data if not calculator._is_event_quest(q)]

    try:
        # Identify item type
        item_type = calculator.price_guide.identify_item_type(item_name)

        # Find enemies that drop the item
        enemy_drops = calculator.find_enemies_that_drop_weapon(item_name, rbr_active=rbr_active, rbr_list=rbr_list, weekly_boost=weekly_boost, event_type=event_type)

        # Find boxes that drop the item
        box_drops = calculator.find_boxes_that_drop_weapon(item_name)

        # Find best quests
        quest_results = calculator.find_best_quests_for_item(
            item_name,
            rbr_active=rbr_active,
            rbr_list=rbr_list,
            weekly_boost=weekly_boost,
            quest_filter=quest_filter,
            event_type=event_type,
        )

        # Limit results if top_n is specified
        if top_n and top_n > 0:
            quest_results = quest_results[:top_n]

        # Convert to JSON-serializable format
        serializable_quest_results = []
        for result in quest_results:
            serializable_result = {
                "quest_name": result.get("quest_name"),
                "long_name": result.get("long_name"),
                "section_id": result.get("section_id"),
                "episode": result.get("episode"),
                "probability": float(result.get("probability", 0.0)),
                "percentage": float(result.get("percentage", 0.0)),
                "contributions": [],
            }

            # Serialize contributions
            for contrib in result.get("contributions", []):
                serializable_contrib = {
                    "source": contrib.get("source"),
                    "probability": float(contrib.get("probability", 0.0)),
                }

                # Add source-specific fields
                if contrib.get("source") == "Box":
                    serializable_contrib["area"] = contrib.get("area")
                    serializable_contrib["box_count"] = contrib.get("box_count", 0)
                    serializable_contrib["drop_rate"] = float(contrib.get("drop_rate", 0.0))
                    serializable_contrib["technique"] = contrib.get("technique", False)
                elif contrib.get("source") == "Technique":
                    serializable_contrib["enemy"] = contrib.get("enemy")
                    serializable_contrib["area"] = contrib.get("area", "Unknown")
                    serializable_contrib["count"] = float(contrib.get("count", 0.0))
                    serializable_contrib["dar"] = float(contrib.get("dar", 0.0))
                    serializable_contrib["adjusted_dar"] = float(contrib.get("adjusted_dar", contrib.get("dar", 0.0)))
                else:  # Enemy (weapon)
                    serializable_contrib["enemy"] = contrib.get("enemy")
                    serializable_contrib["count"] = float(contrib.get("count", 0.0))
                    serializable_contrib["dar"] = float(contrib.get("dar", 0.0))
                    serializable_contrib["rdr"] = float(contrib.get("rdr", 0.0))
                    serializable_contrib["adjusted_dar"] = float(contrib.get("adjusted_dar", contrib.get("dar", 0.0)))
                    serializable_contrib["adjusted_rdr"] = float(contrib.get("adjusted_rdr", contrib.get("rdr", 0.0)))

                serializable_result["contributions"].append(serializable_contrib)

            serializable_quest_results.append(serializable_result)

        # Serialize enemy drops
        serializable_enemy_drops = []
        for enemy in enemy_drops:
            serializable_enemy = {
                "enemy": enemy.get("enemy"),
                "episode": enemy.get("episode"),
                "section_id": enemy.get("section_id"),
                "area": enemy.get("area", "Unknown"),
                "drop_rate": float(enemy.get("drop_rate", 0.0)),
                "drop_rate_percent": float(enemy.get("drop_rate_percent", 0.0)),
                "dar": float(enemy.get("dar", 0.0)),
                "rdr": float(enemy.get("rdr", 0.0)),
                "adjusted_dar": float(enemy.get("adjusted_dar", enemy.get("dar", 0.0))),
            }
            if "adjusted_rdr" in enemy:
                serializable_enemy["adjusted_rdr"] = float(enemy.get("adjusted_rdr", enemy.get("rdr", 0.0)))
            serializable_enemy_drops.append(serializable_enemy)

        # Serialize box drops
        serializable_box_drops = []
        for box in box_drops:
            serializable_box = {
                "area": box.get("area"),
                "episode": box.get("episode"),
                "section_id": box.get("section_id"),
                "drop_rate": float(box.get("drop_rate", 0.0)),
                "drop_rate_percent": float(box.get("drop_rate_percent", 0.0)),
                "box_count": box.get("box_count", 0),
                "technique": box.get("technique", False),
            }
            serializable_box_drops.append(serializable_box)

        return {
            "quest_results": serializable_quest_results,
            "enemy_drops": serializable_enemy_drops,
            "box_drops": serializable_box_drops,
            "item_type": item_type,
            "error": None,
        }

    except Exception as e:
        tb = traceback.format_exc()
        return {
            "error": f"Error finding item drops: {e}\n\nTraceback:\n{tb}",
            "quest_results": [],
            "enemy_drops": [],
            "box_drops": [],
            "item_type": None,
        }


def calculate_item_value(
    price_guide_data: Dict[str, Dict],  # Dict mapping filename to JSON data
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Calculate the expected value of an item.

    Args:
        price_guide_data: Dict mapping filename (e.g., 'weapons.json') to JSON data
        params: Form parameters dict with keys:
            - item_name: str (required) - Name of the item to calculate value for
            - drop_area: Optional[str] (e.g., "Forest 1", "Ruins 3") - Only affects weapons
            - price_strategy: Optional[str] (default: "MINIMUM") - "MINIMUM" or "AVERAGE"

    Returns:
        Dict with keys:
            - item_type: str (item type: "weapon", "frame", "barrier", etc.)
            - value: float (expected value in PD)
            - error: Optional[str] error message
    """

    # Create temporary directory structure in Pyodide filesystem
    base_path = Path("/tmp/pso_data")
    price_guide_dir = base_path / "price_guide" / "data"
    price_guide_dir.mkdir(parents=True, exist_ok=True)

    # Write price guide data files
    for filename, data in price_guide_data.items():
        file_path = price_guide_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    # Parse parameters
    item_name = params.get("item_name")
    if not item_name:
        return {
            "error": "item_name parameter is required",
            "item_type": None,
            "value": None,
        }

    drop_area = params.get("drop_area")
    price_strategy_str = params.get("price_strategy", "MINIMUM")

    # Parse price strategy
    try:
        price_strategy = BasePriceStrategy(price_strategy_str.upper())
    except ValueError:
        return {
            "error": f"Invalid price_strategy: {price_strategy_str}",
            "item_type": None,
            "value": None,
        }

    # Initialize price guide and calculator
    try:
        price_guide = PriceGuideFixed(str(price_guide_dir), base_price_strategy=price_strategy)
        item_value_calculator = ItemValueCalculator(price_guide)
    except Exception as e:
        tb = traceback.format_exc()
        return {
            "error": f"Failed to initialize price guide: {e}\n\nTraceback:\n{tb}",
            "item_type": None,
            "value": None,
        }

    # Calculate item value
    try:
        item_info = calc_item_value(
            item_name,
            price_guide,
            item_value_calculator,
            drop_area,
        )

        if item_info is None:
            return {
                "error": f"Could not find '{item_name}' in any item category",
                "item_type": None,
                "value": None,
                "breakdown": None,
            }

        item_type, item_value = item_info

        # Get detailed breakdown for weapons, frames, and barriers
        breakdown = item_value_calculator.get_calculation_breakdown(item_name, drop_area)

        # Serialize breakdown to JSON-compatible format
        serializable_breakdown = None
        if breakdown:
            if item_type == "weapon":
                serializable_breakdown = {
                    "weapon_name": breakdown.get("weapon_name"),
                    "drop_area": breakdown.get("drop_area"),
                    "total_value": float(breakdown.get("total_value", 0.0)),
                    "hit_contribution": float(breakdown.get("hit_contribution", 0.0)),
                    "attribute_contribution": float(breakdown.get("attribute_contribution", 0.0)),
                    "area_attribute_probs": (
                        {k: float(v) if v is not None else None for k, v in (breakdown.get("area_attribute_probs") or {}).items()}
                        if breakdown.get("area_attribute_probs")
                        else None
                    ),
                    "hit_probability": float(breakdown.get("hit_probability", 0.0)),
                    "three_roll_hit_prob": float(breakdown.get("three_roll_hit_prob", 0.0)),
                    "no_hit_prob": float(breakdown.get("no_hit_prob", 0.0)),
                    "pattern5_probs": {str(k): float(v) for k, v in breakdown.get("pattern5_probs", {}).items()},
                    "hit_breakdown": [
                        {
                            "hit_value": int(item.get("hit_value", 0)),
                            "teched_hit": int(item.get("teched_hit", 0)),
                            "pattern5_prob": (float(item.get("pattern5_prob", 0.0)) if item.get("pattern5_prob") is not None else None),
                            "combined_prob": float(item.get("combined_prob", 0.0)),
                            "price_range": item.get("price_range", "N/A"),
                            "price": float(item.get("price", 0.0)),
                            "expected_value": float(item.get("expected_value", 0.0)),
                        }
                        for item in breakdown.get("hit_breakdown", [])
                    ],
                    "attribute_details": [
                        {
                            "attribute": detail.get("attribute"),
                            "modifier_price_str": detail.get("modifier_price_str"),
                            "modifier_price": float(detail.get("modifier_price", 0.0)),
                            "probability": float(detail.get("probability", 0.0)),
                            "contribution": float(detail.get("contribution", 0.0)),
                        }
                        for detail in breakdown.get("attribute_details", [])
                    ],
                }
            elif item_type == "frame":
                serializable_breakdown = {
                    "frame_name": breakdown.get("frame_name"),
                    "total_value": float(breakdown.get("total_value", 0.0)),
                    "base_price": float(breakdown.get("base_price", 0.0)),
                    "base_price_str": breakdown.get("base_price_str", "0"),
                    "stat_probs": {k: float(v) for k, v in breakdown.get("stat_probs", {}).items()},
                    "tier_details": [
                        {
                            "tier": detail.get("tier"),
                            "stat_key": detail.get("stat_key"),
                            "price_range": str(detail.get("price_range", "N/A")),
                            "price": float(detail.get("price", 0.0)),
                            "probability": float(detail.get("probability", 0.0)),
                            "contribution": float(detail.get("contribution", 0.0)),
                        }
                        for detail in breakdown.get("tier_details", [])
                    ],
                    "stat_tier_contributions": {k: float(v) for k, v in breakdown.get("stat_tier_contributions", {}).items()},
                }
            elif item_type == "barrier":
                serializable_breakdown = {
                    "barrier_name": breakdown.get("barrier_name"),
                    "total_value": float(breakdown.get("total_value", 0.0)),
                    "base_price": float(breakdown.get("base_price", 0.0)),
                    "base_price_str": breakdown.get("base_price_str", "0"),
                    "stat_probs": {k: float(v) for k, v in breakdown.get("stat_probs", {}).items()},
                    "tier_details": [
                        {
                            "tier": detail.get("tier"),
                            "stat_key": detail.get("stat_key"),
                            "price_range": str(detail.get("price_range", "N/A")),
                            "price": float(detail.get("price", 0.0)),
                            "probability": float(detail.get("probability", 0.0)),
                            "contribution": float(detail.get("contribution", 0.0)),
                        }
                        for detail in breakdown.get("tier_details", [])
                    ],
                    "stat_tier_contributions": {k: float(v) for k, v in breakdown.get("stat_tier_contributions", {}).items()},
                }

        return {
            "item_type": item_type,
            "value": float(item_value),
            "breakdown": serializable_breakdown,
            "error": None,
        }

    except Exception as e:
        tb = traceback.format_exc()
        return {
            "error": f"Error calculating item value: {e}\n\nTraceback:\n{tb}",
            "item_type": None,
            "value": None,
            "breakdown": None,
        }
