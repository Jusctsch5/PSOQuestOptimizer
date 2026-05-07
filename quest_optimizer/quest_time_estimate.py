"""
Heuristic quest duration from area list (for PD/min when no quest_times.json entry).

Default: 15 minutes per regular area, 5 minutes per boss arena (Ephinea area names from
``quests.quest_listing.Area`` where the quest uses the boss-stage name).
"""

from __future__ import annotations

from typing import Any, Dict

from quests.quest_listing import Area

# Boss / finale stages (matches Area enum — quest ``areas[].name`` in quests.json)
_BOSS_AREA_NAMES = frozenset(
    (
        Area.UNDER_THE_DOME.value,
        Area.UNDERGROUND_CHANNEL.value,
        Area.MONITOR_ROOM.value,
        Area.QUESTION_MARKS.value,
        Area.VR_TEMPLE_FINAL.value,
        Area.VR_SPACESHIP_FINAL.value,
        Area.CLIFFS_OF_GAL_DA_VAL.value,
        Area.TEST_SUBJECT_DISPOSAL_AREA.value,
        Area.METEOR_IMPACT_SITE.value,
    )
)

_cf_boss = {name.casefold() for name in _BOSS_AREA_NAMES}


def is_boss_area(area_name: str) -> bool:
    """True if ``area_name`` matches a known boss-stage area (case-insensitive)."""
    n = area_name.strip()
    if not n:
        return False
    return n.casefold() in _cf_boss


def estimate_quest_minutes_heuristic(
    quest_data: Dict[str, Any],
    *,
    minutes_per_area: float = 15.0,
    minutes_per_boss_area: float = 5.0,
) -> float:
    """
    Sum time per quest area: boss arenas ``minutes_per_boss_area``, else ``minutes_per_area``.

    Returns 0.0 if there are no named areas.
    """
    areas = quest_data.get("areas") or []
    if not areas:
        # Same as QuestCalculator: flat ``enemies`` on the quest without ``areas``
        if quest_data.get("enemies"):
            return float(minutes_per_area)
        return 0.0
    total = 0.0
    for block in areas:
        name = str(block.get("name", "")).strip()
        if not name:
            continue
        if is_boss_area(name):
            total += float(minutes_per_boss_area)
        else:
            total += float(minutes_per_area)
    return float(total)


def ranking_efficiency_sort_key(result: Dict[str, Any]) -> float:
    """Sort quests: explicit ``pd_per_minute`` first, else heuristic, else ``total_pd``."""
    pm = result.get("pd_per_minute")
    if pm is not None:
        return float(pm)
    pme = result.get("pd_per_minute_estimated")
    if pme is not None:
        return float(pme)
    return float(result.get("total_pd", 0.0))
