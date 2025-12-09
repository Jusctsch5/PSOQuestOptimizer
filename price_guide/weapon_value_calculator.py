"""
Calculate average weapon value based on drop location and attribute/hit patterns.

This module handles the probabilistic calculation of weapon values when dropped
from specific areas, taking into account:
- Area attribute probabilities (Native, A.Beast, Machine, Dark, Hit, No Attribute)
- Pattern value distributions (how many attributes roll and their value ranges)
- Price guide lookups for each possible combination
"""

from typing import Dict, List, Tuple, Optional, Any
from bisect import bisect


class WeaponValueCalculator:
    """
    Calculate expected weapon values by combining pattern probabilities with prices.
    
    This is the "connective tissue" that takes pattern probabilities from
    weapon_patterns.py and multiplies them by prices from price_guide.py.
    """
    
    def __init__(self, price_guide):
        """
        Initialize calculator with a price guide instance.
        
        Args:
            price_guide: PriceGuideAbstract instance for price lookups
        """
        self.price_guide = price_guide
    
    def calculate_weapon_expected_value(
        self,
        weapon_name: str,
        drop_area: Optional[str] = None,
    ) -> float:
        """
        Calculate expected weapon value based on pattern probabilities.
        
        For rare weapons: Always uses Pattern 5 for all attributes.
        For common weapons: Uses area-specific patterns.
        
        Args:
            weapon_name: Name of the weapon
            drop_area: Area where weapon drops (for hit probability calculation)
        
        Returns:
            Expected PD value
        """
        from drop_tables.weapon_patterns import calculate_weapon_attributes
        
        # Get weapon data
        weapon_key = weapon_name.upper()
        weapon_data = self.price_guide.weapon_prices.get(weapon_key)
        if not weapon_data:
            # Try case-insensitive lookup
            weapon_key = next(
                (key for key in self.price_guide.weapon_prices.keys() 
                    if key.upper() == weapon_name.upper()),
                None
            )
            if weapon_key:
                weapon_data = self.price_guide.weapon_prices[weapon_key]
            else:
                return 0.0
        
        if not weapon_data:
            return 0.0
        
        # Get base price
        base_price_str = weapon_data.get("base")
        base_price = 0.0
        if base_price_str and base_price_str is not None:
            base_price = self.price_guide.get_price_from_range(base_price_str, self.price_guide.bps)
        
        # For rare weapons, always use Pattern 5
        # Get Pattern 5 contributions (probabilities, not prices)
        attr_results = calculate_weapon_attributes(weapon_data, drop_area)
        
        # Calculate attribute contributions (multiply Pattern 5 prob by modifier price)
        attribute_contribution = self._calculate_attribute_contribution(weapon_data, attr_results)
        
        # Calculate hit contribution
        hit_contribution = self._calculate_hit_contribution(weapon_data, attr_results, drop_area)
        
        return base_price + attribute_contribution + hit_contribution
    
    def _calculate_attribute_contribution(
        self,
        weapon_data: Dict,
        attr_results: Dict[str, float],
    ) -> float:
        """
        Calculate expected attribute value contribution.
        
        Args:
            weapon_data: Weapon data from price guide
            attr_results: Results from calculate_weapon_attributes (probabilities)
        
        Returns:
            Expected attribute contribution in PD
        """
        modifiers = weapon_data.get("modifiers", {})
        attr_to_modifier = {
            "native": "N",
            "abeast": "AB",
            "machine": "M",
            "dark": "D",
        }
        
        attribute_contribution = 0.0
        for attr_name, mod_key in attr_to_modifier.items():
            if mod_key in modifiers and attr_name in attr_results:
                try:
                    modifier_price = self.price_guide.get_price_from_range(
                        modifiers[mod_key], self.price_guide.bps
                    )
                    attribute_contribution += attr_results[attr_name] * modifier_price
                except Exception:
                    pass
        
        return attribute_contribution
    
    def _calculate_hit_contribution(
        self,
        weapon_data: Dict,
        attr_results: Dict[str, float],
        drop_area: Optional[str] = None,
    ) -> float:
        """
        Calculate expected hit value contribution.
        
        Uses teched hit values (original + 10) for price lookups.
        
        Args:
            weapon_data: Weapon data from price guide
            attr_results: Results from calculate_weapon_attributes
            drop_area: Area where weapon drops (for hit probability)
        
        Returns:
            Expected hit contribution in PD
        """
        from drop_tables.weapon_patterns import (
            PATTERN_5_HIT_PROBABILITIES,
            get_three_roll_hit_probability,
        )
        
        hit_values = weapon_data.get("hit_values", {})
        if not hit_values or "hit" not in attr_results:
            return 0.0
        
        # Use three_roll_hit_probability to ensure probabilities sum correctly
        three_roll_hit_prob = get_three_roll_hit_probability(drop_area)
        
        # Calculate hit contribution by iterating through Pattern 5 hit values
        hit_contribution = 0.0
        sorted_hits = sorted(map(int, hit_values.keys()))
        
        for hit_val, pattern5_prob in PATTERN_5_HIT_PROBABILITIES.items():
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
                    hit_price = self.price_guide.get_price_from_range(price_range, self.price_guide.bps)
                    hit_contribution += hit_price * combined_prob
                except Exception:
                    pass
        
        return hit_contribution
    
    def get_weapon_value_breakdown(
        self,
        weapon_name: str,
        drop_area: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get detailed breakdown of weapon value calculation.
        
        Args:
            weapon_name: Name of the weapon
            drop_area: Area where weapon drops
        
        Returns:
            Dictionary with breakdown:
            {
                "base_price": float,
                "attribute_contribution": float,
                "hit_contribution": float,
                "total": float,
                "weapon_data": Dict,
                "attr_results": Dict,
                "hit_breakdown": List[Dict],
            }
        """
        from drop_tables.weapon_patterns import calculate_weapon_attributes
        
        # Get weapon data
        weapon_key = weapon_name.upper()
        weapon_data = self.price_guide.weapon_prices.get(weapon_key)
        if not weapon_data:
            weapon_key = next(
                (key for key in self.price_guide.weapon_prices.keys() 
                    if key.upper() == weapon_name.upper()),
                None
            )
            if weapon_key:
                weapon_data = self.price_guide.weapon_prices[weapon_key]
            else:
                return {
                    "base_price": 0.0,
                    "attribute_contribution": 0.0,
                    "hit_contribution": 0.0,
                    "total": 0.0,
                    "weapon_data": {},
                    "attr_results": {},
                    "hit_breakdown": [],
                }
        
        # Get base price
        base_price_str = weapon_data.get("base")
        base_price = 0.0
        if base_price_str and base_price_str is not None:
            base_price = self.price_guide.get_price_from_range(base_price_str, self.price_guide.bps)
        
        # Get attribute results (probabilities from weapon_patterns)
        attr_results = calculate_weapon_attributes(weapon_data, drop_area)
        
        # Calculate attribute contributions
        attribute_contribution = self._calculate_attribute_contribution(weapon_data, attr_results)
        
        # Calculate hit breakdown
        hit_breakdown = self._get_hit_breakdown(weapon_data, attr_results, drop_area)
        hit_contribution = sum(item["expected_value"] for item in hit_breakdown)
        
        return {
            "base_price": base_price,
            "attribute_contribution": attribute_contribution,
            "hit_contribution": hit_contribution,
            "total": base_price + attribute_contribution + hit_contribution,
            "weapon_data": weapon_data,
            "attr_results": attr_results,
            "hit_breakdown": hit_breakdown,
        }
    
    def _get_hit_breakdown(
        self,
        weapon_data: Dict,
        attr_results: Dict[str, float],
        drop_area: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get detailed breakdown of hit value contributions.
        
        Returns:
            List of dictionaries with hit value, probability, price, and expected value
        """
        from drop_tables.weapon_patterns import (
            PATTERN_5_HIT_PROBABILITIES,
            get_three_roll_hit_probability,
        )
        
        hit_values = weapon_data.get("hit_values", {})
        if not hit_values or "hit" not in attr_results:
            return []
        
        # Use three_roll_hit_probability to ensure probabilities sum correctly
        three_roll_hit_prob = get_three_roll_hit_probability(drop_area)
        sorted_hits = sorted(map(int, hit_values.keys()))
        breakdown = []
        
        for hit_val, pattern5_prob in PATTERN_5_HIT_PROBABILITIES.items():
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
                    hit_price = self.price_guide.get_price_from_range(price_range, self.price_guide.bps)
                    expected_value = hit_price * combined_prob
                    breakdown.append({
                        "hit_value": hit_val,
                        "teched_hit": teched_hit,
                        "pattern5_prob": pattern5_prob,
                        "combined_prob": combined_prob,
                        "price_range": price_range,
                        "price": hit_price,
                        "expected_value": expected_value,
                    })
                except Exception:
                    pass
        
        return breakdown
