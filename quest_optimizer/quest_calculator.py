"""
Quest value calculator for RBR quests.

Calculates expected PD value per quest by:
1. Cross-referencing quest enemy counts with drop tables
2. Applying RBR and weekly boost multipliers
3. Looking up item values from price guide
4. Calculating total expected PD value
"""

import json
from bisect import bisect
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from drop_tables.weapon_patterns import (
    PATTERN_ATTRIBUTE_PROBABILITIES,
    calculate_rare_weapon_attributes,
    get_three_roll_hit_probability,
)
from price_guide import (
    PriceGuideExceptionItemNameNotFound,
    PriceGuideFixed,
)
from price_guide.armor_value_calculator import ArmorValueCalculator
from quests.quest_listing import QuestListing


class WeeklyBoost(Enum):
    DAR = "DAR"  # Drop Anything Rate
    RDR = "RDR"  # Rare Drop Rate
    RareEnemy = "RareEnemy"  # Rare Enemy Appearance Rate
    XP = "XP"  # Experience Rate


class EventType(Enum):
    """Event types in Ephinea PSO server."""

    Easter = "Easter"
    Halloween = "Halloween"
    Christmas = "Christmas"
    ValentinesDay = "ValentinesDay"
    Anniversary = "Anniversary"


class SectionIds(Enum):
    Viridia = "Viridia"
    Greenill = "Greenill"
    Skyly = "Skyly"
    Bluefull = "Bluefull"
    Purplenum = "Purplenum"
    Pinkal = "Pinkal"
    Redria = "Redria"
    Oran = "Oran"
    Yellowboze = "Yellowboze"
    Whitill = "Whitill"


WEEKLY_DAR_BOOST = 0.25  # +25% Drop Anything Rate
WEEKLY_RDR_BOOST = 0.25  # +25% Rare Drop Rate
WEEKLY_ENEMY_RATE_BOOST = 0.50  # +50% to rare enemy drop rate

HOLLOWEEN_QUEST_DAR_BOOST = 0.50  # +50% Drop Anything Rate
HOLLOWEEN_QUEST_EXPERIENCE_BOOST = 2.00  # +200% Experience Rate
HOLLOWEEN_QUEST_RDR_BOOST = 0.50  # +50% Rare Drop Rate
HOLLOWEEN_QUEST_RARE_ENEMY_BOOST = 1.00  # +100% Rare Enemy Appearance Rate
HOLLOWEEN_QUEST_COOKIE_BOOST = 0.20  # +20% Halloween Cookie drop rate


RBR_DAR_BOOST = 0.25  # +25% Drop Anything Rate
RBR_RDR_BOOST = 0.25  # +25% Rare Drop Rate
RBR_ENEMY_RATE_BOOST = 0.50  # +50% to rare enemy drop rate

BASE_PD_DROP_RATE = 1.0 / 375.0  # 1/375 chance for PD drop
BASE_RARE_ENEMY_RATE = 1.0 / 512  # 1/512 base chance for rare enemy spawn
RARE_ENEMY_RATE_KONDRIEU = 1.0 / 10  # 1/10 chance for rare enemy spawn as Kondrieu

# Event drop rates
CHRISTMAS_PRESENT_DROP_RATE = 1.0 / 2250.0  # 1/2250 chance for Christmas Present
HALLOWEEN_COOKIE_DROP_RATE = 1.0 / 1500.0  # 1/1500 base chance for Halloween Cookie
HALLOWEEN_QUEST_COOKIE_MULTIPLIER = 1.2  # +20% cookie drop rate in Halloween quests during Halloween event
EASTER_EGG_DROP_RATE = 1.0 / 500.0  # 1/500 chance for Easter Egg

# Music disk drop rate (must fail for technique to drop)
MUSIC_DISK_DROP_RATE = 1.0 / 600.0  # 1/600 chance for music disk

# Level 30 technique drop constants
TECHNIQUE_DISK_RATE = 0.1  # 10% chance Tool is a Technique Disk
SPECIFIC_TECHNIQUE_RATE = 0.001  # 0.1% chance for specific technique on eligible floor
LEVEL_30_RATE = 0.1  # 10% chance technique is level 30
TOOL_DROP_RATE = 1.0 / 3.0  # 1/3 chance for Tool (vs Meseta or set drop)

# Level 30 technique areas mapping
LEVEL_30_TECHNIQUE_AREAS = {
    "Foie": ["Ruins 2", "VR Temple Alpha"],
    "Barta": ["Mine 1", "VR Spaceship Beta", "Crater West"],
    "Zonde": ["Mine 2", "Mountain Area", "Crater Interior"],
    "Gifoie": ["Ruins 1", "VR Temple Beta"],
    "Gibarta": ["Cave 3", "Jungle Area (North)", "Crater South"],
    "Gizonde": ["Ruins 1", "Seaside Area", "Central Control Area", "Desert 1"],
    "Rafoie": ["Mine 2", "VR Spaceship Alpha", "Crater East"],
    "Rabarta": ["Mine 1", "Jungle Area (East)", "Crater North"],
    "Razonde": ["Ruins 2", "Seabed Upper Levels", "Desert 2"],
    "Grants": ["Ruins 3", "Seabed Lower Levels", "Control Tower", "Desert 3"],
    "Megid": ["Seabed Lower Levels", "Control Tower", "Desert 3"],
}

# Slime splitting technique
SLIME_SPLIT = True  # Enable slime splitting (each slime counts as 8)
SLIME_SPLIT_MULTIPLIER = 8  # Each slime can be split into 8 slimes

# Map of normal enemies to their rare variants (Ultimate only)
EP1_RARE_ENEMY_MAPPING = {
    "El Rappy": "Pal Rappy",
    "Hildelt": "Hildetorr",
    "Ob Lily": "Mil Lily",
    "Pofuilly Slime": "Pouilly Slime",
}

EP2_RARE_ENEMY_MAPPING = {
    "El Rappy": "Love Rappy",
    "Ob Lily": "Mil Lily",
    "Hildelt": "Hildetorr",
}

EP4_RARE_ENEMY_MAPPING = {
    "Sand Rappy": "Del Rappy",
    "Dorphon": "Dorphon Eclair",
    "Zu": "Pazuzu",
    "Merissa A": "Merissa AA",
    "Saint-Milion": "Kondrieu",
    "Shambertin": "Kondrieu",
}


class DropTableNotFoundError(Exception):
    """Exception raised when a box drop area is not found in the drop table."""

    pass


class QuestCalculator:
    """Calculate quest values based on drop tables and price guide."""

    def __init__(self, drop_table_path: Path, price_guide_path: Path, quest_data_path: Path):
        """
        Initialize calculator with drop table and price guide paths.

        Args:
            drop_table_path: Path to drop_tables_ultimate.json
            price_guide_path: Path to price guide directory
            quest_data_path: Path to quests.json file
        """
        self.price_guide = PriceGuideFixed(str(price_guide_path))
        self.drop_data = self._load_drop_table(drop_table_path)
        self.quest_listing = QuestListing(quest_data_path)
        self.quest_data = self.quest_listing.get_all_quests()
        self.armor_calculator = ArmorValueCalculator(self.price_guide)

    def _get_rare_enemy_mapping(self, episode: int) -> Dict[str, str]:
        """Return episode-specific rare enemy mapping."""
        if episode == 1:
            return EP1_RARE_ENEMY_MAPPING
        if episode == 2:
            return EP2_RARE_ENEMY_MAPPING
        if episode == 4:
            return EP4_RARE_ENEMY_MAPPING
        return {}

    def _load_drop_table(self, drop_table_path: Path) -> Dict:
        """Load drop table JSON file."""
        with open(drop_table_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _is_hallow_quest(self, quest_data: Dict) -> bool:
        """
        Check if a quest is a Hallow quest (uses Halloween boosts instead of weekly boosts).

        Args:
            quest_data: Quest data dictionary with quest_name and/or long_name

        Returns:
            True if quest is a Hallow quest
        """
        quest_name = quest_data.get("quest_name", "").upper()
        long_name = quest_data.get("long_name", "").upper()
        return "HALLOW" in quest_name or "HALLOW" in long_name

    def _is_in_rbr_rotation(self, quest_data: Dict) -> bool:
        """
        Check if a quest is in the RBR rotation (RBR boosts apply).

        Args:
            quest_data: Quest data dictionary with optional in_rbr_rotation field

        Returns:
            True if quest is in RBR rotation (defaults to False if field not present)
        """
        # Default to False - quests must be explicitly marked as in rotation
        # Note: The field name in quests.json is "is_in_rbr_rotation", not "in_rbr_rotation"
        return quest_data.get("is_in_rbr_rotation", False)

    def _is_event_quest(self, quest_data: Dict) -> bool:
        """
        Check if a quest is an event quest. Callers may want to filter out event quests.

        Args:
            quest_data: Quest data dictionary with optional is_event_quest field

        Returns:
            True if quest is an event quest (defaults to False if field not present)
        """
        # Default to False - quests must be explicitly marked as event quests
        return quest_data.get("is_event_quest", False)

    def _get_weapon_expected_value(
        self,
        item_name: str,
        drop_area: Optional[str] = None,
        weapon_data: Optional[Dict] = None,
    ) -> float:
        """
        Calculate expected weapon value based on pattern probabilities.

        For rare weapons: Always uses Pattern 5 for all attributes.
        For common weapons: Uses area-specific patterns.

        Args:
            item_name: Name of the weapon
            drop_area: Area where weapon drops (for common weapons)
            weapon_data: Optional weapon data (if not provided, will fetch it)

        Returns:
            Expected PD value
        """
        # Fetch weapon data if not provided
        if weapon_data is None:
            weapon_data = self.price_guide.get_weapon_data(item_name)

        is_rare = True  # TODO: support common items

        # Get base price
        base_price_str = weapon_data.get("base")
        base_price = 0.0
        if base_price_str and base_price_str is not None:
            try:
                base_price = PriceGuideFixed.get_price_from_range(base_price_str, self.price_guide.bps)
            except Exception:
                pass

        # For rare weapons, always use Pattern 5
        if is_rare:
            return self._calculate_rare_weapon_value(weapon_data, base_price, drop_area=drop_area)
        else:
            # For common weapons, use area-specific patterns
            return self._calculate_common_weapon_value(weapon_data, base_price, drop_area=drop_area)

    def _calculate_rare_weapon_value(self, weapon_data: Dict, base_price: float, drop_area: Optional[str] = None) -> float:
        """Calculate expected value for rare weapon using Pattern 5."""

        total_value = base_price

        # Get Pattern 5 contributions (probabilities, not prices)
        # Note: For rare weapons, we use calculate_rare_weapon_attributes which doesn't need drop_area
        # But we still need drop_area for hit probability calculation
        attr_results = calculate_rare_weapon_attributes(weapon_data)

        # Multiply by prices to get actual PD values
        modifiers = weapon_data.get("modifiers", {})
        attr_to_modifier = {
            "native": "N",
            "abeast": "AB",
            "machine": "M",
            "dark": "D",
        }

        # Calculate attribute contributions (multiply Pattern 5 prob by modifier price)
        for attr_name, mod_key in attr_to_modifier.items():
            if mod_key in modifiers and attr_name in attr_results:
                try:
                    modifier_price = PriceGuideFixed.get_price_from_range(modifiers[mod_key], self.price_guide.bps)
                    total_value += attr_results[attr_name] * modifier_price
                except Exception:
                    pass

        # Calculate hit contribution (matching WeaponValueCalculator approach)
        hit_values = weapon_data.get("hit_values", {})
        if hit_values and "hit" in attr_results:
            # Get three-roll hit probability
            three_roll_hit_prob = get_three_roll_hit_probability(drop_area)
            no_hit_prob = 1.0 - three_roll_hit_prob

            sorted_hits = sorted(map(int, hit_values.keys()))

            # No-hit contribution (if a 0-hit price exists)
            if "0" in hit_values:
                try:
                    no_hit_price = PriceGuideFixed.get_price_from_range(hit_values["0"], self.price_guide.bps)
                    total_value += no_hit_price * no_hit_prob
                except Exception:
                    pass

            # Hit contribution: iterate through Pattern 5 hit values
            for hit_val, pattern5_prob in PATTERN_ATTRIBUTE_PROBABILITIES[5].items():
                # Combined probability = (three-roll hit prob) * (Pattern 5 prob for this hit value)
                combined_prob = three_roll_hit_prob * pattern5_prob

                # Tech the hit value: add 10 to the original hit value
                teched_hit = hit_val + 10

                # Find the price threshold for the teched hit value
                index = bisect(sorted_hits, teched_hit) - 1
                if index >= 0:
                    threshold = sorted_hits[index]
                    price_range = hit_values[str(threshold)]
                    try:
                        hit_price = PriceGuideFixed.get_price_from_range(price_range, self.price_guide.bps)
                        total_value += hit_price * combined_prob
                    except Exception:
                        pass

        return total_value

    def _calculate_common_weapon_value(self, weapon_data: Dict, base_price: float, drop_area: Optional[str] = None) -> float:
        """Calculate expected value for common weapon using area-specific patterns."""
        # TODO: Implement common weapon pattern calculation
        # For now, return base price
        return base_price

    def _get_armor_expected_value(self, item_name: str) -> float:
        """
        Calculate expected armor (frame) value based on DEF stat probabilities.

        Args:
            item_name: Name of the frame

        Returns:
            Expected PD value
        """
        return self.armor_calculator.calculate_frame_expected_value(item_name)

    def _get_shield_expected_value(self, item_name: str) -> float:
        """
        Calculate expected shield (barrier) value based on EVP stat probabilities.

        Args:
            item_name: Name of the barrier

        Returns:
            Expected PD value
        """
        return self.armor_calculator.calculate_barrier_expected_value(item_name)

    def _get_item_price_pd(self, item_name: str, drop_area: Optional[str] = None) -> float:
        """
        Get price for an item by searching all price categories.
        For weapons, calculates expected value based on patterns.
        Returns price in PD (price guide already returns PD values).

        Raises:
            PriceGuideExceptionItemNameNotFound: If item is not found in any price category
        """
        # Weapons - use pattern-based calculation
        try:
            return self._get_weapon_expected_value(item_name, drop_area)
        except PriceGuideExceptionItemNameNotFound:
            pass  # Not a weapon, continue to check other item types

        # Units
        try:
            return self.price_guide.get_price_unit(item_name)
        except PriceGuideExceptionItemNameNotFound:
            pass

        # Cells (mag cells / special items)
        try:
            return self.price_guide.get_price_cell(item_name)
        except PriceGuideExceptionItemNameNotFound:
            pass

        # Tools
        try:
            return self.price_guide.get_price_tool(item_name, 1)
        except PriceGuideExceptionItemNameNotFound:
            pass

        # Frames (armor) - use expected value calculation
        try:
            return self._get_armor_expected_value(item_name)
        except PriceGuideExceptionItemNameNotFound:
            pass

        # Barriers (shields) - use expected value calculation
        try:
            return self._get_shield_expected_value(item_name)
        except PriceGuideExceptionItemNameNotFound:
            pass

        # Mags (need level, default to 0)
        try:
            return self.price_guide.get_price_mag(item_name, 0)
        except PriceGuideExceptionItemNameNotFound:
            pass

        # Disks (default to level 30)
        try:
            return self.price_guide.get_price_disk(item_name, 30)
        except PriceGuideExceptionItemNameNotFound:
            pass

        # S-Rank weapons (need more info)
        # Skip for now as they require ability, grinder, element

        # Item not found in any category
        raise PriceGuideExceptionItemNameNotFound(f"Item name {item_name} not found in any price category")

    # Mapping from names used in Ultimate to base names
    ENEMY_NAME_MAPPING = {
        # Episode 1 - Forest
        "Bartle": "Booma",
        "Barble": "Gobooma",
        "Tollaw": "Gigobooma",
        "Gulgus": "Savage Wolf",
        "Gulgus-Gue": "Barbarous Wolf",
        "Hildelt": "Hildebear",
        "Hildetorr": "Hildeblue",
        "El Rappy": "Rag Rappy",
        "Pal Rappy": "Al Rappy",
        "Mothvist": "Mothmant",
        "Sil Dragon": "Dragon",
        # Episode 1 - Caves
        "Vulmer": "Evil Shark",
        "Govulmer": "Pal Shark",
        "Melqueek": "Guil Shark",
        "Ob Lily": "Poison Lily",
        "Mil Lily": "Nar Lily",
        "Pofuilly Slime": "Pofuilly Slime",
        "Pouilly Slime": "Pouilly Slime",
        "Nano Dragon": "Nano Dragon",
        "Pan Arms": "Pan Arms",
        "Crimson Assassin": "Grass Assassin",
        "Dal Ra Lie": "De Rol Le",
        # Episode 1 - Mines
        "Dubchich": "Dubchic",
        "Gillchich": "Gillchic",
        "Duvuik": "Dubwitch",
        "Canabin": "Canadine",
        "Canune": "Canane",
        "Sinow Red": "Sinow Gold",
        "Sinow Blue": "Sinow Beat",
        "Baranz": "Garanz",
        # Episode 1 - Ruins
        "Arlan": "Dimenian",
        "Merlan": "La Dimenian",
        "Del-D": "So Dimenian",
        "Bulclaw": "Bulclaw",
        "Claw": "Claw",
        "Dark Gunner": "Dark Gunner",
        "Delsaber": "Delsaber",
        "Gran Sorcerer": "Chaos Sorcerer",
        "Indi Belra": "Dark Belra",
        "Dark Bringer": "Chaos Bringer",
        "Dark Falz": "Dark Falz",
        # Episode 2 - All of the names are the same.
        # Some EP1 enemies are present in EP2.
        # We use the names above.
        "Meriltas": "Meriltas",
        "Merillia": "Merillia",
        "Zol Gibbon": "Zol Gibbon",
        "Ul Gibbon": "Ul Gibbon",
        "Sinow Spigell": "Sinow Spigell",
        "Sinow Berill": "Sinow Berill",
        "Merikle": "Merikle",
        "Mericus": "Mericus",
        "Mericarol": "Mericarol",
        "Dolmdarl": "Dolmdarl",
        "Dolmolm": "Dolmolm",
        "Recon": "Recon",
        "Recobox": "Recobox",
        "Sinow Zele": "Sinow Zele",
        "Sinow Zoa": "Sinow Zoa",
        "Delbiter": "Delbiter",
        "Del Lily": "Del Lily",
        "Ill Gill": "Ill Gill",
        "Epsilon": "Epsilon",
        "Barba Ray": "Barba Ray",
        "Gol Dragon": "Gol Dragon",
        "Gal Gryphon": "Gal Gryphon",
        "Olga Flow": "Olga Flow",
        # Episode 4 - All of the names are the same.
        "Boota": "Boota",
        "Ze Boota": "Ze Boota",
        "Ba Boota": "Ba Boota",
        "Satellite Lizard": "Satellite Lizard",
        "Yowie": "Yowie",
        "Sand Rappy": "Sand Rappy",
        "Zu": "Zu",
        "Pazuzu": "Pazuzu",
        "Astark": "Astark",
        "Dorphon": "Dorphon",
        "Goran": "Goran",
        "Pyro Goran": "Pyro Goran",
        "Goran Detonator": "Goran Detonator",
        "Merissa A": "Merissa A",
        "Girtablulu": "Girtablulu",
    }

    ENEMIES_WITHOUT_DROPS = ["Dubwitch", "Duvuik", "Monest", "Mothvist", "Recobox"]

    def _determine_drop_area(self, enemy_name: str, episode: int) -> str:
        """
        Determine drop area from enemy name and episode.
        Returns a default area for the episode if specific area can't be determined.
        """
        enemy_lower = enemy_name.lower()
        normalized = self._normalize_enemy_name(enemy_name).lower()

        # Episode 1 areas
        if episode == 1:
            # Forest enemies
            forest_enemies = [
                "booma",
                "gobooma",
                "gigobooma",
                "savage wolf",
                "barbarous wolf",
                "rag rappy",
                "al rappy",
                "hildebear",
                "mothmant",
            ]
            if normalized in forest_enemies or any(fe in enemy_lower for fe in forest_enemies):
                return "Forest 1"

            # Cave enemies
            cave_enemies = [
                "evil shark",
                "pal shark",
                "guil shark",
                "poison lily",
                "nar lily",
                "pofuilly slime",
                "grass assassin",
                "nano dragon",
                "pan arms",
            ]
            if normalized in cave_enemies or any(ce in enemy_lower for ce in cave_enemies):
                return "Cave 1"

            # Mine enemies
            mine_enemies = ["gillchich", "canabin", "sinow blue", "garanz"]
            if normalized in mine_enemies or any(me in enemy_lower for me in mine_enemies):
                return "Mine 1"

            # Ruins enemies
            ruins_enemies = [
                "dimenian",
                "la dimenian",
                "so dimenian",
                "bulclaw",
                "claw",
                "dark gunner",
                "delsaber",
                "chaos sorcerer",
                "dark belra",
                "chaos bringer",
                "dark falz",
            ]
            if normalized in ruins_enemies or any(re in enemy_lower for re in ruins_enemies):
                return "Ruins 1"

            # Default to Forest 1 for Episode 1
            return "Forest 1"

        # Episode 2 areas
        elif episode == 2:
            # VR Temple enemies
            vr_temple_enemies = [
                "merillia",
                "meriltas",
                "ul gibbon",
                "zol gibbon",
                "gibbon",
                "mercarol",
                "gi gue",
            ]
            if normalized in vr_temple_enemies or any(vt in enemy_lower for vt in vr_temple_enemies):
                return "VR Temple Alpha"

            # VR Spaceship enemies
            vr_spaceship_enemies = [
                "gee",
                "sinow berill",
                "sinow spigell",
                "sinow",
            ]
            if normalized in vr_spaceship_enemies or any(vs in enemy_lower for vs in vr_spaceship_enemies):
                # Default to Beta, but some quests use Alpha
                return "VR Spaceship Beta"

            # Mountain enemies
            mountain_enemies = [
                "gibbles",
            ]
            if normalized in mountain_enemies or any(me in enemy_lower for me in mountain_enemies):
                return "Mountain Area"

            # Seaside enemies (same as VR Temple typically)
            seaside_enemies = [
                "merillia",
                "meriltas",
            ]
            if normalized in seaside_enemies or any(se in enemy_lower for se in seaside_enemies):
                return "Seaside Area"

            # Central Control Area enemies
            central_control_enemies = [
                "ul gibbon",
                "zol gibbon",
            ]
            if normalized in central_control_enemies or any(cc in enemy_lower for cc in central_control_enemies):
                return "Central Control Area"

            # Seabed enemies
            seabed_enemies = [
                "dolmolm",
                "dolmdarl",
                "morfos",
            ]
            if normalized in seabed_enemies or any(sb in enemy_lower for sb in seabed_enemies):
                return "Seabed Upper Levels"

            # Control Tower enemies (same as Seabed typically)
            control_tower_enemies = [
                "dolmolm",
                "dolmdarl",
                "morfos",
            ]
            if normalized in control_tower_enemies or any(ct in enemy_lower for ct in control_tower_enemies):
                return "Control Tower"

            # Default to VR Temple Alpha for Episode 2
            return "VR Temple Alpha"

        # Episode 4 areas
        elif episode == 4:
            # Default to Crater East for Episode 4
            return "Crater East"

        # Fallback
        return "Forest 1"

    def _normalize_enemy_name(self, enemy_name: str) -> str:
        """
        Normalize enemy name for matching.
        Maps rare variant names to base names used in drop table.
        """
        # Check mapping first
        if enemy_name in self.ENEMY_NAME_MAPPING:
            return self.ENEMY_NAME_MAPPING[enemy_name]

        # If name contains "/", take the first part (base name)
        if "/" in enemy_name:
            parts = enemy_name.split("/")
            if len(parts) > 0:
                return parts[0].strip()

        return enemy_name.strip()

    def _normalize_quest_enemy_to_ultimate(self, enemy_name: str) -> str:
        """
        Normalize quest enemy name from non-Ultimate to Ultimate name.
        Maps base names (like "Rag Rappy", "Hildebear") to Ultimate names (like "El Rappy", "Hildelt").

        If the name is already in Ultimate form (exists as a key in ENEMY_NAME_MAPPING), return as-is.
        If the name is a base name (exists as a value in ENEMY_NAME_MAPPING), map it to Ultimate.
        """
        # First check if it's already an Ultimate name (key in mapping)
        if enemy_name in self.ENEMY_NAME_MAPPING:
            return enemy_name

        # Create reverse mapping: base -> Ultimate
        # ENEMY_NAME_MAPPING is Ultimate -> base, so reverse it
        base_to_ultimate = {base: ultimate for ultimate, base in self.ENEMY_NAME_MAPPING.items()}

        # Check if this is a base name that maps to an Ultimate name
        if enemy_name in base_to_ultimate:
            return base_to_ultimate[enemy_name]

        # If not found in either, return as-is (might be a name not in mapping)
        return enemy_name

    def _find_enemy_in_drop_table(self, enemy_name: str, episode: int) -> Optional[Dict]:
        """
        Find enemy in drop table, handling name variations.
        Returns enemy data or None if not found.
        """
        episode_key = f"episode{episode}"
        if episode_key not in self.drop_data:
            return None

        enemies = self.drop_data[episode_key].get("enemies", {})

        # Try exact match first
        if enemy_name in enemies:
            return enemies[enemy_name]

        # Try case-insensitive exact match
        enemy_name_lower = enemy_name.lower()
        for drop_enemy_name, enemy_data in enemies.items():
            if drop_enemy_name.lower() == enemy_name_lower:
                return enemy_data

        # Try mapped name (rare variant -> base name)
        # This handles cases like "Pal Rappy" -> "Al Rappy", "Mil Lily" -> "Nar Lily"
        mapped_name = self._normalize_enemy_name(enemy_name)
        if mapped_name != enemy_name and mapped_name in enemies:
            return enemies[mapped_name]

        # Try reverse lookup: check if any enemy in drop table normalizes to this name
        for drop_enemy_name, enemy_data in enemies.items():
            normalized_drop_name = self._normalize_enemy_name(drop_enemy_name)
            if normalized_drop_name == enemy_name or normalized_drop_name == mapped_name:
                return enemy_data

        # Try partial match (for cases like "Gulgus-Gue" matching "Barbarous Wolf")
        # This should be last resort
        for drop_enemy_name, enemy_data in enemies.items():
            drop_name_lower = drop_enemy_name.lower()
            if enemy_name_lower in drop_name_lower or drop_name_lower in enemy_name_lower:
                return enemy_data

        return None

    def _is_area_eligible_for_technique(self, area_name: str, technique_name: str) -> bool:
        """
        Check if an area is eligible for a specific level 30 technique.
        
        Args:
            area_name: Area name to check
            technique_name: Technique name (e.g., "Foie", "Barta")
        
        Returns:
            True if area is eligible for the technique, False otherwise
        """
        if technique_name not in LEVEL_30_TECHNIQUE_AREAS:
            return False
        
        eligible_areas = LEVEL_30_TECHNIQUE_AREAS[technique_name]
        # Check exact match or case-insensitive match
        area_name_lower = area_name.lower()
        return any(area.lower() == area_name_lower for area in eligible_areas)

    def _calculate_technique_drop_rate(
        self, event_type: Optional[EventType], area_name: str
    ) -> Dict[str, float]:
        """
        Calculate level 30 technique drop rates, assuming DAR has been met (something is dropping).
        
        This calculates the conditional probability: given that something drops,
        what's the probability it's a level 30 technique?
        
        Args:
            event_type: Active event type (None if no event)
            area_name: Area where monster is killed
        
        Returns:
            Dictionary mapping technique names to their conditional drop rates
            (caller must multiply by DAR to get actual drop rate)
        """
        technique_rates = {}
        
        # Conditional rate calculation (assuming DAR has been met):
        # (1 - event_item_rate) × (1 - music_disk_rate) × (1/3 for Tool) × 
        # (0.1 for Technique Disk) × (0.001 for specific technique) × (0.1 for level 30)
        # Note: RDR doesn't affect technique drops (techniques are not rare drops)
        
        # Event item rate (must fail during events)
        event_item_rate = 0.0
        if event_type in [EventType.Easter, EventType.Anniversary, EventType.Halloween, EventType.Christmas]:
            # Approximate event item rate - this is a placeholder, actual rate varies by event
            event_item_rate = 0.001  # Small rate, will be refined if needed
        
        # Calculate conditional rate (given something drops)
        conditional_rate = (
            (1.0 - event_item_rate) *  # (1 - event_item_rate)
            (1.0 - MUSIC_DISK_DROP_RATE) *  # (1 - music_disk_rate)
            TOOL_DROP_RATE *  # 1/3 for Tool
            TECHNIQUE_DISK_RATE *  # 0.1 for Technique Disk
            SPECIFIC_TECHNIQUE_RATE *  # 0.001 for specific technique
            LEVEL_30_RATE  # 0.1 for level 30
        )
        
        # Calculate rate for each technique if area is eligible
        for technique_name in LEVEL_30_TECHNIQUE_AREAS.keys():
            if self._is_area_eligible_for_technique(area_name, technique_name):
                technique_rates[technique_name] = conditional_rate
        
        return technique_rates

    def _calculate_box_technique_drop_rate(self, area_name: str) -> Dict[str, float]:
        """
        Calculate level 30 technique drop rates for boxes in a specific area.
        
        Note: Box drops (including techniques) are NOT affected by RDR multipliers or section_id.
        Techniques drop independently of rare drop rates.
        
        Args:
            area_name: Area where box is located
        
        Returns:
            Dictionary mapping technique names to their drop rates
        """
        technique_rates = {}
        
        # Base rate: 0.1 (Tool) × 0.1 (Technique Disk) × 0.001 (specific technique) × 0.1 (level 30)
        # = 1/1,000,000 per box
        base_rate = (
            0.1 *  # Tool roll (10%)
            TECHNIQUE_DISK_RATE *  # 0.1 for Technique Disk
            SPECIFIC_TECHNIQUE_RATE *  # 0.001 for specific technique
            LEVEL_30_RATE  # 0.1 for level 30
        )
        
        # Calculate rate for each technique if area is eligible
        for technique_name in LEVEL_30_TECHNIQUE_AREAS.keys():
            if self._is_area_eligible_for_technique(area_name, technique_name):
                technique_rates[technique_name] = base_rate
        
        return technique_rates

    def _calculate_boost_multipliers(
        self,
        quest_data: Dict,
        rbr_active: bool,
        weekly_boost: Optional[WeeklyBoost],
        event_type: Optional[EventType],
    ) -> Tuple[float, float, float]:
        """
        Calculate boost multipliers for a quest, dependent on a number of factors.
        TODO: Does not account for daily luck boost.
        
        Args:
            quest_data: Quest data dictionary
            rbr_active: Whether RBR boost is active
            weekly_boost: Type of weekly boost (WeeklyBoost enum or None)
            event_type: Type of active event (EventType enum or None)
        
        Returns:
            Tuple of (dar_multiplier, rdr_multiplier, enemy_rate_multiplier)
        """
        # Check if this is a Hallow quest (uses Halloween boosts instead of weekly boosts)
        is_hallow = self._is_hallow_quest(quest_data)
        # Check if quest is in RBR rotation (RBR boosts only apply if in rotation)
        in_rbr_rotation = self._is_in_rbr_rotation(quest_data)

        if is_hallow:
            # Hallow quests use Halloween boosts (ignore weekly_boost parameter, RBR boosts, and event boosts)
            dar_multiplier = 1.0 + HOLLOWEEN_QUEST_DAR_BOOST
            rdr_multiplier = 1.0 + HOLLOWEEN_QUEST_RDR_BOOST
            enemy_rate_multiplier = 1.0 + HOLLOWEEN_QUEST_RARE_ENEMY_BOOST
        else:
            # Regular quests use RBR and weekly boosts
            dar_multiplier = 1.0
            rdr_multiplier = 1.0
            enemy_rate_multiplier = 1.0

            # RBR boosts only apply if quest is in RBR rotation
            if in_rbr_rotation and rbr_active:
                dar_multiplier *= 1.0 + RBR_DAR_BOOST
                rdr_multiplier *= 1.0 + RBR_RDR_BOOST
                enemy_rate_multiplier *= 1.0 + RBR_ENEMY_RATE_BOOST

            # Apply weekly boosts (doubled if Christmas event is active)
            christmas_multiplier = 2.0 if event_type == EventType.Christmas else 1.0

            if weekly_boost == WeeklyBoost.DAR:
                dar_multiplier *= 1.0 + (WEEKLY_DAR_BOOST * christmas_multiplier)
            elif weekly_boost == WeeklyBoost.RDR:
                rdr_multiplier *= 1.0 + (WEEKLY_RDR_BOOST * christmas_multiplier)
            elif weekly_boost == WeeklyBoost.RareEnemy:
                enemy_rate_multiplier *= 1.0 + (WEEKLY_ENEMY_RATE_BOOST * christmas_multiplier)

        return dar_multiplier, rdr_multiplier, enemy_rate_multiplier

    @staticmethod
    def _calculate_rare_enemy_rates(enemy_rate_multiplier: float) -> Tuple[float, float]:
        """
        Calculate rare enemy spawn rates with boosts.
        
        Args:
            enemy_rate_multiplier: Multiplier for enemy rate boosts
        
        Returns:
            Tuple of (rare_enemy_rate, kondrieu_rate)
        """
        # Calculate rare enemy spawn rate with boosts
        # Note: Kondrieu has a fixed 1/10 rate (not affected by boosts) - handled separately
        rare_enemy_rate = BASE_RARE_ENEMY_RATE * enemy_rate_multiplier
        kondrieu_rate = RARE_ENEMY_RATE_KONDRIEU * enemy_rate_multiplier

        # Cap at reasonable maximum (e.g., 1/256 = ~0.39%)
        rare_enemy_rate = min(rare_enemy_rate, 1.0 / 256.0)
        kondrieu_rate = min(kondrieu_rate, 1.0)
        
        return rare_enemy_rate, kondrieu_rate

    def _normalize_quest_enemies(self, enemies: Dict[str, int]) -> Dict[str, int]:
        """
        Normalize quest enemy names from non-Ultimate to Ultimate names.
        
        Args:
            enemies: Dictionary mapping enemy names to counts
        
        Returns:
            Dictionary mapping normalized (Ultimate) enemy names to counts
        """
        normalized_enemies = {}
        for enemy_name, count in enemies.items():
            ultimate_name = self._normalize_quest_enemy_to_ultimate(enemy_name)
            if ultimate_name not in normalized_enemies:
                normalized_enemies[ultimate_name] = 0
            normalized_enemies[ultimate_name] += count
        return normalized_enemies

    @staticmethod
    def _adjust_dar(base_dar: float, multiplier: float) -> float:
        """
        Adjust DAR (Drop Anything Rate) with a multiplier, capping at 1.0.
        
        Args:
            base_dar: Base DAR value (0.0 to 1.0)
            multiplier: Multiplier to apply (e.g., 1.25 for +25% boost)
        
        Returns:
            Adjusted DAR value, capped at 1.0
        """
        return min(base_dar * multiplier, 1.0)

    def _process_enemy_drops(
        self, 
        enemy_name: str, 
        count: float, 
        episode: int, 
        section_id: str, 
        dar_multiplier: float, 
        rdr_multiplier: float, 
        area_name: Optional[str] = None, 
        event_type: Optional[EventType] = None
    ) -> Tuple[float, float, Dict, Dict]:
        """
        Process drops for a single enemy type.

        Returns:
            Tuple of (total_pd, total_pd_drops, enemy_breakdown, pd_drop_breakdown)
        """
        enemy_breakdown = {}
        pd_drop_breakdown = {}
        total_pd = 0.0
        total_pd_drops = 0.0

        # Find enemy in drop table
        enemy_data = self._find_enemy_in_drop_table(enemy_name, episode)
        section_drops = None
        if enemy_name in self.ENEMIES_WITHOUT_DROPS:
            return 0.0, 0.0, {}, {}

        if not enemy_data:
            # Fail fast: surface missing enemies instead of silently skipping
            raise ValueError(f"Enemy not found in drop table for episode {episode} and enemy name: '{enemy_name}'")

        # Get DAR and drop data for this Section ID
        dar = enemy_data.get("dar", 0.0)
        section_ids_data = enemy_data.get("section_ids", {})

        # Apply DAR multiplier, but cap at 1.0
        adjusted_dar = self._adjust_dar(dar, dar_multiplier)

        # Check if enemy has any item drops at all
        if not section_ids_data:
            enemy_breakdown[enemy_name] = {
                "count": count,
                "pd_value": 0.0,
                "error": "Enemy has no item drops in Ultimate difficulty",
            }
        else:
            section_drops = section_ids_data.get(section_id)

            if not section_drops:
                enemy_breakdown[enemy_name] = {
                    "count": count,
                    "pd_value": 0.0,
                    "error": f"No item drops for Section ID {section_id}",
                }

        # Calculate PD drops for ALL enemies (DAR affects, but RDR is fixed at 1/375)
        expected_pd_drops = count * adjusted_dar * BASE_PD_DROP_RATE
        total_pd_drops += expected_pd_drops

        pd_drop_breakdown[enemy_name] = {
            "count": count,
            "dar": dar,
            "adjusted_dar": adjusted_dar,
            "pd_drop_rate": BASE_PD_DROP_RATE,
            "expected_pd_drops": expected_pd_drops,
        }

        # Only process item drops if we have valid section_drops
        if section_drops:
            # Get item and RDR
            item_name = section_drops.get("item", "")
            base_rdr = section_drops.get("rdr", 0.0)

            # Apply RDR multiplier
            adjusted_rdr = base_rdr * rdr_multiplier

            # Calculate expected drops
            expected_drops = count * adjusted_dar * adjusted_rdr

            # Determine drop area for weapon value calculation
            drop_area = area_name if area_name else self._determine_drop_area(enemy_name, episode)

            # Get item price (already in PD)
            item_price_pd = self._get_item_price_pd(item_name, drop_area)

            # Expected PD value
            expected_pd = expected_drops * item_price_pd

            total_pd += expected_pd

            enemy_breakdown[enemy_name] = {
                "count": count,
                "dar": dar,
                "adjusted_dar": adjusted_dar,
                "rdr": base_rdr,
                "adjusted_rdr": adjusted_rdr,
                "item": item_name,
                "item_price_pd": item_price_pd,
                "expected_drops": expected_drops,
                "pd_value": expected_pd,
            }

        # Calculate technique drops if area is provided
        if area_name:
            technique_rates = self._calculate_technique_drop_rate(event_type, area_name)
            for technique_name, conditional_rate in technique_rates.items():
                # Multiply by DAR to get actual drop rate
                technique_rate = adjusted_dar * conditional_rate
                expected_technique_drops = count * technique_rate
                technique_item_name = f"{technique_name} Lv30"
                try:
                    # Look up technique directly by name and level
                    technique_price_pd = self.price_guide.get_price_disk(technique_name, 30)
                except PriceGuideExceptionItemNameNotFound:
                    # Technique not in price guide - this is a data issue that should be fixed
                    raise PriceGuideExceptionItemNameNotFound(
                        f"Technique {technique_item_name} not found in price guide. "
                        f"This technique can drop in {area_name} but is missing from price data."
                    )
                technique_pd_value = expected_technique_drops * technique_price_pd
                total_pd += technique_pd_value
                
                # Add to breakdown
                if technique_item_name not in enemy_breakdown:
                    enemy_breakdown[technique_item_name] = {
                        "count": count,
                        "dar": dar,
                        "adjusted_dar": adjusted_dar,
                        "area": area_name,
                        "drop_rate": technique_rate,
                        "expected_drops": 0.0,
                        "item_price_pd": technique_price_pd,
                        "pd_value": 0.0,
                    }
                enemy_breakdown[technique_item_name]["expected_drops"] += expected_technique_drops
                enemy_breakdown[technique_item_name]["pd_value"] += technique_pd_value

        return total_pd, total_pd_drops, enemy_breakdown, pd_drop_breakdown

    def _process_box_drops(
        self,
        area_name: str,
        box_counts: Dict[str, int],
        episode: int,
        section_id: str,
    ) -> Tuple[float, Dict]:
        """
        Process box drops for an area.

        Only processes "box" type (regular boxes that can drop rare items).
        Skips box_armor, box_weapon, and box_rareless.

        Note: Box drops are NOT affected by any drop rate bonuses (DAR, RDR, etc.).
        They use the base drop rate directly from the drop table.

        Args:
            area_name: Quest area name (will be mapped to drop table area)
            box_counts: Dictionary mapping box types to counts
            episode: Episode number (1, 2, or 4)
            section_id: Section ID to use for drops

        Returns:
            Tuple of (total_pd, box_breakdown)
        """
        total_pd = 0.0
        box_breakdown = {}

        # Only process regular boxes (box_armor, box_weapon, box_rareless cannot drop rare items)
        regular_box_count = box_counts.get("box", 0)
        if regular_box_count == 0:
            return 0.0, {}

        # Map quest area name to drop table area name
        mapped_area = self.quest_listing.map_quest_area_to_drop_table_area(area_name)

        # Get box drop data from drop table
        episode_key = f"episode{episode}"
        if episode_key not in self.drop_data:
            raise DropTableNotFoundError(f"Drop table not found for episode {episode}")

        boxes_data = self.drop_data[episode_key].get("boxes", {})
        if mapped_area not in boxes_data:
            raise DropTableNotFoundError(
                f"Box drop area not found in drop table for episode {episode} and area name: '{area_name}'"
            )

        section_ids_data = boxes_data[mapped_area].get("section_ids", {})
        if section_id not in section_ids_data:
            # Special case for Yellowboze certain areas, which has no box drops.
            if section_id == "Yellowboze" and episode == 1 and area_name == "Forest 1":
                return 0.0, {}
            elif section_id == "Yellowboze" and episode == 1 and area_name == "Cave 1":
                return 0.0, {}
            elif section_id == "Yellowboze" and episode == 2 and area_name == "VR Spaceship Beta":
                return 0.0, {}

            raise DropTableNotFoundError(
                f"Section ID not found in drop table for episode {episode} and area name: '{area_name}' and section ID: '{section_id}'"
            )

        # Get list of items that can drop from boxes in this area/section
        box_items = section_ids_data[section_id]

        # Process each item that can drop from boxes
        for item_data in box_items:
            item_name = item_data.get("item", "")
            drop_rate = item_data.get("rate", 0.0)

            # Calculate expected drops: box_count * drop_rate
            # Note: Box drops are NOT affected by DAR, RDR, or any other drop rate bonuses
            expected_drops = regular_box_count * drop_rate

            # Get item price
            # For rare weapons, area doesn't affect hit probability (always uses Pattern 5)
            # Area is only used for common weapons, so pass None for box drops (rare weapons)
            item_price_pd = self._get_item_price_pd(item_name)
            # Expected PD value
            expected_pd = expected_drops * item_price_pd
            total_pd += expected_pd

            # Add to breakdown
            if item_name not in box_breakdown:
                box_breakdown[item_name] = {
                    "box_count": regular_box_count,
                    "drop_rate": drop_rate,
                    "expected_drops": 0.0,
                    "item_price_pd": item_price_pd,
                    "pd_value": 0.0,
                }

            box_breakdown[item_name]["expected_drops"] += expected_drops
            box_breakdown[item_name]["pd_value"] += expected_pd

        # Calculate technique drops for non-set boxes
        # Use quest area name (not mapped area) for technique eligibility check
        technique_rates = self._calculate_box_technique_drop_rate(area_name)
        for technique_name, technique_rate in technique_rates.items():
            expected_technique_drops = regular_box_count * technique_rate
            technique_item_name = f"{technique_name} Lv30"
            try:
                # Look up technique directly by name and level
                technique_price_pd = self.price_guide.get_price_disk(technique_name, 30)
            except PriceGuideExceptionItemNameNotFound:
                # Technique not in price guide - this is a data issue that should be fixed
                raise PriceGuideExceptionItemNameNotFound(
                    f"Technique {technique_item_name} not found in price guide. "
                    f"This technique can drop in {area_name} but is missing from price data."
                )
            technique_pd_value = expected_technique_drops * technique_price_pd
            total_pd += technique_pd_value
            
            # Add to breakdown
            if technique_item_name not in box_breakdown:
                box_breakdown[technique_item_name] = {
                    "box_count": regular_box_count,
                    "drop_rate": technique_rate,
                    "expected_drops": 0.0,
                    "item_price_pd": technique_price_pd,
                    "pd_value": 0.0,
                    "area": area_name,
                }
            box_breakdown[technique_item_name]["expected_drops"] += expected_technique_drops
            box_breakdown[technique_item_name]["pd_value"] += technique_pd_value

        return total_pd, box_breakdown

    def _process_enemy_list(
        self,
        enemies: Dict[str, int],
        episode: int,
        section_id: str,
        dar_multiplier: float,
        rdr_multiplier: float,
        rare_enemy_rate: float,
        kondrieu_rate: float,
        rare_mapping: Dict[str, str],
        area_name: Optional[str] = None,
        event_type: Optional[EventType] = None,
        merge_breakdowns: bool = False,
    ) -> Tuple[float, float, int, Dict, Dict]:
        """
        Process a list of enemies and return PD values and breakdowns.
        
        Args:
            enemies: Dictionary mapping enemy names to counts
            episode: Episode number
            section_id: Section ID
            dar_multiplier: DAR multiplier
            rdr_multiplier: RDR multiplier
            rare_enemy_rate: Rate for rare enemy spawns
            kondrieu_rate: Rate for Kondrieu spawns
            rare_mapping: Mapping of normal enemies to rare variants
            area_name: Optional area name for technique drops
            event_type: Optional event type
            merge_breakdowns: If True, merge entries when they already exist (for multi-area processing)
        
        Returns:
            Tuple of (total_pd, total_pd_drops, enemy_breakdown, pd_drop_breakdown)
        """
        total_pd = 0.0
        total_pd_drops = 0.0
        enemy_breakdown = {}
        pd_drop_breakdown = {}
        total_enemies = 0
        
        # Slime enemies that can be split
        SLIME_ENEMIES = ["Pofuilly Slime", "Pouilly Slime"]
        
        # Normalize quest enemy names from non-Ultimate to Ultimate names
        normalized_enemies = self._normalize_quest_enemies(enemies)
        
        # Process each enemy
        for enemy_name, count in normalized_enemies.items():
            # Apply slime splitting if enabled
            if SLIME_SPLIT and enemy_name in SLIME_ENEMIES:
                count = count * SLIME_SPLIT_MULTIPLIER
            
            total_enemies += count
            
            # Check if this enemy can spawn as a rare variant
            rare_variant = rare_mapping.get(enemy_name)
            
            if rare_variant:
                # Special case: Kondrieu uses 1/10 base rate but can be boosted by RareEnemy boost
                if rare_variant == "Kondrieu":
                    normal_count = count * (1.0 - kondrieu_rate)
                    rare_count = count * kondrieu_rate
                else:
                    # Normal rare enemy rate calculation
                    normal_count = count * (1.0 - rare_enemy_rate)
                    rare_count = count * rare_enemy_rate
                
                # Process normal version
                normal_pd, normal_pd_drops, normal_breakdown, normal_pd_breakdown = self._process_enemy_drops(
                    enemy_name, normal_count, episode, section_id, dar_multiplier, rdr_multiplier, area_name, event_type
                )
                
                # Process rare version
                rare_pd, rare_pd_drops, rare_breakdown, rare_pd_breakdown = self._process_enemy_drops(
                    rare_variant, rare_count, episode, section_id, dar_multiplier, rdr_multiplier, area_name, event_type
                )
                
                # Combine results
                total_pd += normal_pd + rare_pd
                total_pd_drops += normal_pd_drops + rare_pd_drops
                
                # Merge breakdowns
                if merge_breakdowns:
                    # Merge logic for multi-area processing - merge ALL entries (including techniques)
                    if normal_breakdown:
                        for key, value in normal_breakdown.items():
                            if key in enemy_breakdown:
                                enemy_breakdown[key]["count"] = enemy_breakdown[key].get("count", 0) + value.get("count", 0)
                                enemy_breakdown[key]["pd_value"] = enemy_breakdown[key].get("pd_value", 0.0) + value.get("pd_value", 0.0)
                                if "expected_drops" in value:
                                    enemy_breakdown[key]["expected_drops"] = enemy_breakdown[key].get("expected_drops", 0.0) + value.get("expected_drops", 0.0)
                            else:
                                enemy_breakdown[key] = value.copy()
                    
                    if rare_breakdown:
                        for key, value in rare_breakdown.items():
                            if key in enemy_breakdown:
                                enemy_breakdown[key]["count"] = enemy_breakdown[key].get("count", 0) + value.get("count", 0)
                                enemy_breakdown[key]["pd_value"] = enemy_breakdown[key].get("pd_value", 0.0) + value.get("pd_value", 0.0)
                                if "expected_drops" in value:
                                    enemy_breakdown[key]["expected_drops"] = enemy_breakdown[key].get("expected_drops", 0.0) + value.get("expected_drops", 0.0)
                            else:
                                enemy_breakdown[key] = value.copy()
                    
                    # Merge PD drop breakdowns
                    if normal_pd_breakdown:
                        for key, value in normal_pd_breakdown.items():
                            if key in pd_drop_breakdown:
                                pd_drop_breakdown[key]["count"] = pd_drop_breakdown[key].get("count", 0) + value.get("count", 0)
                                pd_drop_breakdown[key]["expected_pd_drops"] = pd_drop_breakdown[key].get("expected_pd_drops", 0.0) + value.get("expected_pd_drops", 0.0)
                            else:
                                pd_drop_breakdown[key] = value.copy()
                    
                    if rare_pd_breakdown:
                        for key, value in rare_pd_breakdown.items():
                            if key in pd_drop_breakdown:
                                pd_drop_breakdown[key]["count"] = pd_drop_breakdown[key].get("count", 0) + value.get("count", 0)
                                pd_drop_breakdown[key]["expected_pd_drops"] = pd_drop_breakdown[key].get("expected_pd_drops", 0.0) + value.get("expected_pd_drops", 0.0)
                            else:
                                pd_drop_breakdown[key] = value.copy()
                else:
                    # Simple merge logic for single-area processing - merge ALL entries (including techniques)
                    if normal_breakdown:
                        enemy_breakdown.update(normal_breakdown)
                    if rare_breakdown:
                        enemy_breakdown.update(rare_breakdown)
                    
                    # Merge PD drop breakdowns
                    if normal_pd_breakdown:
                        pd_drop_breakdown.update(normal_pd_breakdown)
                    if rare_pd_breakdown:
                        pd_drop_breakdown.update(rare_pd_breakdown)
            else:
                # Process normally (no rare variant)
                normal_pd, normal_pd_drops, normal_breakdown, normal_pd_breakdown = self._process_enemy_drops(
                    enemy_name, count, episode, section_id, dar_multiplier, rdr_multiplier, area_name, event_type
                )
                
                total_pd += normal_pd
                total_pd_drops += normal_pd_drops
                
                # Merge breakdowns
                if merge_breakdowns:
                    # Merge logic for multi-area processing
                    if normal_breakdown:
                        for key, value in normal_breakdown.items():
                            if key in enemy_breakdown:
                                enemy_breakdown[key]["count"] = enemy_breakdown[key].get("count", 0) + value.get("count", 0)
                                enemy_breakdown[key]["pd_value"] = enemy_breakdown[key].get("pd_value", 0.0) + value.get("pd_value", 0.0)
                                if "expected_drops" in value:
                                    enemy_breakdown[key]["expected_drops"] = enemy_breakdown[key].get("expected_drops", 0.0) + value.get("expected_drops", 0.0)
                            else:
                                enemy_breakdown[key] = value.copy()
                    
                    if normal_pd_breakdown:
                        for key, value in normal_pd_breakdown.items():
                            if key in pd_drop_breakdown:
                                pd_drop_breakdown[key]["count"] = pd_drop_breakdown[key].get("count", 0) + value.get("count", 0)
                                pd_drop_breakdown[key]["expected_pd_drops"] = pd_drop_breakdown[key].get("expected_pd_drops", 0.0) + value.get("expected_pd_drops", 0.0)
                            else:
                                pd_drop_breakdown[key] = value.copy()
                else:
                    # Simple merge logic for single-area processing
                    if normal_breakdown:
                        enemy_breakdown.update(normal_breakdown)
                    if normal_pd_breakdown:
                        pd_drop_breakdown.update(normal_pd_breakdown)
        
        return total_pd, total_pd_drops, total_enemies, enemy_breakdown, pd_drop_breakdown

    def calculate_quest_value(
        self,
        quest_data: Dict,
        section_id: str,
        rbr_active: bool = False,
        weekly_boost: Optional[WeeklyBoost] = None,
        event_type: Optional[EventType] = None,
    ) -> Dict:
        """
        Calculate expected PD value for a quest.

        Args:
            quest_data: Quest JSON data with enemy counts
            section_id: Section ID to use for drops
            rbr_active: Whether RBR boost is active
            weekly_boost: Type of weekly boost (WeeklyBoost enum or None)
            event_type: Type of active event (EventType enum or None)

        Returns:
            Dictionary with calculated values:
            {
                "total_pd": float,
                "enemy_breakdown": {...},
                "total_enemies": int
            }
        """
        episode = quest_data.get("episode", 1)
        enemies = quest_data.get("enemies", {})

        total_pd = 0.0
        total_pd_drops = 0.0  # Expected PD drops (not item value)
        enemy_breakdown = {}
        pd_drop_breakdown = {}  # Breakdown of PD drops per enemy
        total_enemies = 0

        # Calculate boost multipliers and rare enemy rates
        dar_multiplier, rdr_multiplier, enemy_rate_multiplier = self._calculate_boost_multipliers(
            quest_data, rbr_active, weekly_boost, event_type
        )
        rare_enemy_rate, kondrieu_rate = self._calculate_rare_enemy_rates(enemy_rate_multiplier)

        # Episode-specific rare enemy mapping
        rare_mapping = self._get_rare_enemy_mapping(episode)

        # Process enemies per area (for technique drops, area matters)
        quest_areas = quest_data.get("areas", [])
        
        # If no areas defined, process enemies globally (backward compatibility)
        if not quest_areas:
            area_pd, area_pd_drops, area_total_enemies, area_enemy_breakdown, area_pd_breakdown = self._process_enemy_list(
                enemies, episode, section_id, dar_multiplier, rdr_multiplier,
                rare_enemy_rate, kondrieu_rate, rare_mapping, None, event_type, False
            )
            total_pd += area_pd
            total_pd_drops += area_pd_drops
            total_enemies += area_total_enemies
            enemy_breakdown.update(area_enemy_breakdown)
            pd_drop_breakdown.update(area_pd_breakdown)

        # If areas defined, process enemies per area
        else:
            # Process enemies per area
            # First, check if any areas have explicit enemies
            areas_with_enemies = [area for area in quest_areas if area.get("enemies")]
            
            if areas_with_enemies:
                # Process enemies from areas that explicitly have them
                for area in areas_with_enemies:
                    area_name = area.get("name", "")
                    area_enemies = area.get("enemies", {})
                    
                    area_pd, area_pd_drops, area_total_enemies, area_enemy_breakdown, area_pd_breakdown = self._process_enemy_list(
                        area_enemies, episode, section_id, dar_multiplier, rdr_multiplier,
                        rare_enemy_rate, kondrieu_rate, rare_mapping, area_name, event_type, True
                    )
                    total_pd += area_pd
                    total_pd_drops += area_pd_drops
                    total_enemies += area_total_enemies
                    # Merge breakdowns (handle duplicates across areas)
                    for key, value in area_enemy_breakdown.items():
                        if key in enemy_breakdown:
                            enemy_breakdown[key]["count"] = enemy_breakdown[key].get("count", 0) + value.get("count", 0)
                            enemy_breakdown[key]["pd_value"] = enemy_breakdown[key].get("pd_value", 0.0) + value.get("pd_value", 0.0)
                            if "expected_drops" in value:
                                enemy_breakdown[key]["expected_drops"] = enemy_breakdown[key].get("expected_drops", 0.0) + value.get("expected_drops", 0.0)
                        else:
                            enemy_breakdown[key] = value.copy()
                    for key, value in area_pd_breakdown.items():
                        if key in pd_drop_breakdown:
                            pd_drop_breakdown[key]["count"] = pd_drop_breakdown[key].get("count", 0) + value.get("count", 0)
                            pd_drop_breakdown[key]["expected_pd_drops"] = pd_drop_breakdown[key].get("expected_pd_drops", 0.0) + value.get("expected_pd_drops", 0.0)
                        else:
                            pd_drop_breakdown[key] = value.copy()
            else:
                # No areas have explicit enemies, process global enemies once with first area as context
                area_name = quest_areas[0].get("name", "") if quest_areas else None
                
                area_pd, area_pd_drops, area_total_enemies, area_enemy_breakdown, area_pd_breakdown = self._process_enemy_list(
                    enemies, episode, section_id, dar_multiplier, rdr_multiplier,
                    rare_enemy_rate, kondrieu_rate, rare_mapping, area_name, event_type, False
                )
                total_pd += area_pd
                total_pd_drops += area_pd_drops
                total_enemies += area_total_enemies
                enemy_breakdown.update(area_enemy_breakdown)
                pd_drop_breakdown.update(area_pd_breakdown)

        # Process box drops
        # Note: Box drops are NOT affected by any drop rate bonuses (DAR, RDR, etc.)
        box_pd = 0.0
        box_breakdown = {}
        # Reuse quest_areas from above (or get it if we didn't process enemies per area)
        if not quest_areas:
            quest_areas = quest_data.get("areas", [])
        for area in quest_areas:
            area_name = area.get("name", "")
            boxes = area.get("boxes", {})
            if boxes:
                area_box_pd, area_box_breakdown = self._process_box_drops(area_name, boxes, episode, section_id)
                box_pd += area_box_pd
                # Merge area box breakdown into overall box breakdown
                for item_name, item_data in area_box_breakdown.items():
                    if item_name not in box_breakdown:
                        box_breakdown[item_name] = item_data
                    else:
                        # Combine data from multiple areas
                        box_breakdown[item_name]["box_count"] += item_data["box_count"]
                        box_breakdown[item_name]["expected_drops"] += item_data["expected_drops"]
                        box_breakdown[item_name]["pd_value"] += item_data["pd_value"]

        # Add box PD to total
        total_pd += box_pd

        # Process quest completion items
        completion_items_pd = 0.0
        completion_items_breakdown = {}
        quest_completion_items = quest_data.get("quest_completion_items", {})

        for item_name, quantity in quest_completion_items.items():
            # Look up item value in price guide
            item_price_pd = self._get_item_price_pd(item_name)
            item_total_pd = item_price_pd * quantity
            completion_items_pd += item_total_pd

            completion_items_breakdown[item_name] = {
                "quantity": quantity,
                "item_price_pd": item_price_pd,
                "total_pd": item_total_pd,
            }

        # Add completion items PD to total
        total_pd += completion_items_pd

        # Add random PD drops to total (PD/Quest should include everything)
        total_pd += total_pd_drops

        # Process event drops (Christmas Presents, Halloween Cookies, and Easter Eggs)
        event_drops_pd = 0.0
        event_drops_breakdown = {}
        
        # Christmas Presents: only during Christmas event
        if event_type == EventType.Christmas:
            # Calculate expected presents from all enemies
            # Present drop rate: 1/2250, affected by DAR
            present_drop_rate = CHRISTMAS_PRESENT_DROP_RATE
            expected_presents = total_enemies * dar_multiplier * present_drop_rate
            
            # Get present price
            try:
                present_price = self._get_item_price_pd("Present")
                present_pd_value = expected_presents * present_price
                event_drops_pd += present_pd_value
                
                event_drops_breakdown["Present"] = {
                    "drop_rate": present_drop_rate,
                    "expected_drops": expected_presents,
                    "item_price_pd": present_price,
                    "pd_value": present_pd_value,
                }
            except Exception:
                pass  # Present not found in price guide
        
        # Halloween Cookies: only during Halloween event
        if event_type == EventType.Halloween:
            # Base cookie drop rate: 1/1500
            cookie_drop_rate = HALLOWEEN_COOKIE_DROP_RATE
            
            # If this is a Halloween quest, apply 20% boost
            is_hallow = self._is_hallow_quest(quest_data)
            if is_hallow:
                cookie_drop_rate *= HALLOWEEN_QUEST_COOKIE_MULTIPLIER
            
            # Calculate expected cookies from all enemies
            # Cookie drop rate affected by DAR
            expected_cookies = total_enemies * dar_multiplier * cookie_drop_rate
            
            # Get cookie price
            try:
                cookie_price = self._get_item_price_pd("Halloween Cookie")
                cookie_pd_value = expected_cookies * cookie_price
                event_drops_pd += cookie_pd_value
                
                event_drops_breakdown["Halloween Cookie"] = {
                    "drop_rate": cookie_drop_rate,
                    "expected_drops": expected_cookies,
                    "item_price_pd": cookie_price,
                    "pd_value": cookie_pd_value,
                    "is_halloween_quest": is_hallow,
                }
            except Exception:
                pass  # Cookie not found in price guide
        
        # Easter Eggs: only during Easter event
        if event_type == EventType.Easter:
            # Calculate expected eggs from all enemies
            # Egg drop rate: 1/500, affected by DAR
            egg_drop_rate = EASTER_EGG_DROP_RATE
            expected_eggs = total_enemies * dar_multiplier * egg_drop_rate
            
            # Get egg price
            try:
                egg_price = self._get_item_price_pd("Event Egg")
                egg_pd_value = expected_eggs * egg_price
                event_drops_pd += egg_pd_value
                
                event_drops_breakdown["Event Egg"] = {
                    "drop_rate": egg_drop_rate,
                    "expected_drops": expected_eggs,
                    "item_price_pd": egg_price,
                    "pd_value": egg_pd_value,
                }
            except Exception:
                pass  # Event Egg not found in price guide
        
        # Add event drops PD to total
        total_pd += event_drops_pd

        return {
            "total_pd": total_pd,
            "total_pd_drops": total_pd_drops,  # Expected PD drops (not item value)
            "enemy_breakdown": enemy_breakdown,
            "pd_drop_breakdown": pd_drop_breakdown,
            "box_breakdown": box_breakdown,
            "box_pd": box_pd,
            "completion_items_breakdown": completion_items_breakdown,
            "completion_items_pd": completion_items_pd,
            "event_drops_breakdown": event_drops_breakdown,
            "event_drops_pd": event_drops_pd,
            "total_enemies": total_enemies,
            "section_id": section_id,
            "rbr_active": rbr_active,
            "weekly_boost": weekly_boost,
        }

    def calculate_all_section_ids(
        self,
        quest_data: Dict,
        rbr_active: bool = False,
        weekly_boost: Optional[WeeklyBoost] = None,
        event_type: Optional[EventType] = None,
    ) -> Dict[str, Dict]:
        """
        Calculate quest value for all Section IDs.

        Returns:
            Dictionary mapping Section ID to calculated values
        """
        results = {}
        for section_id_enum in SectionIds:
            section_id: str = section_id_enum.value
            results[section_id] = self.calculate_quest_value(quest_data, section_id, rbr_active, weekly_boost, event_type)

        return results

    def _is_technique_lv30(self, item_name: str) -> Optional[str]:
        """
        Check if item name is a level 30 technique and return the technique name.
        
        Args:
            item_name: Item name to check (e.g., "Foie Lv30", "Foie")
        
        Returns:
            Technique name if it's a level 30 technique, None otherwise
        """
        item_norm = item_name.strip().lower()
        
        # Check if it matches "Technique Lv30" pattern
        if "lv30" in item_norm or "lv 30" in item_norm:
            # Extract technique name (everything before "lv30" or "lv 30")
            technique_name = item_norm.split("lv30")[0].split("lv 30")[0].strip()
            if technique_name in [t.lower() for t in LEVEL_30_TECHNIQUE_AREAS.keys()]:
                # Return the canonical technique name (capitalized)
                for tech_name in LEVEL_30_TECHNIQUE_AREAS.keys():
                    if tech_name.lower() == technique_name:
                        return tech_name
        
        # Check if it's just a technique name (without level)
        if item_norm in [t.lower() for t in LEVEL_30_TECHNIQUE_AREAS.keys()]:
            for tech_name in LEVEL_30_TECHNIQUE_AREAS.keys():
                if tech_name.lower() == item_norm:
                    return tech_name
        
        return None

    def _weapon_matches(self, item_name: str, target_weapon: str) -> bool:
        """
        Check if item name matches target weapon (case-insensitive).
        Handles variations like parentheses and partial matches.
        """
        item_norm = item_name.strip().lower()
        target_norm = target_weapon.strip().lower()

        # Exact match
        if item_norm == target_norm:
            return True

        # Check if target is contained in item (handles "Flowen's Sword" matching "Flowen's Sword (3064)")
        if target_norm in item_norm:
            return True

        # Check if item is contained in target (handles "Flowen's Sword (3064)" matching "Flowen's Sword")
        if item_norm in target_norm:
            return True

        # Remove parentheses and content for comparison
        item_no_parens = item_norm.split("(")[0].strip()
        target_no_parens = target_norm.split("(")[0].strip()

        if item_no_parens == target_no_parens:
            return True

        return False

    def _get_enemy_weapon_drop_prob(
        self,
        enemy_name: str,
        count: float,
        episode: int,
        section_id: str,
        dar_multiplier: float,
        rdr_multiplier: float,
        weapon_name: str,
        area_name: Optional[str] = None,
        event_type: Optional[EventType] = None,
    ) -> Tuple[float, List[Dict]]:
        """
        Get drop probability for a weapon from a specific enemy.
        Also handles level 30 technique drops if weapon_name is a technique.

        Returns:
            Tuple of (total_probability, list of contributions)
        """
        contributions = []
        total_prob = 0.0

        # Check if this is a level 30 technique
        technique_name = self._is_technique_lv30(weapon_name)
        if technique_name and area_name:
            # Calculate technique drop probability
            enemy_data = self._find_enemy_in_drop_table(enemy_name, episode)
            if enemy_data:
                dar = enemy_data.get("dar", 0.0)
                adjusted_dar = self._adjust_dar(dar, dar_multiplier)
                technique_rates = self._calculate_technique_drop_rate(event_type, area_name)
                
                if technique_name in technique_rates:
                    conditional_rate = technique_rates[technique_name]
                    # Multiply by DAR to get actual drop rate
                    technique_rate = adjusted_dar * conditional_rate
                    technique_prob = count * technique_rate
                    total_prob += technique_prob
                    
                    contributions.append(
                        {
                            "enemy": enemy_name,
                            "count": count,
                            "dar": dar,
                            "adjusted_dar": adjusted_dar,
                            "rdr": 0.0,  # RDR doesn't affect techniques
                            "adjusted_rdr": 0.0,
                            "probability": technique_prob,
                            "item": f"{technique_name} Lv30",
                            "area": area_name,
                            "source": "Technique",
                        }
                    )
            
            # Return early for techniques (they don't drop from regular enemy drops)
            return total_prob, contributions

        # Regular weapon drop logic
        # Find enemy in drop table
        enemy_data = self._find_enemy_in_drop_table(enemy_name, episode)

        if not enemy_data:
            return 0.0, []

        # Get DAR (Drop Anything Rate)
        dar = enemy_data.get("dar", 0.0)

        # Get section ID drop data
        section_ids_data = enemy_data.get("section_ids", {})
        section_drops = section_ids_data.get(section_id)

        if not section_drops:
            return 0.0, []

        # Get item name and RDR (Rare Drop Rate)
        item_name = section_drops.get("item", "")
        rdr = section_drops.get("rdr", 0.0)

        # Check if this item matches our target weapon
        if self._weapon_matches(item_name, weapon_name):
            # Apply multipliers (cap DAR at 1.0)
            adjusted_dar = self._adjust_dar(dar, dar_multiplier)
            adjusted_rdr = rdr * rdr_multiplier
            # Calculate drop probability: count * adjusted_DAR * adjusted_RDR
            enemy_prob = count * adjusted_dar * adjusted_rdr
            total_prob += enemy_prob

            contributions.append(
                {
                    "enemy": enemy_name,
                    "count": count,
                    "dar": dar,
                    "adjusted_dar": adjusted_dar,
                    "rdr": rdr,
                    "adjusted_rdr": adjusted_rdr,
                    "probability": enemy_prob,
                    "item": item_name,
                }
            )

        return total_prob, contributions

    def _get_box_item_drop_prob(
        self,
        area_name: str,
        box_counts: Dict[str, int],
        episode: int,
        section_id: str,
        item_name: str,
    ) -> Tuple[float, List[Dict]]:
        """
        Get drop probability for a item from boxes in a specific area.
        Also handles level 30 technique drops if item_name is a technique.

        Returns:
            Tuple of (total_probability, list of contributions)
        """
        contributions = []
        total_prob = 0.0

        # Only process regular boxes (box_armor, box_weapon, box_rareless cannot drop rare items)
        regular_box_count = box_counts.get("box", 0)
        if regular_box_count == 0:
            return 0.0, []

        # Check if this is a level 30 technique
        technique_name = self._is_technique_lv30(item_name)
        if technique_name:
            # Calculate technique drop probability for boxes
            # Technique drops are independent of section_id and don't require box drop data
            technique_rates = self._calculate_box_technique_drop_rate(area_name)
            
            if technique_name in technique_rates:
                technique_rate = technique_rates[technique_name]
                technique_prob = regular_box_count * technique_rate
                total_prob += technique_prob
                
                contributions.append(
                    {
                        "source": "Box",
                        "area": area_name,
                        "box_count": regular_box_count,
                        "drop_rate": technique_rate,
                        "probability": technique_prob,
                        "item": f"{technique_name} Lv30",
                        "technique": True,
                    }
                )
            
            # Return early for techniques (they don't drop from regular box drops)
            return total_prob, contributions

        # Regular weapon drop logic
        # Map quest area name to drop table area name
        mapped_area = self.quest_listing.map_quest_area_to_drop_table_area(area_name)

        # Get box drop data from drop table
        episode_key = f"episode{episode}"
        if episode_key not in self.drop_data:
            return 0.0, []

        boxes_data = self.drop_data[episode_key].get("boxes", {})
        if mapped_area not in boxes_data:
            return 0.0, []

        section_ids_data = boxes_data[mapped_area].get("section_ids", {})
        if section_id not in section_ids_data:
            return 0.0, []

        # Get list of items that can drop from boxes in this area/section
        box_items = section_ids_data[section_id]

        # Process each item that can drop from boxes
        for item_data in box_items:
            box_item_name = item_data.get("item", "")
            drop_rate = item_data.get("rate", 0.0)

            # Check if this item matches our target weapon
            if self._weapon_matches(box_item_name, item_name):
                # Box drops are NOT affected by DAR, RDR, or any other drop rate bonuses
                # Calculate drop probability: box_count * drop_rate
                box_prob = regular_box_count * drop_rate
                total_prob += box_prob

                contributions.append(
                    {
                        "source": "Box",
                        "area": area_name,
                        "box_count": regular_box_count,
                        "drop_rate": drop_rate,
                        "probability": box_prob,
                        "item": box_item_name,
                    }
                )

        return total_prob, contributions

    def find_best_quests_for_item(
        self,
        weapon_name: str,
        rbr_active: bool = False,
        rbr_list: Optional[List[str]] = None,
        weekly_boost: Optional[WeeklyBoost] = None,
        quest_filter: Optional[List[str]] = None,
        event_type: Optional[EventType] = None,
    ) -> List[Dict]:
        """
        Find all quest/Section ID combinations that drop the weapon, sorted by probability.

        Args:
            weapon_name: Name of the weapon to search for
            rbr_active: Whether RBR boost is active for all quests
            rbr_list: Optional list of quest short names to apply RBR boost to (mutually exclusive with rbr_active)
            weekly_boost: Type of weekly boost (WeeklyBoost enum or None)
            quest_filter: Optional list of quest names to filter to (case-insensitive)

            Returns:
            List of results, each containing:
            - quest_name: Quest ID
            - long_name: Quest full name
            - section_id: Section ID
            - probability: Total drop probability per quest run
            - percentage: Drop probability as percentage
            - contributions: List of enemy and box contributions
        """
        # Base multipliers (will be adjusted per quest based on in_rbr_rotation field)

        results = []

        # Normalize rbr_list to lowercase for case-insensitive matching
        rbr_list_lower = [q.lower() for q in rbr_list] if rbr_list else None

        # Filter quests if requested
        quests_to_search: List[Dict]
        if quest_filter:
            quest_filter_lower = [q.lower() for q in quest_filter]
            quests_to_search = [quest for quest in self.quest_data if quest.get("quest_name", "").lower() in quest_filter_lower]
        else:
            quests_to_search = self.quest_data

        for quest in quests_to_search:
            quest_name = quest.get("quest_name", "Unknown")
            long_name = quest.get("long_name", quest_name)
            episode = quest.get("episode", 1)
            enemies = quest.get("enemies", {})

            # Determine if RBR should be active for this specific quest
            quest_rbr_active = False
            if rbr_active:
                # RBR active for all quests
                quest_rbr_active = True
            elif rbr_list_lower:
                # RBR only for quests in the list
                quest_rbr_active = quest_name.lower() in rbr_list_lower

            # Calculate quest-specific boost multipliers and rare enemy rates
            dar_multiplier, rdr_multiplier, enemy_rate_multiplier = self._calculate_boost_multipliers(
                quest, quest_rbr_active, weekly_boost, event_type
            )
            rare_enemy_rate, kondrieu_rate = self._calculate_rare_enemy_rates(enemy_rate_multiplier)

            # Normalize quest enemy names from non-Ultimate to Ultimate names
            normalized_enemies = self._normalize_quest_enemies(enemies)
            rare_mapping = self._get_rare_enemy_mapping(episode)

            # Process enemies per area if quest has areas, otherwise process globally
            quest_areas = quest.get("areas", [])
            
            if quest_areas:
                # Process enemies per area
                for area in quest_areas:
                    area_name = area.get("name", "")
                    area_enemies = area.get("enemies", {})
                    if not area_enemies:
                        area_enemies = normalized_enemies
                    
                    # Normalize area enemies
                    normalized_area_enemies = self._normalize_quest_enemies(area_enemies)
                    
                    # Process each section ID for this area
                    for section_id_enum in SectionIds:
                        section_id: str = section_id_enum.value
                        total_prob = 0.0
                        contributions = []
                        
                        for enemy_name, count in normalized_area_enemies.items():
                            # Check if this enemy can spawn as a rare variant
                            rare_variant = rare_mapping.get(enemy_name)

                            if rare_variant:
                                # Special case: Kondrieu uses 1/10 base rate
                                if rare_variant == "Kondrieu":
                                    normal_count = count * (1.0 - kondrieu_rate)
                                    rare_count = count * kondrieu_rate
                                else:
                                    # Normal rare enemy rate calculation
                                    normal_count = count * (1.0 - rare_enemy_rate)
                                    rare_count = count * rare_enemy_rate

                                # Process normal version
                                normal_prob, normal_contrib = self._get_enemy_weapon_drop_prob(
                                    enemy_name, normal_count, episode, section_id, dar_multiplier, rdr_multiplier, weapon_name, area_name, event_type
                                )
                                if normal_prob > 0:
                                    total_prob += normal_prob
                                    contributions.extend(normal_contrib)

                                # Process rare version
                                rare_prob, rare_contrib = self._get_enemy_weapon_drop_prob(
                                    rare_variant, rare_count, episode, section_id, dar_multiplier, rdr_multiplier, weapon_name, area_name, event_type
                                )
                                if rare_prob > 0:
                                    total_prob += rare_prob
                                    contributions.extend(rare_contrib)
                            else:
                                # No rare variant, process normally
                                enemy_prob, enemy_contrib = self._get_enemy_weapon_drop_prob(
                                    enemy_name, count, episode, section_id, dar_multiplier, rdr_multiplier, weapon_name, area_name, event_type
                                )
                                if enemy_prob > 0:
                                    total_prob += enemy_prob
                                    contributions.extend(enemy_contrib)
                        
                        # Check box drops for this area
                        boxes = area.get("boxes", {})
                        if boxes:
                            box_prob, box_contrib = self._get_box_item_drop_prob(
                                area_name, boxes, episode, section_id, weapon_name
                            )
                            if box_prob > 0:
                                total_prob += box_prob
                                contributions.extend(box_contrib)
                        
                        if total_prob > 0:
                            results.append(
                                {
                                    "quest_name": quest_name,
                                    "long_name": long_name,
                                    "section_id": section_id,
                                    "probability": total_prob,
                                    "percentage": total_prob * 100,
                                    "contributions": contributions,
                                }
                            )
            else:
                # No areas defined, process enemies globally
                for section_id_enum in SectionIds:
                    section_id: str = section_id_enum.value
                    total_prob = 0.0
                    contributions = []
                    
                    for enemy_name, count in normalized_enemies.items():
                        # Determine area for this enemy (for techniques)
                        area_name = self._determine_drop_area(enemy_name, episode)
                        
                        # Check if this enemy can spawn as a rare variant
                        rare_variant = rare_mapping.get(enemy_name)

                        if rare_variant:
                            # Special case: Kondrieu uses 1/10 base rate
                            if rare_variant == "Kondrieu":
                                normal_count = count * (1.0 - kondrieu_rate)
                                rare_count = count * kondrieu_rate
                            else:
                                # Normal rare enemy rate calculation
                                normal_count = count * (1.0 - rare_enemy_rate)
                                rare_count = count * rare_enemy_rate

                            # Process normal version
                            normal_prob, normal_contrib = self._get_enemy_weapon_drop_prob(
                                enemy_name, normal_count, episode, section_id, dar_multiplier, rdr_multiplier, weapon_name, area_name, event_type
                            )
                            if normal_prob > 0:
                                total_prob += normal_prob
                                contributions.extend(normal_contrib)

                            # Process rare version
                            rare_prob, rare_contrib = self._get_enemy_weapon_drop_prob(
                                rare_variant, rare_count, episode, section_id, dar_multiplier, rdr_multiplier, weapon_name, area_name, event_type
                            )
                            if rare_prob > 0:
                                total_prob += rare_prob
                                contributions.extend(rare_contrib)
                        else:
                            # No rare variant, process normally
                            enemy_prob, enemy_contrib = self._get_enemy_weapon_drop_prob(
                                enemy_name, count, episode, section_id, dar_multiplier, rdr_multiplier, weapon_name, area_name, event_type
                            )
                            if enemy_prob > 0:
                                total_prob += enemy_prob
                                contributions.extend(enemy_contrib)
                    
                    # Check box drops
                    quest_areas_global = quest.get("areas", [])
                    for area in quest_areas_global:
                        area_name = area.get("name", "")
                        boxes = area.get("boxes", {})
                        if boxes:
                            box_prob, box_contrib = self._get_box_item_drop_prob(
                                area_name, boxes, episode, section_id, weapon_name
                            )
                            if box_prob > 0:
                                total_prob += box_prob
                                contributions.extend(box_contrib)
                    
                    if total_prob > 0:
                        results.append(
                            {
                                "quest_name": quest_name,
                                "long_name": long_name,
                                "section_id": section_id,
                                "probability": total_prob,
                                "percentage": total_prob * 100,
                                "contributions": contributions,
                            }
                        )
                    # Check if this enemy can spawn as a rare variant
                    rare_variant = rare_mapping.get(enemy_name)

                    if rare_variant:
                        # Special case: Kondrieu uses 1/10 base rate
                        if rare_variant == "Kondrieu":
                            normal_count = count * (1.0 - kondrieu_rate)
                            rare_count = count * kondrieu_rate
                        else:
                            # Normal rare enemy rate calculation
                            normal_count = count * (1.0 - rare_enemy_rate)
                            rare_count = count * rare_enemy_rate

                        # Process normal version - need area context for techniques and common weapon drops.
                        # Determine area from quest structure or enemy default
                        area_name = None
                        quest_areas = quest.get("areas", [])
                        if quest_areas:
                            # Use first area as default (or find area with this enemy)
                            area_name = quest_areas[0].get("name", "")
                            # Try to find area that contains this enemy
                            for area in quest_areas:
                                area_enemies = area.get("enemies", {})
                                if enemy_name in area_enemies or self._normalize_quest_enemy_to_ultimate(enemy_name) in area_enemies:
                                    area_name = area.get("name", "")
                                    break
                        else:
                            # Fall back to determining area from enemy
                            area_name = self._determine_drop_area(enemy_name, episode)
                        
                        normal_prob, normal_contrib = self._get_enemy_weapon_drop_prob(
                            enemy_name, normal_count, episode, section_id, dar_multiplier, rdr_multiplier, weapon_name, area_name, event_type
                        )
                        if normal_prob > 0:
                            total_prob += normal_prob
                            contributions.extend(normal_contrib)

                        # Process rare version
                        rare_prob, rare_contrib = self._get_enemy_weapon_drop_prob(
                            rare_variant, rare_count, episode, section_id, dar_multiplier, rdr_multiplier, weapon_name, area_name, event_type
                        )
                        if rare_prob > 0:
                            total_prob += rare_prob
                            contributions.extend(rare_contrib)
                    else:
                        # No rare variant, process normally - need area context for techniques
                        area_name = None
                        quest_areas = quest.get("areas", [])
                        if quest_areas:
                            # Use first area as default (or find area with this enemy)
                            area_name = quest_areas[0].get("name", "")
                            # Try to find area that contains this enemy
                            for area in quest_areas:
                                area_enemies = area.get("enemies", {})
                                if enemy_name in area_enemies or self._normalize_quest_enemy_to_ultimate(enemy_name) in area_enemies:
                                    area_name = area.get("name", "")
                                    break
                        else:
                            # Fall back to determining area from enemy
                            area_name = self._determine_drop_area(enemy_name, episode)
                        
                        enemy_prob, enemy_contrib = self._get_enemy_weapon_drop_prob(
                            enemy_name, count, episode, section_id, dar_multiplier, rdr_multiplier, weapon_name, area_name, event_type
                        )
                        if enemy_prob > 0:
                            total_prob += enemy_prob
                            contributions.extend(enemy_contrib)

                # Check box drops
                quest_areas = quest.get("areas", [])
                for area in quest_areas:
                    area_name = area.get("name", "")
                    boxes = area.get("boxes", {})
                    if boxes:
                        box_prob, box_contrib = self._get_box_item_drop_prob(
                            area_name, boxes, episode, section_id, weapon_name
                        )
                        if box_prob > 0:
                            total_prob += box_prob
                            contributions.extend(box_contrib)

                if total_prob > 0:
                    results.append(
                        {
                            "quest_name": quest_name,
                            "long_name": long_name,
                            "section_id": section_id,
                            "probability": total_prob,
                            "percentage": total_prob * 100,
                            "contributions": contributions,
                        }
                    )

        # Sort by probability (highest first)
        results.sort(key=lambda x: x["probability"], reverse=True)

        return results

    def find_enemies_that_drop_weapon(
        self,
        weapon_name: str,
        rbr_active: bool = False,
        rbr_list: Optional[List[str]] = None,
        weekly_boost: Optional[WeeklyBoost] = None,
        event_type: Optional[EventType] = None,
    ) -> List[Dict]:
        """
        Find all enemies that drop the weapon and their drop rates.
        Also handles level 30 technique drops.

        Args:
            weapon_name: Name of the weapon/technique to search for
            rbr_active: Whether RBR boost is active for all quests
            rbr_list: Optional list of quest short names to apply RBR boost to (mutually exclusive with rbr_active)
            weekly_boost: Type of weekly boost (WeeklyBoost enum or None)
            event_type: Type of active event (EventType enum or None)

        Returns:
            List of enemy drop information, each containing:
            - enemy: Enemy name
            - episode: Episode number
            - section_id: Section ID that drops the weapon (None for techniques)
            - area: Area where technique can drop (for techniques)
            - dar: Base Drop Anything Rate
            - adjusted_dar: Adjusted DAR (with multipliers)
            - rdr: Base Rare Drop Rate (0.0 for techniques)
            - adjusted_rdr: Adjusted RDR (with multipliers, 0.0 for techniques)
            - drop_rate: Final drop rate per kill
            - item: Item name from drop table
        """
        # Check if this is a level 30 technique
        technique_name = self._is_technique_lv30(weapon_name)
        if technique_name:
            # Search for technique drops
            results = []
            
            # Calculate boost multipliers
            # Apply RBR if rbr_active is True or rbr_list is provided (non-empty)
            dar_multiplier = 1.0
            if rbr_active or (rbr_list and len(rbr_list) > 0):
                dar_multiplier *= 1.0 + RBR_DAR_BOOST
            
            # Apply weekly boosts (doubled if Christmas event is active)
            christmas_multiplier = 2.0 if event_type == EventType.Christmas else 1.0
            if weekly_boost == WeeklyBoost.DAR:
                dar_multiplier *= 1.0 + (WEEKLY_DAR_BOOST * christmas_multiplier)
            
            # Search through all quests to find enemies in eligible areas
            seen = set()
            for quest in self.quest_data:
                episode = quest.get("episode", 1)
                quest_areas = quest.get("areas", [])
                
                # Process enemies per area
                for area in quest_areas:
                    area_name = area.get("name", "")
                    if not self._is_area_eligible_for_technique(area_name, technique_name):
                        continue
                    
                    area_enemies = area.get("enemies", {})
                    if not area_enemies:
                        area_enemies = quest.get("enemies", {})
                    
                    for enemy_name, count in area_enemies.items():
                        # Normalize enemy name
                        ultimate_name = self._normalize_quest_enemy_to_ultimate(enemy_name)
                        
                        # Find enemy in drop table
                        enemy_data = self._find_enemy_in_drop_table(ultimate_name, episode)
                        if not enemy_data:
                            continue
                        
                        dar = enemy_data.get("dar", 0.0)
                        adjusted_dar = self._adjust_dar(dar, dar_multiplier)
                        technique_rates = self._calculate_technique_drop_rate(event_type, area_name)
                        
                        if technique_name in technique_rates:
                            conditional_rate = technique_rates[technique_name]
                            # Multiply by DAR to get actual drop rate
                            technique_rate = adjusted_dar * conditional_rate
                            
                            # Use a key to avoid duplicates
                            key = (ultimate_name, episode, area_name)
                            if key not in seen:
                                seen.add(key)
                                results.append(
                                    {
                                        "enemy": ultimate_name,
                                        "episode": episode,
                                        "section_id": None,  # Techniques don't depend on Section ID
                                        "area": area_name,
                                        "dar": dar,
                                        "adjusted_dar": adjusted_dar,
                                        "rdr": 0.0,
                                        "adjusted_rdr": 0.0,
                                        "drop_rate": technique_rate,
                                        "drop_rate_percent": technique_rate * 100,
                                        "item": f"{technique_name} Lv30",
                                    }
                                )
            
            # Sort by drop rate (highest first)
            results.sort(key=lambda x: x["drop_rate"], reverse=True)
            return results

        # Regular weapon drop logic
        # Calculate boost multipliers
        # Apply RBR if rbr_active is True or rbr_list is provided (non-empty)
        dar_multiplier = 1.0
        rdr_multiplier = 1.0

        if rbr_active or (rbr_list and len(rbr_list) > 0):
            dar_multiplier *= 1.0 + RBR_DAR_BOOST
            rdr_multiplier *= 1.0 + RBR_RDR_BOOST

        # Apply weekly boosts (doubled if Christmas event is active)
        christmas_multiplier = 2.0 if event_type == EventType.Christmas else 1.0

        if weekly_boost == WeeklyBoost.DAR:
            dar_multiplier *= 1.0 + (WEEKLY_DAR_BOOST * christmas_multiplier)
        elif weekly_boost == WeeklyBoost.RDR:
            rdr_multiplier *= 1.0 + (WEEKLY_RDR_BOOST * christmas_multiplier)

        results = []

        # Track unique enemy/section_id combinations
        seen = set()

        for episode_key in ["episode1", "episode2", "episode4"]:
            if episode_key not in self.drop_data:
                continue

            episode_num = int(episode_key.replace("episode", ""))
            enemies = self.drop_data[episode_key].get("enemies", {})

            for enemy_name, enemy_data in enemies.items():
                dar = enemy_data.get("dar", 0.0)
                section_ids_data = enemy_data.get("section_ids", {})

                for section_id_enum in SectionIds:
                    section_id: str = section_id_enum.value
                    section_drops = section_ids_data.get(section_id)
                    if not section_drops:
                        continue

                    item_name = section_drops.get("item", "")
                    rdr = section_drops.get("rdr", 0.0)

                    if self._weapon_matches(item_name, weapon_name):
                        # Apply multipliers (cap DAR at 1.0)
                        adjusted_dar = self._adjust_dar(dar, dar_multiplier)
                        adjusted_rdr = rdr * rdr_multiplier
                        drop_rate = adjusted_dar * adjusted_rdr

                        # Use a key to avoid duplicates
                        key = (enemy_name, episode_num, section_id)
                        if key not in seen:
                            seen.add(key)
                            results.append(
                                {
                                    "enemy": enemy_name,
                                    "episode": episode_num,
                                    "section_id": section_id,
                                    "dar": dar,
                                    "adjusted_dar": adjusted_dar,
                                    "rdr": rdr,
                                    "adjusted_rdr": adjusted_rdr,
                                    "drop_rate": drop_rate,
                                    "drop_rate_percent": drop_rate * 100,
                                    "item": item_name,
                                }
                            )

        # Sort by drop rate (highest first)
        results.sort(key=lambda x: x["drop_rate"], reverse=True)

        return results

    def find_boxes_that_drop_weapon(
        self,
        weapon_name: str,
    ) -> List[Dict]:
        """
        Find all boxes that drop the weapon and their drop rates.
        Also handles level 30 technique drops.

        Note: Box drops are NOT affected by DAR, RDR, or any other drop rate bonuses.
        They use the base drop rate directly from the drop table.

        Args:
            weapon_name: Name of the weapon/technique to search for

        Returns:
            List of box drop information, each containing:
            - area: Area name
            - episode: Episode number
            - section_id: Section ID that drops the weapon (None for techniques)
            - drop_rate: Base drop rate per box
            - drop_rate_percent: Drop rate as percentage
            - item: Item name from drop table
        """
        # Check if this is a level 30 technique
        technique_name = self._is_technique_lv30(weapon_name)
        if technique_name:
            # Search for technique drops from boxes
            results = []
            seen = set()
            
            # Search through all quests to find boxes in eligible areas
            for quest in self.quest_data:
                episode = quest.get("episode", 1)
                quest_areas = quest.get("areas", [])
                
                for area in quest_areas:
                    area_name = area.get("name", "")
                    if not self._is_area_eligible_for_technique(area_name, technique_name):
                        continue
                    
                    boxes = area.get("boxes", {})
                    regular_box_count = boxes.get("box", 0)
                    if regular_box_count == 0:
                        continue
                    
                    # Get total rare drop rate from boxes in this area
                    mapped_area = self.quest_listing.map_quest_area_to_drop_table_area(area_name)
                    episode_key = f"episode{episode}"
                    if episode_key in self.drop_data:
                        boxes_data = self.drop_data[episode_key].get("boxes", {})
                        if mapped_area in boxes_data:
                            technique_rates = self._calculate_box_technique_drop_rate(area_name)
                            
                            if technique_name in technique_rates:
                                technique_rate = technique_rates[technique_name]
                                
                                # Use a key to avoid duplicates
                                key = (area_name, episode)
                                if key not in seen:
                                    seen.add(key)
                                    results.append(
                                        {
                                            "area": area_name,
                                            "episode": episode,
                                            "section_id": None,  # Techniques don't depend on Section ID
                                            "drop_rate": technique_rate,
                                            "drop_rate_percent": technique_rate * 100,
                                            "item": f"{technique_name} Lv30",
                                        }
                                    )
                            break
            
            # Sort by drop rate (highest first)
            results.sort(key=lambda x: x["drop_rate"], reverse=True)
            return results

        # Regular weapon drop logic
        results = []

        # Track unique area/episode/section_id combinations
        seen = set()

        for episode_key in ["episode1", "episode2", "episode4"]:
            if episode_key not in self.drop_data:
                continue

            episode_num = int(episode_key.replace("episode", ""))
            boxes_data = self.drop_data[episode_key].get("boxes", {})

            for area_name, area_data in boxes_data.items():
                section_ids_data = area_data.get("section_ids", {})

                for section_id_enum in SectionIds:
                    section_id: str = section_id_enum.value
                    box_items = section_ids_data.get(section_id, [])

                    for item_data in box_items:
                        item_name = item_data.get("item", "")
                        drop_rate = item_data.get("rate", 0.0)

                        if self._weapon_matches(item_name, weapon_name):
                            # Use a key to avoid duplicates
                            key = (area_name, episode_num, section_id)
                            if key not in seen:
                                seen.add(key)
                                results.append(
                                    {
                                        "area": area_name,
                                        "episode": episode_num,
                                        "section_id": section_id,
                                        "drop_rate": drop_rate,
                                        "drop_rate_percent": drop_rate * 100,
                                        "item": item_name,
                                    }
                                )

        # Sort by drop rate (highest first)
        results.sort(key=lambda x: x["drop_rate"], reverse=True)

        return results
