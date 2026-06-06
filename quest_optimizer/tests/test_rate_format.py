import math

from quest_optimizer.rate_format import (
    RateFormat,
    format_rate,
    format_rate_change,
    format_rate_fraction,
    normalize_rate_format,
)


def test_format_rate_fraction_integers():
    assert format_rate_fraction(0.5) == "1/2"
    assert format_rate_fraction(1.0 / 315.0) == "1/315"
    assert format_rate_fraction(1.0 / 2048.0) == "1/2048"


def test_format_rate_fraction_modified_denominator():
    assert format_rate_fraction(1.0 / 900.2) == "1/900.2"
    boosted = (1.0 / 315.0) * 1.25
    assert format_rate_fraction(boosted) == "1/252"


def test_format_rate_fraction_edge_cases():
    assert format_rate_fraction(0) == "0"
    assert format_rate_fraction(1.0) == "1/1"
    assert format_rate_fraction(1.5) == "1/1"


def test_format_rate_decimal_percent():
    assert format_rate(0.001, RateFormat.DECIMAL) == "0.100000%"


def test_format_rate_fraction_mode():
    assert format_rate(1.0 / 315.0, "fraction") == "1/315"


def test_format_rate_change_with_boost():
    base = 1.0 / 315.0
    adjusted = base * 1.25
    assert format_rate_change(base, adjusted, "fraction") == "1/315 -> 1/252"
    assert format_rate_change(base, base, "fraction") == "1/315"


def test_normalize_rate_format_aliases():
    assert normalize_rate_format("fraction") == RateFormat.FRACTION
    assert normalize_rate_format("1/n") == RateFormat.FRACTION
    assert normalize_rate_format(None) == RateFormat.DECIMAL
    assert normalize_rate_format("decimal") == RateFormat.DECIMAL


def test_rdr_boost_matches_drop_chart_math():
    """+25% RDR multiplies probability, dividing the 1/N denominator by 1.25."""
    base_rdr = 1.0 / 1170.3
    adjusted_rdr = base_rdr * 1.25
    expected_denom = 1170.3 / 1.25
    assert math.isclose(1.0 / adjusted_rdr, expected_denom, rel_tol=1e-9)
    assert format_rate_fraction(adjusted_rdr) == f"1/{expected_denom:.1f}".rstrip("0").rstrip(".")
