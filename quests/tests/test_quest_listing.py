"""
Test quest listing functionality.

Tests the QuestListing class for loading quests, area mapping, and box type filtering.
"""

import logging
from pathlib import Path

import pytest

from quests.quest_listing import (
    BOX_TYPE_ARMOR,
    BOX_TYPE_RARELESS,
    BOX_TYPE_REGULAR,
    BOX_TYPE_WEAPON,
    Area,
    QuestListing,
    area_has_enemy_spawns,
    resolve_area_enemies,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Paths to test data
PROJECT_ROOT = Path(__file__).parent.parent.parent
QUEST_DATA_PATH = PROJECT_ROOT / "quests" / "quests.json"


@pytest.fixture
def quest_listing():
    """Create a QuestListing instance for testing"""
    return QuestListing(QUEST_DATA_PATH)


def test_quest_listing_load(quest_listing: QuestListing):
    """Test that quest listing loads correctly"""
    assert quest_listing.quests is not None
    assert len(quest_listing.quests) > 0


def test_get_quest(quest_listing: QuestListing):
    """Test getting quest by name"""
    quest = quest_listing.get_quest("MU1")
    assert quest is not None
    assert quest.get("quest_name") == "MU1"
    assert quest.get("long_name") == "Mop-up Operation 1"

    # Test case-insensitive
    quest2 = quest_listing.get_quest("mu1")
    assert quest2 is not None
    assert quest2.get("quest_name") == "MU1"

    # Test non-existent quest
    quest3 = quest_listing.get_quest("NONEXISTENT")
    assert quest3 is None


def test_get_all_quests(quest_listing: QuestListing):
    """Test getting all quests"""
    all_quests = quest_listing.get_all_quests()
    assert len(all_quests) > 0
    assert all_quests == quest_listing.quests


def test_get_quests_by_episode(quest_listing: QuestListing):
    """Test filtering quests by episode"""
    episode1_quests = quest_listing.get_quests_by_episode(1)
    assert len(episode1_quests) > 0
    for quest in episode1_quests:
        assert quest.get("episode") == 1

    episode2_quests = quest_listing.get_quests_by_episode(2)
    assert len(episode2_quests) > 0
    for quest in episode2_quests:
        assert quest.get("episode") == 2


def test_get_areas_for_quest(quest_listing: QuestListing):
    """Test getting areas for a quest"""
    areas = quest_listing.get_areas_for_quest("MU1")
    assert len(areas) > 0
    assert areas[0].get("name") == "Forest 1"
    assert "boxes" in areas[0]

    # Test non-existent quest
    areas2 = quest_listing.get_areas_for_quest("NONEXISTENT")
    assert len(areas2) == 0


def test_get_boxes_for_area(quest_listing: QuestListing):
    """Test getting box counts for an area"""
    boxes = quest_listing.get_boxes_for_area("MU1", "Forest 1")
    assert "box" in boxes
    assert boxes["box"] == 44
    assert "box_rareless" in boxes
    assert boxes["box_rareless"] == 5

    # Test non-existent area
    boxes2 = quest_listing.get_boxes_for_area("MU1", "NONEXISTENT")
    assert len(boxes2) == 0


def test_area_mapping_simple(quest_listing: QuestListing):
    """Test that unmapped areas return original name"""
    mapped = quest_listing.map_quest_area_to_drop_table_area("Forest 1")
    assert mapped == "Forest 1"

    mapped2 = quest_listing.map_quest_area_to_drop_table_area("Cave 2")
    assert mapped2 == "Cave 2"


def test_area_mapping_boss_areas(quest_listing: QuestListing):
    """Test area mapping: Under the Dome -> Cave 1"""
    mapped = quest_listing.map_quest_area_to_drop_table_area("Under the Dome")
    assert mapped == "Cave 1"

    # Test case-insensitive
    mapped2 = quest_listing.map_quest_area_to_drop_table_area("under the dome")
    assert mapped2 == "Cave 1"

    mapped = quest_listing.map_quest_area_to_drop_table_area("Underground Channel")
    assert mapped == "Mine 1"

    mapped = quest_listing.map_quest_area_to_drop_table_area("Monitor Room")
    assert mapped == "Ruins 1"

    mapped = quest_listing.map_quest_area_to_drop_table_area("????")
    assert mapped == "Ruins 3"

    mapped = quest_listing.map_quest_area_to_drop_table_area("VR Temple Final")
    assert mapped == "VR Spaceship Alpha"

    mapped = quest_listing.map_quest_area_to_drop_table_area("Control Tower")
    assert mapped == "Central Control Area"


def test_area_mapping_all_areas(quest_listing: QuestListing):
    """Test area mapping for all areas"""
    for area in Area:
        assert quest_listing.map_quest_area_to_drop_table_area(area.value) is not None


def test_is_rare_dropping_box(quest_listing: QuestListing):
    """Test box type filtering - only regular boxes can drop rares"""
    assert quest_listing.is_rare_dropping_box(BOX_TYPE_REGULAR) is True
    assert quest_listing.is_rare_dropping_box(BOX_TYPE_ARMOR) is False
    assert quest_listing.is_rare_dropping_box(BOX_TYPE_WEAPON) is False
    assert quest_listing.is_rare_dropping_box(BOX_TYPE_RARELESS) is False
    assert quest_listing.is_rare_dropping_box("unknown") is False


def test_get_rare_dropping_box_count(quest_listing: QuestListing):
    """Test getting count of rare-dropping boxes"""
    # MU1 has 44 regular boxes and 5 box_rareless
    count = quest_listing.get_rare_dropping_box_count("MU1", "Forest 1")
    assert count == 44

    # MU3 has 39 regular boxes, 6 box_armor, 7 box_weapon
    count2 = quest_listing.get_rare_dropping_box_count("MU3", "Mine 1")
    assert count2 == 39

    # Test non-existent area
    count3 = quest_listing.get_rare_dropping_box_count("MU1", "NONEXISTENT")
    assert count3 == 0


def test_resolve_area_enemies_fixed_only():
    area = {"enemies": {"Booma": 10, "Gobooma": 5}}
    assert resolve_area_enemies(area) == {"Booma": 10.0, "Gobooma": 5.0}


def test_resolve_area_enemies_random_spawns():
    area = {
        "enemies": {"Monest": 1},
        "average_random_enemies": 100,
        "random_enemies": {
            "Booma": 50,
            "Gobooma": 50,
        },
    }
    enemies = resolve_area_enemies(area)
    assert enemies["Monest"] == pytest.approx(1.0)
    assert enemies["Booma"] == pytest.approx(50.0)
    assert enemies["Gobooma"] == pytest.approx(50.0)


def test_resolve_area_enemies_normalizes_random_weights():
    area = {
        "average_random_enemies": 104,
        "random_enemies": {
            "Dimenian": 17,
            "La Dimenian": 18,
            "So Dimenian": 19,
        },
    }
    weight_sum = 17 + 18 + 19
    enemies = resolve_area_enemies(area)
    assert enemies["Dimenian"] == pytest.approx(104 * 17 / weight_sum)
    assert sum(enemies.values()) == pytest.approx(104.0)


def test_area_has_enemy_spawns():
    assert area_has_enemy_spawns({"enemies": {"Booma": 1}}) is True
    assert area_has_enemy_spawns({"random_enemies": {"Booma": 100}}) is True
    assert area_has_enemy_spawns({"boxes": {"box": 10}}) is False


def test_ao1_ruins_2_random_spawns(quest_listing: QuestListing):
    quest = quest_listing.get_quest("AO1")
    assert quest is not None
    ruins = next(area for area in quest["areas"] if area["name"] == "Ruins 2")
    enemies = resolve_area_enemies(ruins)

    fixed_total = sum(ruins["enemies"].values())
    weight_sum = sum(ruins["random_enemies"].values())
    assert sum(enemies.values()) == pytest.approx(fixed_total + ruins["average_random_enemies"])
    assert enemies["Delsaber"] == pytest.approx(2 + 163 * 11 / weight_sum)
    assert enemies["Chaos Bringer"] == pytest.approx(1 + 163 * 8 / weight_sum)


# Random spawn pools whose weights sum to something other than 100.
RANDOM_ENEMY_WEIGHT_TOTALS: dict[tuple[str, str], int] = {
    ("AO4", "Seabed Lower"): 92,
}


def test_random_enemy_weights_valid(quest_listing: QuestListing):
    """random_enemies weights must be positive and sum to 100 (or a known alternate total)."""
    failures = []
    for quest in quest_listing.get_all_quests():
        quest_name = quest.get("quest_name", "?")
        for area in quest.get("areas", []):
            random_enemies = area.get("random_enemies")
            if not random_enemies:
                continue
            area_name = area.get("name", "?")
            if any(weight <= 0 for weight in random_enemies.values()):
                failures.append(f"{quest_name} / {area_name}: all weights must be positive")
                continue
            total = sum(random_enemies.values())
            expected_total = RANDOM_ENEMY_WEIGHT_TOTALS.get((quest_name, area_name), 100)
            if total != expected_total:
                failures.append(
                    f"{quest_name} / {area_name}: weights sum to {total}, expected {expected_total}"
                )

    assert not failures, "invalid random_enemies weights:\n" + "\n".join(failures)


def _weighted(counts: tuple[float, ...], probs: tuple[float, ...]) -> float:
    return sum(count * prob for count, prob in zip(counts, probs))


def test_xrd1_route_expected_counts(quest_listing: QuestListing):
    """Random Attack Xrd Stage (E1) counts are appearance-weighted.

    One path per run. Cave base is always cleared. Green (50%) continues through
    Ruins 3 base plus one ruins color, then Dark Falz (75%) or Spaceship and
    De Rol Le (25%). Red (50%) continues through Yellow or Blue, then Mine 1
    base plus one mine color. Mine Green splits Vol Opt / Palace then Dragon;
    Mine Red is Vol Opt. Counts use the wiki appearance table, which matches
    the published per-run enemy ranges.
    """
    quest = quest_listing.get_quest("XRD1")
    assert quest is not None
    assert quest["long_name"] == "Random Attack Xrd Stage (E1)"
    assert quest["episode"] == 1
    areas = {area["name"]: area for area in quest["areas"]}

    cave_probs = (1.0, 0.5, 0.5, 0.25, 0.25)
    half_probs = (0.5, 0.25, 0.25)
    rare = 0.125

    cave = areas["Cave 1"]["enemies"]
    assert cave["Evil Shark"] == pytest.approx(_weighted((3, 11, 3, 3, 4), cave_probs))
    assert cave["Pal Shark"] == pytest.approx(_weighted((8, 4, 4, 8, 6), cave_probs))
    assert cave["Guil Shark"] == pytest.approx(_weighted((2, 4, 7, 10, 4), cave_probs))
    assert cave["Poison Lily"] == pytest.approx(_weighted((8, 2, 16, 11, 8), cave_probs))
    assert cave["Grass Assassin"] == pytest.approx(_weighted((6, 2, 9, 4, 2), cave_probs))
    assert cave["Nano Dragon"] == pytest.approx(_weighted((7, 2, 3, 3, 2), cave_probs))
    assert cave["Pan Arms"] == pytest.approx(_weighted((0, 2, 5, 4, 1), cave_probs))

    mine = areas["Mine 1"]["enemies"]
    assert mine["Gillchic"] == pytest.approx(_weighted((17, 7, 20), half_probs))
    assert mine["Dubchic"] == pytest.approx(_weighted((14, 8, 17), half_probs))
    assert mine["Dubwitch"] == pytest.approx(_weighted((2, 2, 0), half_probs))
    assert mine["Canadine"] == pytest.approx(_weighted((12, 16, 54), half_probs))
    assert mine["Canane"] == pytest.approx(_weighted((1, 2, 6), half_probs))
    assert mine["Sinow Beat"] == pytest.approx(_weighted((6, 6, 3), half_probs))
    assert mine["Sinow Gold"] == pytest.approx(_weighted((3, 22, 2), half_probs))
    assert mine["Garanz"] == pytest.approx(_weighted((1, 16, 5), half_probs))

    ruins = areas["Ruins 3"]["enemies"]
    assert ruins["Dimenian"] == pytest.approx(_weighted((12, 20, 3), half_probs))
    assert ruins["La Dimenian"] == pytest.approx(_weighted((9, 14, 2), half_probs))
    assert ruins["So Dimenian"] == pytest.approx(_weighted((11, 6, 11), half_probs))
    assert ruins["Claw"] == pytest.approx(_weighted((8, 0, 0), half_probs))
    assert ruins["Bulclaw"] == pytest.approx(_weighted((9, 3, 2), half_probs))
    assert ruins["Dark Belra"] == pytest.approx(_weighted((12, 7, 3), half_probs))
    assert ruins["Dark Gunner"] == pytest.approx(_weighted((10, 5, 0), half_probs))
    assert ruins["Chaos Sorcerer"] == pytest.approx(_weighted((8, 6, 0), half_probs))
    assert ruins["Chaos Bringer"] == pytest.approx(_weighted((8, 1, 3), half_probs))

    palace = areas["Palace"]["enemies"]
    assert palace["Hildebear"] == pytest.approx(8 * rare)
    assert palace["Grass Assassin"] == pytest.approx(6 * rare)
    assert palace["Sinow Beat"] == pytest.approx(12 * rare)
    assert palace["Sinow Gold"] == pytest.approx(16 * rare)
    assert palace["Delsaber"] == pytest.approx(8 * rare)
    assert palace["Chaos Bringer"] == pytest.approx(30 * rare)

    spaceship = areas["Spaceship"]["enemies"]
    assert spaceship["Hildebear"] == pytest.approx(9 * rare)
    assert spaceship["Guil Shark"] == pytest.approx(6 * rare)
    assert spaceship["Grass Assassin"] == pytest.approx(52 * rare)
    assert spaceship["Sinow Beat"] == pytest.approx(9 * rare)
    assert spaceship["Delsaber"] == pytest.approx(13 * rare)
    assert spaceship["Chaos Bringer"] == pytest.approx(7 * rare)

    assert areas["Under the Dome"]["enemies"]["Dragon"] == pytest.approx(rare)
    assert areas["Underground Channel"]["enemies"]["De Rol Le"] == pytest.approx(rare)
    assert areas["Monitor Room"]["enemies"]["Vol Opt"] == pytest.approx(0.375)
    assert areas["????"]["enemies"]["Dark Falz"] == pytest.approx(0.375)

    assert areas["Underground Channel"]["boxes"]["box"] == pytest.approx(4 * rare)
    assert areas["Under the Dome"]["boxes"]["box_weapon"] == pytest.approx(8 * rare)
    assert areas["Monitor Room"]["boxes"]["box_tool"] == pytest.approx(7 * 0.375)
    assert areas["????"]["boxes"]["box_armor"] == pytest.approx(5 * 0.375)

    material_chance = (rare + rare) / 6
    for material in (
        "Mind Material",
        "Evade Material",
        "HP Material",
        "TP Material",
        "Def Material",
        "Luck Material",
    ):
        assert quest["quest_completion_items"][material] == pytest.approx(material_chance)


def test_ao4_seabed_lower_random_spawns(quest_listing: QuestListing):
    """AO4 Seabed Lower uses a 92-denominator random pool (not percents)."""
    quest = quest_listing.get_quest("AO4")
    assert quest is not None
    area = next(a for a in quest["areas"] if a["name"] == "Seabed Lower")
    assert sum(area["random_enemies"].values()) == 92

    enemies = resolve_area_enemies(area)
    avg = area["average_random_enemies"]
    assert enemies["Dolmolm"] == pytest.approx(avg * 28 / 92)
    assert enemies["Delbiter"] == pytest.approx(avg * 7 / 92)
    assert enemies["Morfos"] == pytest.approx(4 + avg * 9 / 92)
