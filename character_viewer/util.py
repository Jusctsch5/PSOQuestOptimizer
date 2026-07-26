"""Binary helpers for PSO character/bank parsing."""

from typing import Sequence


def binary_array_to_int(arr: Sequence[int]) -> int:
    result = 0
    for val in arr:
        result = (result << 8) | (val & 0xFF)
    return result


def binary_array_to_hex(arr: Sequence[int]) -> str:
    return "".join(f"{x & 0xFF:02X}" for x in arr)


def int_to_hex(value: int) -> str:
    return f"0x{value:06X}"


def to_signed_byte(value: int) -> int:
    value = value & 0xFF
    return value - 256 if value > 127 else value
