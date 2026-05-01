"""
Tests for Section ID comparative-advantage helpers.
"""

import pytest

from quest_optimizer.id_advantage import (
    advantage_rows,
    advantage_rows_all_ids,
    build_quest_matrix,
    score_for_ranking_row,
)


def _sample_rank_by_section():
    return {
        "Pinkal": [
            {
                "quest_name": "Q1",
                "total_pd": 5.0,
                "pd_per_minute": 2.0,
                "top_items": [{"item": "Limiter"}],
            },
            {
                "quest_name": "Q2",
                "total_pd": 3.0,
                "pd_per_minute": 1.0,
                "top_items": [{"item": "V801"}],
            },
        ],
        "Redria": [
            {"quest_name": "Q1", "total_pd": 4.0, "pd_per_minute": 1.8, "top_items": [{"item": "Adept"}]},
            {"quest_name": "Q2", "total_pd": 6.0, "pd_per_minute": 1.2, "top_items": [{"item": "Heaven Striker"}]},
        ],
        "Whitill": [
            {"quest_name": "Q1", "total_pd": 3.5, "pd_per_minute": 1.6, "top_items": [{"item": "Liberta Kit"}]},
            {"quest_name": "Q2", "total_pd": 5.0, "pd_per_minute": 1.1, "top_items": [{"item": "Yasminkov"}]},
        ],
    }


def test_score_for_ranking_row_prefers_pd_per_minute():
    row = {"total_pd": 10.0, "pd_per_minute": 2.5}
    assert score_for_ranking_row(row) == 2.5


def test_score_for_ranking_row_falls_back_to_total_pd():
    row = {"total_pd": 10.0, "pd_per_minute": None}
    assert score_for_ranking_row(row) == 10.0


def test_build_quest_matrix():
    matrix = build_quest_matrix(_sample_rank_by_section())
    assert matrix["Q1"]["Pinkal"] == 2.0
    assert matrix["Q1"]["Redria"] == 1.8
    assert matrix["Q2"]["Whitill"] == 1.1


def test_advantage_rows_second_best_baseline_focus_winning():
    rows = advantage_rows(_sample_rank_by_section(), focus_id="Pinkal", baseline="second_best")
    q1 = next(row for row in rows if row["quest_name"] == "Q1")

    assert q1["best_id"] == "Pinkal"
    assert q1["edge_reference_id"] == "Redria"
    assert q1["edge_score"] == pytest.approx(0.2, rel=1e-9)
    assert q1["rank_among_ids"] == 1
    assert q1["top_item"]["item"] == "Limiter"


def test_advantage_rows_second_best_baseline_focus_not_winning():
    rows = advantage_rows(_sample_rank_by_section(), focus_id="Pinkal", baseline="second_best")
    q2 = next(row for row in rows if row["quest_name"] == "Q2")

    assert q2["best_id"] == "Redria"
    assert q2["edge_reference_id"] == "Redria"
    assert q2["edge_score"] == pytest.approx(-0.2, rel=1e-9)
    assert q2["rank_among_ids"] == 3


def test_advantage_rows_median_baseline():
    rows = advantage_rows(_sample_rank_by_section(), focus_id="Pinkal", baseline="median")
    q2 = next(row for row in rows if row["quest_name"] == "Q2")

    # Median of [1.0, 1.2, 1.1] is 1.1
    assert q2["edge_reference_id"] == "Median"
    assert q2["edge_score"] == pytest.approx(-0.1, rel=1e-9)


def test_advantage_rows_sorted_descending_by_edge():
    rows = advantage_rows(_sample_rank_by_section(), focus_id="Pinkal", baseline="second_best")
    assert rows[0]["edge_score"] >= rows[-1]["edge_score"]


def test_advantage_rows_invalid_baseline():
    with pytest.raises(ValueError):
        advantage_rows(_sample_rank_by_section(), focus_id="Pinkal", baseline="bad")


def test_advantage_rows_all_ids_top_n_per_id():
    sample = _sample_rank_by_section()
    by_id = advantage_rows_all_ids(
        sample,
        section_ids=["Pinkal", "Redria", "Whitill"],
        baseline="second_best",
        top_n=1,
    )
    assert len(by_id) == 3
    for _sid, rows in by_id.items():
        assert len(rows) == 1
