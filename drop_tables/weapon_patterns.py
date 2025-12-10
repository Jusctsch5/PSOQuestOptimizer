"""
Weapon pattern attribute value probabilities.

Rare weapons always use Pattern 5 for all attributes.
Common weapons use area-specific patterns (0-4) based on the area pattern selection table.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# Pattern attribute value probabilities
# Each pattern has probabilities for different attribute values (5%, 10%, 15%, etc.)
# Values are percentages (0.0 to 1.0)


PATTERN_ATTRIBUTE_PROBABILITIES = {
    0: {
        5: 0.4256,
        10: 0.3324,
        15: 0.1541,
        20: 0.0820,
        25: 0.0050,
        30: 0.0003,
        35: 0.0002,
        40: 0.0002,
        45: 0.0001,
        50: 0.0001,
    },
    1: {
        5: 0.0897,
        10: 0.1932,
        15: 0.3852,
        20: 0.2219,
        25: 0.0998,
        30: 0.0082,
        35: 0.0011,
        40: 0.0005,
        45: 0.0002,
        50: 0.0001,
        55: 0.0001,
    },
    2: {
        5: 0.0402,
        10: 0.0890,
        15: 0.1532,
        20: 0.3698,
        25: 0.2126,
        30: 0.0972,
        35: 0.0331,
        40: 0.0035,
        45: 0.0007,
        50: 0.0003,
        55: 0.0002,
        60: 0.0001,
        65: 0.0001,
    },
    3: {
        5: 0.0205,
        10: 0.0211,
        15: 0.1021,
        20: 0.1345,
        25: 0.3452,
        30: 0.2102,
        35: 0.1139,
        40: 0.0476,
        45: 0.0025,
        50: 0.0016,
        55: 0.0003,
        60: 0.0002,
        65: 0.0001,
        70: 0.0001,
        75: 0.0001,
    },
    4: {
        5: 0.0102,
        10: 0.0121,
        15: 0.0756,
        20: 0.1011,
        25: 0.1672,
        30: 0.3565,
        35: 0.1568,
        40: 0.0932,
        45: 0.0201,
        50: 0.0041,
        55: 0.0012,
        60: 0.0007,
        65: 0.0004,
        70: 0.0003,
        75: 0.0002,
        80: 0.0001,
        85: 0.0001,
        90: 0.0001,
    },
    5: {
        5: 0.2921,
        10: 0.2309,
        15: 0.1908,
        20: 0.1389,
        25: 0.0865,
        30: 0.0310,
        35: 0.0156,
        40: 0.0067,
        45: 0.0042,
        50: 0.0016,
        55: 0.0008,
        60: 0.0003,
        65: 0.0001,
        70: 0.0001,
        75: 0.0001,
        80: 0.0001,
        85: 0.0001,
        90: 0.0001,
    },
}

# Area attribute rates (for determining hit probability)
# These determine the probability of rolling hit in the first place
AREA_ATTRIBUTE_RATES = {
    # Episode 1
    "Forest 1": {"native": 30, "abeast": 19, "machine": 13, "dark": 8, "hit": 5, "no_attribute": 25},
    "Forest 2": {"native": 30, "abeast": 19, "machine": 13, "dark": 8, "hit": 5, "no_attribute": 25},
    "Cave 1": {"native": 11, "abeast": 30, "machine": 19, "dark": 10, "hit": 5, "no_attribute": 25},
    "Cave 2": {"native": 11, "abeast": 30, "machine": 19, "dark": 10, "hit": 5, "no_attribute": 25},
    "Cave 3": {"native": 9, "abeast": 30, "machine": 21, "dark": 10, "hit": 5, "no_attribute": 25},
    "Mine 1": {"native": 6, "abeast": 12, "machine": 32, "dark": 20, "hit": 5, "no_attribute": 25},
    "Mine 2": {"native": 6, "abeast": 12, "machine": 32, "dark": 20, "hit": 5, "no_attribute": 25},
    "Ruins 1": {"native": 20, "abeast": 7, "machine": 11, "dark": 32, "hit": 5, "no_attribute": 25},
    "Ruins 2": {"native": 20, "abeast": 7, "machine": 11, "dark": 32, "hit": 5, "no_attribute": 25},
    "Ruins 3": {"native": 13, "abeast": 13, "machine": 12, "dark": 32, "hit": 5, "no_attribute": 25},
    # Episode 2
    "VR Temple Alpha": {"native": 15, "abeast": 10, "machine": 10, "dark": 10, "hit": 5, "no_attribute": 50},
    "VR Temple Beta": {"native": 10, "abeast": 10, "machine": 15, "dark": 10, "hit": 5, "no_attribute": 50},
    "VR Spaceship Alpha": {"native": 15, "abeast": 10, "machine": 10, "dark": 10, "hit": 5, "no_attribute": 50},
    "VR Spaceship Beta": {"native": 10, "abeast": 10, "machine": 10, "dark": 15, "hit": 5, "no_attribute": 50},
    "Jungle Area North": {"native": 15, "abeast": 10, "machine": 10, "dark": 10, "hit": 5, "no_attribute": 50},
    "Jungle Area East": {"native": 10, "abeast": 15, "machine": 10, "dark": 10, "hit": 5, "no_attribute": 50},
    "Mountain Area": {"native": 10, "abeast": 10, "machine": 10, "dark": 15, "hit": 5, "no_attribute": 50},
    "Seaside Area": {"native": 10, "abeast": 10, "machine": 15, "dark": 10, "hit": 5, "no_attribute": 50},
    "Central Control Area": {"native": 10, "abeast": 10, "machine": 15, "dark": 10, "hit": 5, "no_attribute": 50},
    "Seabed Upper Levels": {"native": 15, "abeast": 10, "machine": 15, "dark": 10, "hit": 5, "no_attribute": 45},
    "Seabed Lower Levels": {"native": 10, "abeast": 15, "machine": 10, "dark": 15, "hit": 5, "no_attribute": 45},
    "Control Tower": {"native": 10, "abeast": 15, "machine": 10, "dark": 15, "hit": 5, "no_attribute": 45},
    # Episode 4
    "Crater East": {"native": 15, "abeast": 10, "machine": 10, "dark": 10, "hit": 5, "no_attribute": 50},
    "Crater West": {"native": 10, "abeast": 10, "machine": 10, "dark": 15, "hit": 5, "no_attribute": 50},
    "Crater South": {"native": 15, "abeast": 10, "machine": 10, "dark": 10, "hit": 5, "no_attribute": 50},
    "Crater North": {"native": 10, "abeast": 15, "machine": 10, "dark": 10, "hit": 5, "no_attribute": 50},
    "Crater Interior": {"native": 10, "abeast": 10, "machine": 10, "dark": 15, "hit": 5, "no_attribute": 50},
    "Subterranean Desert 1": {"native": 10, "abeast": 10, "machine": 15, "dark": 10, "hit": 5, "no_attribute": 50},
    "Subterranean Desert 2": {"native": 15, "abeast": 10, "machine": 15, "dark": 10, "hit": 5, "no_attribute": 45},
    "Subterranean Desert 3": {"native": 10, "abeast": 15, "machine": 10, "dark": 15, "hit": 5, "no_attribute": 45},
}

AREAS: List[str] = list(AREA_ATTRIBUTE_RATES.keys())


class AttributeType(Enum):
    """Attribute types that can appear on weapons."""

    NATIVE = "N"
    ABEAST = "AB"
    MACHINE = "M"
    DARK = "D"
    HIT = "Hit"
    NONE = "No Attribute"


@dataclass
class AreaAttributeRates:
    """Attribute probability rates for an area."""

    native: float
    abeast: float
    machine: float
    dark: float
    hit: float
    no_attribute: float


@dataclass
class PatternConfig:
    """Pattern configuration for an area."""

    area_name: str
    patterns: List[str]  # Pattern names like ["VR Temple Alpha", "VR Temple Beta", "-"]
    attribute_counts: List[int]  # How many attributes roll, e.g., [2, 1, 0]


# Pattern value ranges
# Each pattern number corresponds to a value range
# Pattern 0: 5-10%, Pattern 1: 10-20%, Pattern 2: 20-30%, etc.
PATTERN_VALUE_RANGES = {
    0: (5, 10),
    1: (10, 20),
    2: (20, 30),
    3: (30, 40),
    4: (40, 50),
    5: (50, 60),
    6: (60, 70),
    7: (70, 80),
    8: (80, 90),
}


def get_pattern_probability(pattern_num: int, attribute_value: int) -> float:
    """
    Get the probability of rolling a specific attribute value on a pattern.

    Args:
        pattern_num: Pattern number (0-5)
        attribute_value: Attribute value (5, 10, 15, 20, etc.)

    Returns:
        Probability (0.0 to 1.0), or 0.0 if not possible
    """
    pattern = PATTERN_ATTRIBUTE_PROBABILITIES.get(pattern_num, {})
    return pattern.get(attribute_value, 0.0)


def get_pattern_probability_at_least(pattern_num: int, min_value: int) -> float:
    """
    Get the probability of rolling at least a specific attribute value on a pattern.

    Args:
        pattern_num: Pattern number (0-5)
        min_value: Minimum attribute value

    Returns:
        Probability (0.0 to 1.0) of rolling at least min_value
    """
    pattern = PATTERN_ATTRIBUTE_PROBABILITIES.get(pattern_num, {})
    total_prob = 0.0
    for attr_val, prob in pattern.items():
        if attr_val >= min_value:
            total_prob += prob
    return total_prob


def is_rare_weapon(weapon_name: str) -> bool:
    """
    Determine if a weapon is rare (uses Pattern 5) or common (uses area patterns).

    This is a simplified check - in reality, you'd check the weapon's rarity code.
    For now, we'll assume weapons in the price guide's weapons.json are rare,
    and weapons in common_weapons.json are common.

    Args:
        weapon_name: Name of the weapon

    Returns:
        True if rare, False if common
    """
    # TODO: Implement proper rarity checking based on item codes
    # For now, we'll need to check against the price guide data
    # This is a placeholder - should be determined from drop table data
    return True  # Default to rare for now


def get_expected_attribute_value(pattern_num: int, min_value: int = 0) -> float:
    """
    Calculate expected attribute value for a pattern, optionally with a minimum.

    Args:
        pattern_num: Pattern number (0-5)
        min_value: Minimum attribute value to consider (default: 0, considers all)

    Returns:
        Expected attribute value
    """
    pattern = PATTERN_ATTRIBUTE_PROBABILITIES.get(pattern_num, {})
    expected = 0.0
    for attr_val, prob in pattern.items():
        if attr_val >= min_value:
            expected += attr_val * prob
    return expected


def _calculate_weapon_attributes(
    weapon_data: Dict,
    drop_area: Optional[str] = None,
) -> Dict[str, float]:
    """
    Calculate expected attribute value contribution using actual game mechanics.

    The game performs three rolls on the area attribute table (1-100).
    Each roll can result in: Native, A.Beast, Machine, Dark, Hit, or No Attribute.
    If a roll results in an attribute that was already chosen, it becomes "no attribute" instead.
    After three rolls, for each successfully assigned attribute type, roll Pattern 5 for the value.
    Only attributes >= 50% contribute to value.

    Args:
        weapon_data: Weapon data from price guide
        drop_area: Drop area name (e.g., "Forest 1", "Cave 2")

    Returns:
        Dictionary with expected attribute value contribution for each attribute type:
        {
            "native": float,
            "abeast": float,
            "machine": float,
            "dark": float,
            "hit": float,
            "total": float
        }
    """
    result = {
        "native": 0.0,
        "abeast": 0.0,
        "machine": 0.0,
        "dark": 0.0,
        "hit": 0.0,
        "total": 0.0,
    }

    # Get area attribute rates
    if not drop_area or drop_area not in AREA_ATTRIBUTE_RATES:
        return result

    area_rates = AREA_ATTRIBUTE_RATES[drop_area]
    total_rate = sum(area_rates.values())

    if total_rate == 0:
        return result

    # Convert to probabilities
    attr_probs = {
        "native": area_rates["native"] / total_rate,
        "abeast": area_rates["abeast"] / total_rate,
        "machine": area_rates["machine"] / total_rate,
        "dark": area_rates["dark"] / total_rate,
        "hit": area_rates["hit"] / total_rate,
        "no_attribute": area_rates["no_attribute"] / total_rate,
    }

    # Map attribute types to modifier keys (just for checking if attribute exists)
    attr_to_modifier = {
        "native": "N",
        "abeast": "AB",
        "machine": "M",
        "dark": "D",
    }

    # Check which attributes the weapon supports
    modifiers = weapon_data.get("modifiers", {})
    supported_attrs = set()
    for attr_name, mod_key in attr_to_modifier.items():
        if mod_key in modifiers:
            supported_attrs.add(attr_name)

    # Check if weapon supports hit
    hit_values = weapon_data.get("hit_values", {})
    if hit_values:
        supported_attrs.add("hit")

    if not supported_attrs:
        return result

    # Calculate Pattern 5 probability sum for attributes >= 50%
    pattern5_prob_sum_50plus = sum(prob for attr_val, prob in PATTERN_ATTRIBUTE_PROBABILITIES[5].items() if attr_val >= 50)

    # Calculate expected Pattern 5 contribution per attribute type if assigned
    # (without price multiplication - that's done by the caller)
    attr_pattern5_contrib_per_assignment = {
        "native": pattern5_prob_sum_50plus,
        "abeast": pattern5_prob_sum_50plus,
        "machine": pattern5_prob_sum_50plus,
        "dark": pattern5_prob_sum_50plus,
        "hit": 1.0,  # Hit uses full Pattern 5 distribution (all values, not just >= 50%)
    }

    # Simulate all possible outcomes of three rolls
    # Each roll can result in one of: native, abeast, machine, dark, hit, no_attribute
    # We need to track which attributes have been assigned (no duplicates)

    roll_outcomes = ["native", "abeast", "machine", "dark", "hit", "no_attribute"]

    # Track expected value per attribute type
    attr_expected = {
        "native": 0.0,
        "abeast": 0.0,
        "machine": 0.0,
        "dark": 0.0,
        "hit": 0.0,
    }

    # Iterate through all possible combinations of three rolls
    for roll1 in roll_outcomes:
        prob1 = attr_probs[roll1]
        if prob1 == 0:
            continue

        assigned_attrs_1 = set()
        if roll1 in attr_to_modifier or roll1 == "hit":
            assigned_attrs_1.add(roll1)

        for roll2 in roll_outcomes:
            prob2 = attr_probs[roll2]
            if prob2 == 0:
                continue

            assigned_attrs_2 = assigned_attrs_1.copy()
            # If roll2 is a duplicate attribute, it becomes "no_attribute"
            if roll2 in attr_to_modifier or roll2 == "hit":
                if roll2 not in assigned_attrs_2:
                    assigned_attrs_2.add(roll2)
                # else: duplicate, becomes no_attribute (don't add)

            for roll3 in roll_outcomes:
                prob3 = attr_probs[roll3]
                if prob3 == 0:
                    continue

                assigned_attrs_3 = assigned_attrs_2.copy()
                # If roll3 is a duplicate attribute, it becomes "no_attribute"
                if roll3 in attr_to_modifier or roll3 == "hit":
                    if roll3 not in assigned_attrs_3:
                        assigned_attrs_3.add(roll3)
                    # else: duplicate, becomes no_attribute (don't add)

                # Calculate probability of this outcome
                outcome_prob = prob1 * prob2 * prob3

                # Add expected Pattern 5 contribution for each assigned attribute
                # (probability that attribute is assigned * Pattern 5 contribution if assigned)
                for attr_name in assigned_attrs_3:
                    if attr_name in supported_attrs and attr_name in attr_pattern5_contrib_per_assignment:
                        attr_expected[attr_name] += attr_pattern5_contrib_per_assignment[attr_name] * outcome_prob

    # Populate result dictionary
    result["native"] = attr_expected["native"]
    result["abeast"] = attr_expected["abeast"]
    result["machine"] = attr_expected["machine"]
    result["dark"] = attr_expected["dark"]
    result["hit"] = attr_expected["hit"]
    result["total"] = sum(attr_expected.values())

    return result


def calculate_common_weapon_attributes(
    weapon_data: Dict[str, Any],
    drop_area: Optional[str] = None,
) -> Dict[str, float]:
    """
    Calculate expected attribute value contribution using actual game mechanics.
    """
    return _calculate_weapon_attributes(weapon_data, drop_area=drop_area)


def calculate_rare_weapon_attributes(
    weapon_data: Dict[str, Any],
) -> Dict[str, float]:
    return _calculate_weapon_attributes(weapon_data)


def get_hit_probability(drop_area: Optional[str] = None) -> float:
    """
    Get the probability of rolling hit in a single roll for a given area.

    Args:
        drop_area: Area name (e.g., "Forest 1", "Cave 2")

    Returns:
        Probability (0.0 to 1.0) of rolling hit in a single roll
    """
    if not drop_area or drop_area not in AREA_ATTRIBUTE_RATES:
        # Default hit probability if area not specified
        return 0.05  # 5% default

    area_rates = AREA_ATTRIBUTE_RATES[drop_area]
    # Handle both dict and dataclass formats
    if isinstance(area_rates, dict):
        total_rate = sum(area_rates.values())
        if total_rate == 0:
            return 0.0
        return area_rates["hit"] / total_rate
    else:
        # Dataclass format
        total_rate = (
            area_rates.native
            + area_rates.abeast
            + area_rates.machine
            + area_rates.dark
            + area_rates.hit
            + area_rates.no_attribute
        )
        if total_rate == 0:
            return 0.0
        return area_rates.hit / total_rate


def get_three_roll_hit_probability(drop_area: Optional[str] = None) -> float:
    """
    Get the probability of rolling hit in at least one of three rolls.

    The game performs three rolls on the area attribute table.
    This calculates the probability that at least one roll results in hit.

    Args:
        drop_area: Area name (e.g., "Forest 1", "Cave 2")

    Returns:
        Probability (0.0 to 1.0) of rolling hit in at least one of three rolls
    """
    single_roll_hit_prob = get_hit_probability(drop_area)

    # Probability of no hit in all three rolls = (1 - hit_prob)^3
    no_hit_prob = (1.0 - single_roll_hit_prob) ** 3

    # Probability of at least one hit = 1 - (no hit in all three rolls)
    return 1.0 - no_hit_prob


def get_hit_breakdown_data(
    drop_area: Optional[str] = None,
) -> Dict[str, float]:
    """
    Get breakdown of hit probabilities for display.

    Args:
        drop_area: Area name

    Returns:
        Dictionary with:
        {
            "single_roll_hit_prob": float,
            "three_roll_hit_prob": float,
            "no_hit_prob": float,
        }
    """
    single_roll_hit_prob = get_hit_probability(drop_area)
    three_roll_hit_prob = get_three_roll_hit_probability(drop_area)
    no_hit_prob = 1.0 - three_roll_hit_prob

    return {
        "single_roll_hit_prob": single_roll_hit_prob,
        "three_roll_hit_prob": three_roll_hit_prob,
        "no_hit_prob": no_hit_prob,
    }


def get_pattern_number(pattern_name: str) -> int:
    """
    Convert pattern name to pattern number.
    Pattern names map to pattern numbers based on the area pattern selection table.
    """
    # This is a simplified mapping - in reality, pattern names correspond to areas
    # and those areas have specific pattern numbers
    # For now, we'll need to map based on the pattern selection table
    pattern_mapping = {
        "VR Temple Alpha": 2,
        "VR Temple Beta": 2,
        "VR Spaceship Alpha": 2,
        "VR Spaceship Beta": 2,
        "Jungle Area North": 3,
        "Jungle Area East": 3,
        "Mountain Area": 3,
        "Seaside Area": 3,
        "Central Control Area": 4,
        "Seabed Upper Levels": 4,
        "Seabed Lower Levels": 4,
        "Control Tower": 4,
        "Crater East": 2,
        "Crater West": 2,
        "Crater South": 3,
        "Crater North": 3,
        "Crater Interior": 3,
        "Subterranean Desert 1": 4,
        "Subterranean Desert 2": 4,
        "Subterranean Desert 3": 4,
    }
    return pattern_mapping.get(pattern_name, 0)


def get_pattern_value_range(pattern_num: int) -> Tuple[int, int]:
    """Get the value range for a pattern number."""
    return PATTERN_VALUE_RANGES.get(pattern_num, (5, 10))


def calculate_average_pattern_value(pattern_num: int) -> float:
    """Calculate average value for a pattern (midpoint of range)."""
    min_val, max_val = get_pattern_value_range(pattern_num)
    return (min_val + max_val) / 2
