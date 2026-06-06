"""
Fetch Ephinea wiki wikitext for Black Paper's Dangerous Deal (1 & 2) and emit bpd_pools.json.

Run from repo root:
  python scripts/generate_bpd_pools.py

See https://wiki.pioneer2.net/w/Black_Paper%27s_Dangerous_Deal
    https://wiki.pioneer2.net/w/Black_Paper%27s_Dangerous_Deal_2

BPD1: equal weight per non-meseta outcome; meseta is 6x as likely (wiki).
BPD2: uniform over listed items per roll (no junk); bold in wiki is quest-exclusive only, same odds.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = REPO_ROOT / "price_guide" / "data" / "bpd_pools.json"
API = "https://wiki.pioneer2.net/api.php"

WIKI_BPD1 = "https://wiki.pioneer2.net/w/Black_Paper%27s_Dangerous_Deal"
WIKI_BPD2 = "https://wiki.pioneer2.net/w/Black_Paper%27s_Dangerous_Deal_2"

# (?:''')? avoids r"'''" which would end a Python raw string early
RE_TEMPLATE_ITEM = re.compile(r"(?:''')?\{\{[^|]+\|rare\|([^}]+)\}\}(?:''')?", re.IGNORECASE)
RE_WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def fetch_wikitext(title: str) -> str:
    q = urllib.parse.urlencode(
        {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "format": "json",
            "titles": title,
        }
    )
    req = urllib.request.Request(API + "?" + q, headers={"User-Agent": "PSOQuestOptimizer-bpd-generator/1.0"})
    with urllib.request.urlopen(req, timeout=45) as r:
        d = json.load(r)
    pages = d["query"]["pages"]
    p = next(iter(pages.values()))
    revs = p.get("revisions", [{}])
    return str(revs[0].get("*", ""))


def _items_from_cell(cell: str) -> list[str]:
    names: list[str] = []
    for m in RE_TEMPLATE_ITEM.finditer(cell):
        names.append(m.group(1).strip())
    for m in RE_WIKILINK.finditer(cell):
        name = m.group(1).strip()
        if not name or name.startswith("File:") or name.startswith("Image:"):
            continue
        names.append(name)
    # de-dupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        key = n.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(n)
    return out


def _extract_data_row_cells(table_block: str) -> list[str]:
    """First wikitable in block: one |- opens the data row; cells split by newline-pipe-newline."""
    t = table_block.replace("\r\n", "\n")
    idx = t.find("|-")
    if idx < 0:
        return []
    data = t[idx + 2 :].lstrip()
    if data.startswith("\n|"):
        data = data[2:]
    elif data.startswith("|"):
        data = data[1:]
    end = data.find("\n|}")
    if end >= 0:
        data = data[:end]
    cells = [c.strip() for c in data.split("\n|\n")]
    return [c for c in cells if c]


def _first_wikitable_after(whole: str, anchor: str) -> str:
    i = whole.find(anchor)
    if i < 0:
        return ""
    j = whole.find("{|", i)
    if j < 0:
        return ""
    k = whole.find("\n|}", j)
    if k < 0:
        return whole[j:]
    return whole[j : k + 3]


def parse_bpd1(wikitext: str) -> dict:
    arenas_order = [
        ("sand_rappy", "===Sand Rappy arena===", "===Zu arena==="),
        ("zu", "===Zu arena===", "===Dorphon arena==="),
        ("dorphon", "===Dorphon arena===", "==Enemy Counts=="),
    ]
    difficulties = ["Normal", "Hard", "Very Hard", "Ultimate"]
    out_arenas: dict[str, dict[str, list[str]]] = {}
    for key, start_anchor, end_anchor in arenas_order:
        i0 = wikitext.find(start_anchor)
        i1 = wikitext.find(end_anchor)
        if i0 < 0 or i1 < 0 or i1 <= i0:
            raise ValueError(f"BPD1: could not slice arena {key}")
        chunk = wikitext[i0:i1]
        tbl = _first_wikitable_after(chunk, start_anchor)
        cells = _extract_data_row_cells(tbl)
        if len(cells) != 4:
            raise ValueError(f"BPD1 arena {key}: expected 4 cells, got {len(cells)}")
        out_arenas[key] = {}
        for diff, cell in zip(difficulties, cells):
            out_arenas[key][diff] = _items_from_cell(cell)
    return {
        "rewards_per_difficulty": {"Normal": 1, "Hard": 2, "Very Hard": 3, "Ultimate": 4},
        "junk_items_equal_weight": ["Sol Atomizer", "Moon Atomizer", "Star Atomizer"],
        "junk_meseta_weight": 6,
        "junk_meseta_label": "Meseta",
        "arenas": out_arenas,
    }


def parse_bpd2(wikitext: str) -> dict:
    i = wikitext.find("==Rewards==")
    if i < 0:
        raise ValueError("BPD2: no ==Rewards==")
    j = wikitext.find("==Enemy Counts==", i)
    if j < 0:
        raise ValueError("BPD2: no ==Enemy Counts==")
    chunk = wikitext[i:j]
    tbl = _first_wikitable_after(chunk, "==Rewards==")
    cells = _extract_data_row_cells(tbl)
    difficulties = ["Normal", "Hard", "Very Hard", "Ultimate"]
    if len(cells) != 4:
        raise ValueError(f"BPD2: expected 4 cells, got {len(cells)}")
    pools = {difficulties[k]: _items_from_cell(cells[k]) for k in range(4)}
    return {
        "rewards_per_difficulty": {"Normal": 1, "Hard": 1, "Very Hard": 2, "Ultimate": 2},
        "pools": pools,
    }


def main() -> None:
    w1 = fetch_wikitext("Black_Paper's_Dangerous_Deal")
    w2 = fetch_wikitext("Black_Paper's_Dangerous_Deal_2")
    doc = {
        "source": {
            "bpd1_wiki": WIKI_BPD1,
            "bpd2_wiki": WIKI_BPD2,
            "notes": [
                "BPD1: wiki — each reward roll draws from good pool for arena+difficulty plus junk; "
                "all outcomes weight 1 except Meseta weight 6.",
                "BPD2: wiki — uniform over listed items per roll (no junk).",
                "Meseta stack size from the quest is not modeled; meseta outcome uses meseta_reward_pd_if_known (default 0).",
            ],
        },
        "bpd1": parse_bpd1(w1),
        "bpd2": parse_bpd2(w2),
        "meseta_reward_pd_if_known": 0.0,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
