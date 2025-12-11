"""
Quest value calculator for RBR quests.

Calculates expected PD value per quest by:
1. Cross-referencing quest enemy counts with drop tables
2. Applying RBR and weekly boost multipliers
3. Looking up item values from price guide
4. Calculating total expected PD value
"""

import json
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from drop_tables.weapon_patterns import (
    PATTERN_ATTRIBUTE_PROBABILITIES,
    _calculate_weapon_attributes,
)
from price_guide import (
    PriceGuideExceptionItemNameNotFound,
    PriceGuideFixed,
)


class WeeklyBoost(Enum):
    DAR = "DAR"  # Drop Anything Rate
    RDR = "RDR"  # Rare Drop Rate
    RareEnemy = "RareEnemy"  # Rare Enemy Appearance Rate
    XP = "XP"  # Experience Rate


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

# Slime splitting technique
SLIME_SPLIT = True  # Enable slime splitting (each slime counts as 8)
SLIME_SPLIT_MULTIPLIER = 8  # Each slime can be split into 8 slimes

# Map of normal enemies to their rare variants (Ultimate only)
RARE_ENEMY_MAPPING = {
    "El Rappy": "Pal Rappy",
    "Hildelt": "Hildetorr",
    "Ob Lily": "Mil Lily",
    "Pofuilly Slime": "Pouilly Slime",
    "Rag Rappy": "Love Rappy",
    "Dorphon": "Dorphon Eclair",
    "Sand Rappy": "Del Rappy",
    "Zu": "Pazuzu",
    "Merissa A": "Merissa AA",
    "Saint-Milion": "Kondrieu",
    "Shambertin": "Kondrieu",
}


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
        self.quest_data = self._load_quest_data(quest_data_path)

    def _load_drop_table(self, drop_table_path: Path) -> Dict:
        """Load drop table JSON file."""
        with open(drop_table_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_quest_data(self, quest_data_path: Path) -> List[Dict]:
        """Load quests.json file."""
        with open(quest_data_path, "r", encoding="utf-8") as f:
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
        return quest_data.get("in_rbr_rotation", False)

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
        # Note: calculate_rare_weapon_attributes doesn't take drop_area, but _calculate_weapon_attributes needs it
        # So we need to call the internal function directly with drop_area for hit probability
        attr_results = _calculate_weapon_attributes(weapon_data, drop_area=drop_area)

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

        # Calculate hit contribution (multiply Pattern 5 prob by hit prices)
        hit_values = weapon_data.get("hit_values", {})
        if hit_values and "hit" in attr_results:
            sorted_hits = sorted(map(int, hit_values.keys()))
            from bisect import bisect

            for hit_val, pattern5_prob in PATTERN_ATTRIBUTE_PROBABILITIES[5].items():
                index = bisect(sorted_hits, hit_val) - 1
                if index >= 0:
                    threshold = sorted_hits[index]
                    price_range = hit_values[str(threshold)]
                    try:
                        hit_price = PriceGuideFixed.get_price_from_range(price_range, self.price_guide.bps)
                        # The attr_results["hit"] already includes the probability that hit is assigned
                        # We need to multiply by Pattern 5 prob for this specific hit value
                        # Actually, attr_results["hit"] is the probability hit is assigned * 1.0
                        # So we need to multiply by pattern5_prob and hit_price
                        total_value += attr_results["hit"] * pattern5_prob * hit_price
                    except Exception:
                        pass

        return total_value

    def _calculate_common_weapon_value(self, weapon_data: Dict, base_price: float, drop_area: Optional[str] = None) -> float:
        """Calculate expected value for common weapon using area-specific patterns."""
        # TODO: Implement common weapon pattern calculation
        # For now, return base price
        return base_price

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

        # Frames (need addition, max_addition, slot - use defaults)
        try:
            return self.price_guide.get_price_frame(item_name, {}, {}, 0)
        except PriceGuideExceptionItemNameNotFound:
            pass

        # Barriers (need addition, max_addition - use defaults)
        try:
            return self.price_guide.get_price_barrier(item_name, {}, {})
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
        "Mil Lily": "Nar  Lily",
        "Pofuilly Slime": "Pofuilly Slime",
        "Pouilly Slime": "Pouilly Slime",
        "Nano Dragon": "Nano Dragon",
        "Pan Arms": "Pan Arms",
        "Crimson Assassin": "Grass Assassin",
        "Dal Ra Lie": "De Rol Le",
        # Episode 1 - Mines
        "Dubchich": "Gillchich",
        "Canabin": "Canadine",
        "Canune": "Canane",
        "Sinow Red": "Sinow Blue",
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
        # Episode 2
        "Meriltas": "Merillia",
        "Zol Gibbon": "Ul Gibbon",
        "Sinow Spigell": "Sinow Berill",
        "Merikle": "Mericarol",
        "Mericus": "Mericarol",
        "Dolmdarl": "Dolmolm",
        "Recon": "Recobox",
        "Sinow Zele": "Sinow Zoa",
        "Del Lily": "Ill Gill",
        # Episode 4
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

    def _process_enemy_drops(
        self, enemy_name: str, count: float, episode: int, section_id: str, dar_multiplier: float, rdr_multiplier: float
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

        if not enemy_data:
            enemy_breakdown[enemy_name] = {"count": count, "pd_value": 0.0, "error": "Enemy not found in drop table"}
            dar = 0.0
            adjusted_dar = 0.0
        else:
            # Get DAR and drop data for this Section ID
            dar = enemy_data.get("dar", 0.0)
            section_ids_data = enemy_data.get("section_ids", {})

            # Apply DAR multiplier, but cap at 1.0
            adjusted_dar = min(dar * dar_multiplier, 1.0)

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
            drop_area = self._determine_drop_area(enemy_name, episode)

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

        return total_pd, total_pd_drops, enemy_breakdown, pd_drop_breakdown

    def calculate_quest_value(
        self, quest_data: Dict, section_id: str, rbr_active: bool = False, weekly_boost: Optional[WeeklyBoost] = None
    ) -> Dict:
        """
        Calculate expected PD value for a quest.

        Args:
            quest_data: Quest JSON data with enemy counts
            section_id: Section ID to use for drops
            rbr_active: Whether RBR boost is active
            weekly_boost: Type of weekly boost (WeeklyBoost enum or None)

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

        # Calculate boost multipliers
        dar_multiplier = 1.0
        rdr_multiplier = 1.0
        enemy_rate_multiplier = 1.0

        # Check if this is a Hallow quest (uses Halloween boosts instead of weekly boosts)
        is_hallow = self._is_hallow_quest(quest_data)
        # Check if quest is in RBR rotation (RBR boosts only apply if in rotation)
        in_rbr_rotation = self._is_in_rbr_rotation(quest_data)

        if is_hallow:
            # Hallow quests use Halloween boosts (ignore weekly_boost parameter)
            dar_multiplier = 1.0 + HOLLOWEEN_QUEST_DAR_BOOST
            rdr_multiplier = 1.0 + HOLLOWEEN_QUEST_RDR_BOOST
            enemy_rate_multiplier = 1.0 + HOLLOWEEN_QUEST_RARE_ENEMY_BOOST

            # RBR boosts only apply if quest is in RBR rotation
            if in_rbr_rotation and rbr_active:
                dar_multiplier *= 1.0 + RBR_DAR_BOOST
                rdr_multiplier *= 1.0 + RBR_RDR_BOOST
                enemy_rate_multiplier *= 1.0 + RBR_ENEMY_RATE_BOOST
        else:
            # Regular quests use RBR and weekly boosts
            if in_rbr_rotation and rbr_active:
                dar_multiplier *= 1.0 + RBR_DAR_BOOST
                rdr_multiplier *= 1.0 + RBR_RDR_BOOST
                enemy_rate_multiplier *= 1.0 + RBR_ENEMY_RATE_BOOST

            if weekly_boost == WeeklyBoost.DAR:
                dar_multiplier *= 1.0 + WEEKLY_DAR_BOOST
            elif weekly_boost == WeeklyBoost.RDR:
                rdr_multiplier *= 1.0 + WEEKLY_RDR_BOOST
            elif weekly_boost == WeeklyBoost.RareEnemy:
                enemy_rate_multiplier *= 1.0 + WEEKLY_ENEMY_RATE_BOOST

        # Let's sub rare enemies in here.

        # Calculate rare enemy spawn rate with boosts
        # Note: Kondrieu has a fixed 1/10 rate (not affected by boosts) - handled separately
        rare_enemy_rate = BASE_RARE_ENEMY_RATE * enemy_rate_multiplier
        kondrieu_rate = RARE_ENEMY_RATE_KONDRIEU * enemy_rate_multiplier

        # Cap at reasonable maximum (e.g., 1/256 = ~0.39%)
        rare_enemy_rate = min(rare_enemy_rate, 1.0 / 256.0)
        kondrieu_rate = min(kondrieu_rate, 1.0)

        # Slime enemies that can be split
        SLIME_ENEMIES = ["Pofuilly Slime", "Pouilly Slime"]

        # Process each enemy
        for enemy_name, count in enemies.items():
            # Apply slime splitting if enabled
            if SLIME_SPLIT and enemy_name in SLIME_ENEMIES:
                count = count * SLIME_SPLIT_MULTIPLIER

            total_enemies += count

            # Check if this enemy can spawn as a rare variant
            rare_variant = RARE_ENEMY_MAPPING.get(enemy_name)

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
                    enemy_name, normal_count, episode, section_id, dar_multiplier, rdr_multiplier
                )

                # Process rare version
                rare_pd, rare_pd_drops, rare_breakdown, rare_pd_breakdown = self._process_enemy_drops(
                    rare_variant, rare_count, episode, section_id, dar_multiplier, rdr_multiplier
                )

                # Combine results
                total_pd += normal_pd + rare_pd
                total_pd_drops += normal_pd_drops + rare_pd_drops

                # Merge breakdowns - include both normal and rare as separate entries
                if normal_breakdown and enemy_name in normal_breakdown:
                    normal_data = normal_breakdown[enemy_name].copy()
                    # Update count to reflect normal_count
                    normal_data["count"] = normal_count
                    enemy_breakdown[enemy_name] = normal_data

                # Add rare variant as separate entry if it exists
                if rare_breakdown and rare_variant in rare_breakdown:
                    rare_data = rare_breakdown[rare_variant].copy()
                    # Update count to reflect rare_count
                    rare_data["count"] = rare_count
                    enemy_breakdown[rare_variant] = rare_data

                # Merge PD drop breakdowns - include both normal and rare as separate entries
                if normal_pd_breakdown and enemy_name in normal_pd_breakdown:
                    normal_pd_data = normal_pd_breakdown[enemy_name]
                    # Update count to reflect normal_count
                    normal_pd_data["count"] = normal_count
                    pd_drop_breakdown[enemy_name] = normal_pd_data

                # Add rare variant as separate entry if it exists
                if rare_pd_breakdown and rare_variant in rare_pd_breakdown:
                    rare_pd_data = rare_pd_breakdown[rare_variant]
                    # Update count to reflect rare_count
                    rare_pd_data["count"] = rare_count
                    pd_drop_breakdown[rare_variant] = rare_pd_data
            else:
                # Process normally (no rare variant)
                normal_pd, normal_pd_drops, normal_breakdown, normal_pd_breakdown = self._process_enemy_drops(
                    enemy_name, count, episode, section_id, dar_multiplier, rdr_multiplier
                )

                total_pd += normal_pd
                total_pd_drops += normal_pd_drops

                if normal_breakdown:
                    enemy_breakdown.update(normal_breakdown)
                if normal_pd_breakdown:
                    pd_drop_breakdown.update(normal_pd_breakdown)

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

        return {
            "total_pd": total_pd,
            "total_pd_drops": total_pd_drops,  # Expected PD drops (not item value)
            "enemy_breakdown": enemy_breakdown,
            "pd_drop_breakdown": pd_drop_breakdown,
            "completion_items_breakdown": completion_items_breakdown,
            "completion_items_pd": completion_items_pd,
            "total_enemies": total_enemies,
            "section_id": section_id,
            "rbr_active": rbr_active,
            "weekly_boost": weekly_boost,
        }

    def calculate_all_section_ids(
        self, quest_data: Dict, rbr_active: bool = False, weekly_boost: Optional[WeeklyBoost] = None
    ) -> Dict[str, Dict]:
        """
        Calculate quest value for all Section IDs.

        Returns:
            Dictionary mapping Section ID to calculated values
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
            results[section_id] = self.calculate_quest_value(quest_data, section_id, rbr_active, weekly_boost)

        return results

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
    ) -> Tuple[float, List[Dict]]:
        """
        Get drop probability for a weapon from a specific enemy.

        Returns:
            Tuple of (total_probability, list of contributions)
        """
        contributions = []
        total_prob = 0.0

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
            adjusted_dar = min(dar * dar_multiplier, 1.0)
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

    def find_best_quests_for_weapon(
        self,
        weapon_name: str,
        rbr_active: bool = False,
        weekly_boost: Optional[WeeklyBoost] = None,
        quest_filter: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Find all quest/Section ID combinations that drop the weapon, sorted by probability.

        Args:
            weapon_name: Name of the weapon to search for
            rbr_active: Whether RBR boost is active
            weekly_boost: Type of weekly boost (WeeklyBoost enum or None)
            quest_filter: Optional list of quest names to filter to (case-insensitive)

        Returns:
            List of results, each containing:
            - quest_name: Quest ID
            - long_name: Quest full name
            - section_id: Section ID
            - probability: Total drop probability per quest run
            - percentage: Drop probability as percentage
            - contributions: List of enemy contributions
        """
        # Base multipliers (will be adjusted per quest based on in_rbr_rotation field)

        results = []
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

            # Calculate quest-specific boost multipliers
            is_hallow = self._is_hallow_quest(quest)
            in_rbr_rotation = self._is_in_rbr_rotation(quest)

            if is_hallow:
                # Hallow quests use Halloween boosts (ignore weekly_boost parameter)
                dar_multiplier = 1.0 + HOLLOWEEN_QUEST_DAR_BOOST
                rdr_multiplier = 1.0 + HOLLOWEEN_QUEST_RDR_BOOST
                enemy_rate_multiplier = 1.0 + HOLLOWEEN_QUEST_RARE_ENEMY_BOOST

                # RBR boosts only apply if quest is in RBR rotation
                if in_rbr_rotation and rbr_active:
                    dar_multiplier *= 1.0 + RBR_DAR_BOOST
                    rdr_multiplier *= 1.0 + RBR_RDR_BOOST
                    enemy_rate_multiplier *= 1.0 + RBR_ENEMY_RATE_BOOST
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

                if weekly_boost == WeeklyBoost.DAR:
                    dar_multiplier *= 1.0 + WEEKLY_DAR_BOOST
                elif weekly_boost == WeeklyBoost.RDR:
                    rdr_multiplier *= 1.0 + WEEKLY_RDR_BOOST
                if weekly_boost == WeeklyBoost.RareEnemy:
                    enemy_rate_multiplier *= 1.0 + WEEKLY_ENEMY_RATE_BOOST

            # Calculate rare enemy spawn rate for this quest
            rare_enemy_rate = BASE_RARE_ENEMY_RATE * enemy_rate_multiplier
            kondrieu_rate = RARE_ENEMY_RATE_KONDRIEU * enemy_rate_multiplier
            rare_enemy_rate = min(rare_enemy_rate, 1.0 / 256.0)
            kondrieu_rate = min(kondrieu_rate, 1.0)

            for section_id in section_ids:
                total_prob = 0.0
                contributions = []

                for enemy_name, count in enemies.items():
                    # Check if this enemy can spawn as a rare variant
                    rare_variant = RARE_ENEMY_MAPPING.get(enemy_name)

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
                            enemy_name, normal_count, episode, section_id, dar_multiplier, rdr_multiplier, weapon_name
                        )
                        if normal_prob > 0:
                            total_prob += normal_prob
                            contributions.extend(normal_contrib)

                        # Process rare version
                        rare_prob, rare_contrib = self._get_enemy_weapon_drop_prob(
                            rare_variant, rare_count, episode, section_id, dar_multiplier, rdr_multiplier, weapon_name
                        )
                        if rare_prob > 0:
                            total_prob += rare_prob
                            contributions.extend(rare_contrib)
                    else:
                        # No rare variant, process normally
                        enemy_prob, enemy_contrib = self._get_enemy_weapon_drop_prob(
                            enemy_name, count, episode, section_id, dar_multiplier, rdr_multiplier, weapon_name
                        )
                        if enemy_prob > 0:
                            total_prob += enemy_prob
                            contributions.extend(enemy_contrib)

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
        self, weapon_name: str, rbr_active: bool = False, weekly_boost: Optional[WeeklyBoost] = None
    ) -> List[Dict]:
        """
        Find all enemies that drop the weapon and their drop rates.

        Args:
            weapon_name: Name of the weapon to search for
            rbr_active: Whether RBR boost is active
            weekly_boost: Type of weekly boost (WeeklyBoost enum or None)

        Returns:
            List of enemy drop information, each containing:
            - enemy: Enemy name
            - episode: Episode number
            - section_id: Section ID that drops the weapon
            - dar: Base Drop Anything Rate
            - adjusted_dar: Adjusted DAR (with multipliers)
            - rdr: Base Rare Drop Rate
            - adjusted_rdr: Adjusted RDR (with multipliers)
            - drop_rate: Final drop rate per kill (DAR * RDR)
            - item: Item name from drop table
        """
        # Calculate boost multipliers
        dar_multiplier = 1.0
        rdr_multiplier = 1.0

        if rbr_active:
            dar_multiplier *= 1.0 + RBR_DAR_BOOST
            rdr_multiplier *= 1.0 + RBR_RDR_BOOST

        if weekly_boost == WeeklyBoost.DAR:
            dar_multiplier *= 1.0 + WEEKLY_DAR_BOOST
        elif weekly_boost == WeeklyBoost.RDR:
            rdr_multiplier *= 1.0 + WEEKLY_RDR_BOOST

        results = []
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

                for section_id in section_ids:
                    section_drops = section_ids_data.get(section_id)
                    if not section_drops:
                        continue

                    item_name = section_drops.get("item", "")
                    rdr = section_drops.get("rdr", 0.0)

                    if self._weapon_matches(item_name, weapon_name):
                        # Apply multipliers (cap DAR at 1.0)
                        adjusted_dar = min(dar * dar_multiplier, 1.0)
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
