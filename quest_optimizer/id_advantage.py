"""
Helpers for computing Section ID comparative advantage per quest.
"""

from __future__ import annotations

from statistics import median
from typing import Dict, List, Optional


def score_for_ranking_row(row: Dict) -> float:
    """
    Match QuestOptimizer sorting behavior:
    use PD/min when available, otherwise total PD.
    """
    pd_per_minute = row.get("pd_per_minute")
    if pd_per_minute is not None:
        return float(pd_per_minute)
    return float(row.get("total_pd", 0.0))


def build_quest_matrix(rank_by_section: Dict[str, List[Dict]]) -> Dict[str, Dict[str, float]]:
    """
    Build quest -> section_id -> score map from rank_by_section_id output.
    """
    matrix: Dict[str, Dict[str, float]] = {}
    for section_id, rankings in rank_by_section.items():
        for row in rankings:
            quest_name = row.get("quest_name", "Unknown")
            if quest_name not in matrix:
                matrix[quest_name] = {}
            matrix[quest_name][section_id] = score_for_ranking_row(row)
    return matrix


def _row_lookup_by_quest(rank_by_section: Dict[str, List[Dict]]) -> Dict[str, Dict[str, Dict]]:
    """
    Build quest -> section_id -> original ranking row lookup.
    """
    lookup: Dict[str, Dict[str, Dict]] = {}
    for section_id, rankings in rank_by_section.items():
        for row in rankings:
            quest_name = row.get("quest_name", "Unknown")
            if quest_name not in lookup:
                lookup[quest_name] = {}
            lookup[quest_name][section_id] = row
    return lookup


def advantage_rows(rank_by_section: Dict[str, List[Dict]], focus_id: str, baseline: str = "second_best") -> List[Dict]:
    """
    Compute per-quest comparative advantage rows for a focus Section ID.

    baseline:
      - second_best: edge is versus best competitor if focus is #1, otherwise versus current #1.
      - median: edge is versus median score across IDs for the quest.
    """
    if baseline not in {"second_best", "median"}:
        raise ValueError("baseline must be 'second_best' or 'median'")

    matrix = build_quest_matrix(rank_by_section)
    row_lookup = _row_lookup_by_quest(rank_by_section)

    rows: List[Dict] = []
    for quest_name, score_by_id in matrix.items():
        if focus_id not in score_by_id:
            continue

        score_pairs = sorted(score_by_id.items(), key=lambda it: it[1], reverse=True)
        focus_score = score_by_id[focus_id]
        rank_among_ids = next((idx + 1 for idx, (sid, _score) in enumerate(score_pairs) if sid == focus_id), len(score_pairs))

        best_id, best_score = score_pairs[0]
        second_best_id, second_best_score = score_pairs[1] if len(score_pairs) > 1 else score_pairs[0]

        if baseline == "median":
            median_score = float(median(score_by_id.values()))
            edge = focus_score - median_score
            edge_reference_id = "Median"
            edge_reference_score = median_score
        else:
            if best_id == focus_id and len(score_pairs) > 1:
                edge_reference_id = second_best_id
                edge_reference_score = second_best_score
            else:
                edge_reference_id = best_id
                edge_reference_score = best_score
            edge = focus_score - edge_reference_score

        focus_row = row_lookup.get(quest_name, {}).get(focus_id, {})
        top_items = focus_row.get("top_items", [])
        top_item = top_items[0] if top_items else None

        long_name = focus_row.get("long_name")
        quest_display = f"{long_name} ({quest_name})" if long_name else quest_name

        rows.append(
            {
                "quest_name": quest_name,
                "quest_display": quest_display,
                "focus_id": focus_id,
                "focus_score": float(focus_score),
                "rank_among_ids": rank_among_ids,
                "best_id": best_id,
                "best_score": float(best_score),
                "second_best_id": second_best_id,
                "second_best_score": float(second_best_score),
                "edge_score": float(edge),
                "edge_reference_id": edge_reference_id,
                "edge_reference_score": float(edge_reference_score),
                "baseline": baseline,
                "top_item": top_item,
            }
        )

    rows.sort(key=lambda row: row["edge_score"], reverse=True)
    return rows


def advantage_rows_all_ids(
    rank_by_section: Dict[str, List[Dict]],
    section_ids: List[str],
    baseline: str = "second_best",
    top_n: Optional[int] = None,
) -> Dict[str, List[Dict]]:
    """
    For each Section ID, compute advantage_rows and optionally keep only the top N by edge score.
    """
    out: Dict[str, List[Dict]] = {}
    for sid in section_ids:
        rows = advantage_rows(rank_by_section, focus_id=sid, baseline=baseline)
        if top_n is not None:
            rows = rows[:top_n]
        out[sid] = rows
    return out
