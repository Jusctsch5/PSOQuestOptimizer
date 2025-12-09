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

from price_guide import PriceGuideFixed, BasePriceStrategy
from drop_tables.weapon_patterns import (
    AREA_ATTRIBUTE_RATES,
    PATTERN_ATTRIBUTE_PROBABILITIES,
    PATTERN_5_HIT_PROBABILITIES,
    get_pattern_probability,
    get_pattern_probability_at_least,
    is_rare_weapon,
)


class WeeklyBoost(Enum):
    """Weekly boost types."""
    DAR = "DAR"  # Drop Anything Rate
    RDR = "RDR"  # Rare Drop Rate
    RareEnemy = "RareEnemy"  # Rare Enemy Appearance Rate
    XP = "XP"  # Experience Rate


# Boost multipliers

WEEKLY_DAR_BOOST = 0.25  # +25% Drop Anything Rate
WEEKLY_RDR_BOOST = 0.25  # +25% Rare Drop Rate
WEEKLY_ENEMY_RATE_BOOST = 0.50  # +50% to rare enemy drop rate

RBR_DAR_BOOST = 0.25  # +25% Drop Anything Rate
RBR_RDR_BOOST = 0.25  # +25% Rare Drop Rate
RBR_ENEMY_RATE_BOOST = 0.50  # +50% to rare enemy drop rate


# PD drop rate (fixed, not affected by RDR boosts)
BASE_PD_DROP_RATE = 1.0 / 375.0  # 1/375 chance for PD drop

BASE_RARE_ENEMY_RATE = 1.0 / 512  # 1/512 base chance for rare enemy spawn
RARE_ENEMY_RATE_KONDRIEU = 1.0 / 10  # 1/10 chance for rare enemy spawn as Kondrieu

# Slime splitting technique
SLIME_SPLIT = True  # Enable slime splitting (each slime counts as 8)
SLIME_SPLIT_MULTIPLIER = 8  # Each slime can be split into 8 slimes


class QuestCalculator:
    """Calculate quest values based on drop tables and price guide."""
    
    def __init__(self, drop_table_path: Path, price_guide_path: Path):
        """
        Initialize calculator with drop table and price guide paths.
        
        Args:
            drop_table_path: Path to drop_tables_ultimate.json
            price_guide_path: Path to price guide directory
        """
        self.drop_table_path = drop_table_path
        self.price_guide = PriceGuideFixed(str(price_guide_path))
        self.drop_data = self._load_drop_table()
    
    def _load_drop_table(self) -> Dict:
        """Load drop table JSON file."""
        with open(self.drop_table_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_weapon_expected_value(
        self,
        item_name: str,
        drop_area: str = None,
    ) -> float:
        """
        Calculate expected weapon value based on pattern probabilities.
        
        For rare weapons: Always uses Pattern 5 for all attributes.
        For common weapons: Uses area-specific patterns.
        
        Args:
            item_name: Name of the weapon
            drop_area: Area where weapon drops (for common weapons)
        
        Returns:
            Expected PD value
        """
        # Check if it's a rare weapon
        is_rare = item_name in self.price_guide.weapon_prices
        
        if not is_rare:
            # Check common weapons
            if item_name not in getattr(self.price_guide, 'common_weapon_prices', {}):
                return 0.0
            weapon_data = self.price_guide.common_weapon_prices.get(item_name, {})
        else:
            weapon_data = self.price_guide.weapon_prices.get(item_name, {})
        
        if not weapon_data:
            return 0.0
        
        # Get base price
        base_price_str = weapon_data.get("base")
        base_price = 0.0
        if base_price_str and base_price_str is not None:
            try:
                base_price = PriceGuideFixed.get_price_from_range(
                    base_price_str, self.price_guide.bps
                )
            except Exception:
                pass
        
        # For rare weapons, always use Pattern 5
        if is_rare:
            return self._calculate_rare_weapon_value(weapon_data, base_price, drop_area)
        else:
            # For common weapons, use area-specific patterns
            return self._calculate_common_weapon_value(weapon_data, base_price, drop_area)
    
    def _calculate_rare_weapon_value(self, weapon_data: Dict, base_price: float, drop_area: str = None) -> float:
        """Calculate expected value for rare weapon using Pattern 5."""
        from calculate_weapon_value import calculate_weapon_attributes
        
        total_value = base_price
        
        # Get Pattern 5 contributions (probabilities, not prices)
        attr_results = calculate_weapon_attributes(weapon_data, drop_area)
        
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
                    modifier_price = PriceGuideFixed.get_price_from_range(
                        modifiers[mod_key], self.price_guide.bps
                    )
                    total_value += attr_results[attr_name] * modifier_price
                except Exception:
                    pass
        
        # Calculate hit contribution (multiply Pattern 5 prob by hit prices)
        hit_values = weapon_data.get("hit_values", {})
        if hit_values and "hit" in attr_results:
            sorted_hits = sorted(map(int, hit_values.keys()))
            from bisect import bisect
            for hit_val, pattern5_prob in PATTERN_5_HIT_PROBABILITIES.items():
                index = bisect(sorted_hits, hit_val) - 1
                if index >= 0:
                    threshold = sorted_hits[index]
                    price_range = hit_values[str(threshold)]
                    try:
                        hit_price = PriceGuideFixed.get_price_from_range(
                            price_range, self.price_guide.bps
                        )
                        # The attr_results["hit"] already includes the probability that hit is assigned
                        # We need to multiply by Pattern 5 prob for this specific hit value
                        # Actually, attr_results["hit"] is the probability hit is assigned * 1.0
                        # So we need to multiply by pattern5_prob and hit_price
                        total_value += attr_results["hit"] * pattern5_prob * hit_price
                    except Exception:
                        pass
        
        return total_value
    
    def _calculate_common_weapon_value(
        self,
        weapon_data: Dict,
        base_price: float,
        drop_area: str = None
    ) -> float:
        """Calculate expected value for common weapon using area-specific patterns."""
        # TODO: Implement common weapon pattern calculation
        # For now, return base price
        return base_price
    
    def _get_item_price_pd(self, item_name: str, drop_area: str = None) -> float:
        """
        Get price for an item by searching all price categories.
        For weapons, calculates expected value based on patterns.
        Returns price in PD (price guide already returns PD values).
        """
        # Weapons - use pattern-based calculation
        if item_name in self.price_guide.weapon_prices:
            return self._get_weapon_expected_value(item_name, drop_area)
    
        # Units
        if item_name in self.price_guide.unit_prices:
            price_range = self.price_guide.unit_prices[item_name]["base"]
            return PriceGuideFixed.get_price_for_item_range(price_range, 1, self.price_guide.bps)
        
        # Tools
        if item_name in self.price_guide.tool_prices:
            price_range = self.price_guide.tool_prices[item_name]["base"]
            return PriceGuideFixed.get_price_for_item_range(price_range, 1, self.price_guide.bps)
        
        # Frames
        if item_name in self.price_guide.frame_prices:
            price_range = self.price_guide.frame_prices[item_name]["base"]
            return PriceGuideFixed.get_price_from_range(price_range, self.price_guide.bps)
        
        # Barriers
        if item_name in self.price_guide.barrier_prices:
            price_range = self.price_guide.barrier_prices[item_name]["base"]
            return PriceGuideFixed.get_price_from_range(price_range, self.price_guide.bps)
        
        # Mags (need level, default to 0)
        if item_name in self.price_guide.mag_prices:
            # Mags need level, but for drop tables we don't have that info
            # Use a default or skip
            return 0.0
        
        # Disks (default to level 30)
        if item_name in self.price_guide.disk_prices:
            return self.price_guide.get_price_disk(item_name, 30)
        
        # S-Rank weapons (need more info)
        # Skip for now as they require ability, grinder, element
        
        return 0.0
    
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
            forest_enemies = ['booma', 'gobooma', 'gigobooma', 'savage wolf', 'barbarous wolf', 
                            'rag rappy', 'al rappy', 'hildebear', 'mothmant']
            if normalized in forest_enemies or any(fe in enemy_lower for fe in forest_enemies):
                return "Forest 1"
            
            # Cave enemies
            cave_enemies = ['evil shark', 'pal shark', 'guil shark', 'poison lily', 'nar lily',
                          'pofuilly slime', 'grass assassin', 'nano dragon', 'pan arms']
            if normalized in cave_enemies or any(ce in enemy_lower for ce in cave_enemies):
                return "Cave 1"
            
            # Mine enemies
            mine_enemies = ['gillchich', 'canabin', 'sinow blue', 'garanz']
            if normalized in mine_enemies or any(me in enemy_lower for me in mine_enemies):
                return "Mine 1"
            
            # Ruins enemies
            ruins_enemies = ['dimenian', 'la dimenian', 'so dimenian', 'bulclaw', 'claw',
                           'dark gunner', 'delsaber', 'chaos sorcerer', 'dark belra',
                           'chaos bringer', 'dark falz']
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
        if '/' in enemy_name:
            parts = enemy_name.split('/')
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
        self,
        enemy_name: str,
        count: float,
        episode: int,
        section_id: str,
        dar_multiplier: float,
        rdr_multiplier: float
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
            enemy_breakdown[enemy_name] = {
                "count": count,
                "pd_value": 0.0,
                "error": "Enemy not found in drop table"
            }
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
                    "error": "Enemy has no item drops in Ultimate difficulty"
                }
            else:
                section_drops = section_ids_data.get(section_id)
                
                if not section_drops:
                    enemy_breakdown[enemy_name] = {
                        "count": count,
                        "pd_value": 0.0,
                        "error": f"No item drops for Section ID {section_id}"
                    }
        
        # Calculate PD drops for ALL enemies (DAR affects, but RDR is fixed at 1/375)
        expected_pd_drops = count * adjusted_dar * BASE_PD_DROP_RATE
        total_pd_drops += expected_pd_drops
        
        pd_drop_breakdown[enemy_name] = {
            "count": count,
            "dar": dar,
            "adjusted_dar": adjusted_dar,
            "pd_drop_rate": BASE_PD_DROP_RATE,
            "expected_pd_drops": expected_pd_drops
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
                "pd_value": expected_pd
            }
        
        return total_pd, total_pd_drops, enemy_breakdown, pd_drop_breakdown
    
    def calculate_quest_value(
        self,
        quest_data: Dict,
        section_id: str,
        rbr_active: bool = False,
        weekly_boost: Optional[WeeklyBoost] = None
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
        
        if rbr_active:
            dar_multiplier *= (1.0 + RBR_DAR_BOOST)
            rdr_multiplier *= (1.0 + RBR_RDR_BOOST)
            enemy_rate_multiplier *= (1.0 + RBR_ENEMY_RATE_BOOST)
        
        if weekly_boost == WeeklyBoost.DAR:
            dar_multiplier *= (1.0 + WEEKLY_DAR_BOOST)
        elif weekly_boost == WeeklyBoost.RDR:
            rdr_multiplier *= (1.0 + WEEKLY_RDR_BOOST)
        elif weekly_boost == WeeklyBoost.RareEnemy:
            enemy_rate_multiplier *= (1.0 + WEEKLY_ENEMY_RATE_BOOST)
        
        # Let's sub rare enemies in here.
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
                "total_pd": item_total_pd
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
            "weekly_boost": weekly_boost
        }
    
    def calculate_all_section_ids(
        self,
        quest_data: Dict,
        rbr_active: bool = False,
        weekly_boost: Optional[WeeklyBoost] = None
    ) -> Dict[str, Dict]:
        """
        Calculate quest value for all Section IDs.
        
        Returns:
            Dictionary mapping Section ID to calculated values
        """
        section_ids = [
            "Viridia", "Greenill", "Skyly", "Bluefull", "Purplenum",
            "Pinkal", "Redria", "Oran", "Yellowboze", "Whitill"
        ]
        
        results = {}
        for section_id in section_ids:
            results[section_id] = self.calculate_quest_value(
                quest_data, section_id, rbr_active, weekly_boost
            )
        
        return results


def load_quest(quest_path: Path) -> Dict:
    """Load quest JSON file."""
    with open(quest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    """Example usage of quest calculator."""
    base_path = Path(__file__).parent
    
    drop_table_path = base_path / "drop_tables" / "drop_tables_ultimate.json"
    price_guide_path = base_path.parent / "price_guide" / "data"
    quest_path = base_path / "quests" / "example_quest.json"
    
    if not drop_table_path.exists():
        print(f"Error: Drop table not found at {drop_table_path}")
        print("Please run drop_table_parser.py first to generate the drop table.")
        return
    
    if not price_guide_path.exists():
        print(f"Error: Price guide directory not found at {price_guide_path}")
        return
    
    if not quest_path.exists():
        print(f"Error: Quest file not found at {quest_path}")
        return
    
    # Initialize calculator
    calculator = QuestCalculator(drop_table_path, price_guide_path)
    
    # Load quest
    quest_data = load_quest(quest_path)
    
    # Calculate for one Section ID
    print(f"\nCalculating value for quest: {quest_data['quest_name']}")
    print(f"Episode: {quest_data['episode']}")
    print(f"Enemies: {quest_data['enemies']}\n")
    
    result = calculator.calculate_quest_value(
        quest_data,
        section_id="Redria",
        rbr_active=True,
        weekly_boost=WeeklyBoost.RDR
    )
    
    print(f"Total Expected PD: {result['total_pd']:.4f}")
    print(f"Total Enemies: {result['total_enemies']}")
    print(f"\nEnemy Breakdown:")
    for enemy, data in result['enemy_breakdown'].items():
        if 'error' in data:
            print(f"  {enemy}: {data['error']}")
        else:
            print(f"  {enemy}: {data['count']} enemies, {data['expected_drops']:.4f} expected drops, {data['pd_value']:.4f} PD")


if __name__ == "__main__":
    main()

