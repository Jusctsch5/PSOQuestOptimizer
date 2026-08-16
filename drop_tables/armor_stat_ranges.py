"""
Absolute DFP/EVP ranges for frames and barriers (shields).

Game-mechanics data used by armor expected-value calculations.
Market prices live in price_guide/data; this file only stores wiki stat ranges.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_DATA_PATH = Path(__file__).with_name("armor_stat_ranges.json")


@dataclass(frozen=True)
class ArmorStatRange:
    """Inclusive absolute DFP/EVP range for one frame or barrier."""

    dfp: Tuple[int, int]
    evp: Tuple[int, int]
    notes: Optional[str] = None

    @property
    def dfp_values(self) -> List[int]:
        lo, hi = self.dfp
        return list(range(lo, hi + 1))

    @property
    def evp_values(self) -> List[int]:
        lo, hi = self.evp
        return list(range(lo, hi + 1))

    def dfp_count(self) -> int:
        lo, hi = self.dfp
        return hi - lo + 1

    def evp_count(self) -> int:
        lo, hi = self.evp
        return hi - lo + 1


def _ci_key(mapping: Dict[str, ArmorStatRange], name: str) -> Optional[str]:
    if name in mapping:
        return name
    lower = name.lower()
    for key in mapping:
        if key.lower() == lower:
            return key
    return None


def _parse_entry(raw: dict) -> ArmorStatRange:
    dfp = raw["dfp"]
    evp = raw["evp"]
    if len(dfp) != 2 or len(evp) != 2:
        raise ValueError(f"dfp/evp must be [min, max], got {raw}")
    return ArmorStatRange(
        dfp=(int(dfp[0]), int(dfp[1])),
        evp=(int(evp[0]), int(evp[1])),
        notes=raw.get("notes"),
    )


class ArmorStatRanges:
    """Lookup table for frame/barrier absolute DFP/EVP ranges."""

    def __init__(self, path: Optional[Path] = None):
        data_path = path or _DATA_PATH
        raw = json.loads(data_path.read_text(encoding="utf-8"))
        self.frames: Dict[str, ArmorStatRange] = {
            name: _parse_entry(entry) for name, entry in raw.get("frames", {}).items()
        }
        self.barriers: Dict[str, ArmorStatRange] = {
            name: _parse_entry(entry) for name, entry in raw.get("barriers", {}).items()
        }

    @classmethod
    def from_dicts(
        cls,
        frames: Optional[Dict[str, Dict]] = None,
        barriers: Optional[Dict[str, Dict]] = None,
    ) -> "ArmorStatRanges":
        """Build ranges from in-memory dicts (for tests)."""
        obj = cls.__new__(cls)
        obj.frames = {name: _parse_entry(entry) for name, entry in (frames or {}).items()}
        obj.barriers = {name: _parse_entry(entry) for name, entry in (barriers or {}).items()}
        return obj

    def get_frame(self, name: str) -> Optional[ArmorStatRange]:
        key = _ci_key(self.frames, name)
        return self.frames[key] if key is not None else None

    def get_barrier(self, name: str) -> Optional[ArmorStatRange]:
        key = _ci_key(self.barriers, name)
        return self.barriers[key] if key is not None else None


_default: Optional[ArmorStatRanges] = None


def get_armor_stat_ranges() -> ArmorStatRanges:
    """Return a process-wide ArmorStatRanges instance."""
    global _default
    if _default is None:
        _default = ArmorStatRanges()
    return _default
