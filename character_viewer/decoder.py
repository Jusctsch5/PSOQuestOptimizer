"""Decode uploaded .psochar / .psobank / .psoclassicbank files into valued inventories."""

from __future__ import annotations

import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from character_viewer.bank_parser import BankParser
from character_viewer.character_parser import CharacterParser
from character_viewer.config import Mode, ViewerConfig
from price_guide.price_guide import PriceGuideAbstract


FileEntry = Dict[str, Any]


def decode_character_files(
    files: Sequence[FileEntry],
    price_guide: Optional[PriceGuideAbstract] = None,
) -> Dict[str, Any]:
    """
    Decode character/bank binaries.

    Args:
        files: Sequence of {"filename": str, "binary": bytes|list[int]}
        price_guide: Optional PriceGuideAbstract for PD valuation

    Returns:
        Dict with characters, share_banks, all_items, totals
    """
    config = ViewerConfig()
    character_parser = CharacterParser(config, price_guide)
    bank_parser = BankParser(config, price_guide)

    entries = _normalize_entries(files)
    sorted_entries = _sort_input_files(entries)

    characters: List[Dict[str, Any]] = []
    share_banks: List[Optional[Dict[str, Any]]] = [None, None]
    all_items = [
        {"slot": "AllItems", "mode": int(Mode.NORMAL), "inventory": [], "total_pd": 0.0},
        {
            "slot": "AllItems(Classic)",
            "mode": int(Mode.CLASSIC),
            "inventory": [],
            "total_pd": 0.0,
        },
    ]

    for entry in sorted_entries:
        filename = entry["filename"]
        binary = entry["binary"]
        if not _is_character_data_path(filename):
            continue
        lower = filename.lower()

        if "psoclassicbank" in lower:
            bank = bank_parser.parse(binary, Mode.CLASSIC)
            share_banks[1] = bank
            all_items[Mode.CLASSIC]["inventory"].extend(bank["bank"])
            continue

        if "psobank" in lower:
            bank = bank_parser.parse(binary, Mode.NORMAL)
            share_banks[0] = bank
            all_items[Mode.NORMAL]["inventory"].extend(bank["bank"])
            continue

        if "psochar" in lower:
            slot_match = re.search(r"(\d+)\.", filename)
            slot = int(slot_match.group(1)) + 1 if slot_match else 1
            character = character_parser.parse(binary, slot)
            characters.append(character)
            mode = character["mode"]
            all_items[mode]["inventory"].extend(character["inventory"])
            all_items[mode]["inventory"].extend(character["bank"])

    for bucket in all_items:
        bucket["inventory"] = _sort_inventory(bucket["inventory"])
        for idx, item in enumerate(bucket["inventory"]):
            # Keep [hex, item, slot, index] for stable UI lookups
            if len(item) == 3:
                item.append(idx)
            else:
                item[3] = idx
        bucket["total_pd"] = sum(float(entry[1].get("price") or 0) for entry in bucket["inventory"])

    banks_present = [b for b in share_banks if b is not None]

    return {
        "characters": characters,
        "share_banks": banks_present,
        "all_items": all_items,
        "totals": {
            "characters_pd": sum(c["total_pd"] for c in characters),
            "share_banks_pd": sum(b["total_pd"] for b in banks_present),
            "all_items_normal_pd": all_items[0]["total_pd"],
            "all_items_classic_pd": all_items[1]["total_pd"],
        },
    }


def decode_from_zip(
    zip_bytes: bytes,
    price_guide: Optional[PriceGuideAbstract] = None,
) -> Dict[str, Any]:
    """Extract relevant files from a zip and decode them."""
    entries: List[FileEntry] = []
    with zipfile.ZipFile(BytesIO(zip_bytes), "r") as zf:
        for name in zf.namelist():
            if not _is_character_data_path(name):
                continue
            base = Path(name).name
            entries.append({"filename": base, "binary": zf.read(name)})
    return decode_character_files(entries, price_guide)


def _is_character_data_path(path: str) -> bool:
    """True for real .psochar/.psobank/.psoclassicbank files (skip macOS junk)."""
    if "__macosx" in path.lower().replace("\\", "/"):
        return False
    base = Path(path).name
    if base.startswith("._"):
        return False
    lower = base.lower()
    return lower.endswith((".psochar", ".psobank", ".psoclassicbank"))


def _normalize_entries(files: Sequence[FileEntry]) -> List[FileEntry]:
    normalized: List[FileEntry] = []
    for entry in files:
        filename = entry.get("filename") or entry.get("name") or ""
        binary = entry.get("binary")
        if binary is None:
            continue
        if isinstance(binary, (bytes, bytearray)):
            data = list(binary)
        else:
            data = [int(b) & 0xFF for b in binary]
        normalized.append({"filename": str(filename), "binary": data})
    return normalized


def _sort_input_files(files: List[FileEntry]) -> List[FileEntry]:
    def sort_key(file: FileEntry):
        filename = file["filename"].lower()
        if "psoclassicbank" in filename:
            return (2, 0)
        if "psobank" in filename:
            return (1, 0)
        match = re.search(r"(\d+)\.", filename)
        slot_num = int(match.group(1)) if match else 0
        return (0, slot_num)

    return sorted(files, key=sort_key)


def _sort_inventory(inventory: List[List[Any]]) -> List[List[Any]]:
    def key(entry: List[Any]):
        item = entry[1]
        item_type = item.get("type")
        hex_code = entry[0]
        slot = str(entry[2])
        # Meseta last-ish; share bank after character slots
        is_meseta = 1 if item_type == 10 else 0
        share_last = 1 if "ShareBank" in slot else 0
        return (is_meseta, hex_code, share_last, slot)

    return sorted(inventory, key=key)
