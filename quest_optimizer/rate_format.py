"""
Format drop rates for display.

Internal calculations always use decimal probabilities. PSO players often
think in 1/N fractions (Ephinea drop charts). After modifiers, denominators
can become non-integers (e.g. 1/900.2).
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, Union

RateFormatInput = Union[str, "RateFormat"]


class RateFormat(str, Enum):
    DECIMAL = "decimal"
    FRACTION = "fraction"


def normalize_rate_format(mode: Optional[RateFormatInput]) -> RateFormat:
    """Parse user-facing rate format; default to decimal."""
    if mode is None:
        return RateFormat.DECIMAL
    if isinstance(mode, RateFormat):
        return mode
    value = str(mode).strip().lower()
    if value in ("fraction", "fractions", "frac", "1/n"):
        return RateFormat.FRACTION
    return RateFormat.DECIMAL


def _format_denominator(denominator: float) -> str:
    rounded_int = round(denominator)
    if abs(denominator - rounded_int) < 1e-9:
        return str(int(rounded_int))

    # Ephinea-style modified rates use one decimal place (e.g. 1/900.2).
    rounded_one = round(denominator, 1)
    if abs(denominator - rounded_one) < 0.05:
        text = f"{rounded_one:.1f}".rstrip("0").rstrip(".")
        return text

    # Fall back to higher precision when one decimal is not enough.
    text = f"{denominator:.4f}".rstrip("0").rstrip(".")
    return text


def format_rate_fraction(rate: float) -> str:
    """Format a probability as 1/N (PSO drop-chart style)."""
    if rate <= 0:
        return "0"
    if rate >= 1:
        return "1/1"
    return f"1/{_format_denominator(1.0 / rate)}"


def format_rate_decimal(
    rate: float,
    as_percent: bool = True,
    precision: Optional[int] = None,
) -> str:
    """Format a probability as a decimal or percentage string."""
    if as_percent:
        places = precision if precision is not None else 6
        return f"{rate * 100:.{places}f}%"
    places = precision if precision is not None else 8
    return f"{rate:.{places}f}"


def format_rate(
    rate: float,
    mode: RateFormatInput = RateFormat.DECIMAL,
    as_percent: bool = True,
    precision: Optional[int] = None,
) -> str:
    """Format a drop rate according to the selected display mode."""
    if normalize_rate_format(mode) == RateFormat.FRACTION:
        return format_rate_fraction(rate)
    return format_rate_decimal(rate, as_percent=as_percent, precision=precision)


def format_rate_change(
    base_rate: float,
    adjusted_rate: float,
    mode: RateFormatInput = RateFormat.DECIMAL,
    as_percent: bool = True,
    precision: Optional[int] = None,
    tolerance: float = 1e-12,
) -> str:
    """Format a base rate, appending ' -> adjusted' when modifiers apply."""
    base_text = format_rate(base_rate, mode, as_percent=as_percent, precision=precision)
    if abs(adjusted_rate - base_rate) <= tolerance:
        return base_text
    adjusted_text = format_rate(adjusted_rate, mode, as_percent=as_percent, precision=precision)
    return f"{base_text} -> {adjusted_text}"
