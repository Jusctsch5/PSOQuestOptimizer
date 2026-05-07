"""Heuristic quest duration from area lists."""

import json
from pathlib import Path

from quest_optimizer.quest_time_estimate import (
    estimate_quest_minutes_heuristic,
    is_boss_area,
    ranking_efficiency_sort_key,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _quest(name: str) -> dict:
    data = json.loads((REPO_ROOT / "quests" / "quests.json").read_text(encoding="utf-8"))
    for q in data:
        if q.get("quest_name") == name:
            return q
    raise KeyError(name)


def test_mu1_single_area_fifteen_minutes():
    q = _quest("MU1")
    assert estimate_quest_minutes_heuristic(q) == 15.0


def test_pw1_two_regular_areas_thirty_minutes():
    q = _quest("PW1")
    assert len(q["areas"]) == 2
    assert estimate_quest_minutes_heuristic(q) == 30.0


def test_boss_area_under_the_dome_five():
    assert is_boss_area("Under the Dome")
    q = {
        "areas": [{"name": "Under the Dome", "enemies": {}, "boxes": {}}],
    }
    assert estimate_quest_minutes_heuristic(q) == 5.0


def test_mixed_alpha_and_final():
    q = {
        "areas": [
            {"name": "VR Temple Alpha"},
            {"name": "VR Temple Beta"},
            {"name": "VR Temple Final"},
        ],
    }
    assert estimate_quest_minutes_heuristic(q) == 15.0 + 15.0 + 5.0


def test_flat_enemies_no_areas_counts_as_one_area():
    q = _quest("DD1")
    assert not q.get("areas")
    assert q.get("enemies")
    assert estimate_quest_minutes_heuristic(q) == 15.0


def test_ranking_efficiency_sort_key_order():
    assert ranking_efficiency_sort_key({"pd_per_minute": 2.0, "pd_per_minute_estimated": 1.0, "total_pd": 10.0}) == 2.0
    assert ranking_efficiency_sort_key({"pd_per_minute": None, "pd_per_minute_estimated": 3.0, "total_pd": 10.0}) == 3.0
    assert ranking_efficiency_sort_key({"pd_per_minute": None, "pd_per_minute_estimated": None, "total_pd": 7.5}) == 7.5
