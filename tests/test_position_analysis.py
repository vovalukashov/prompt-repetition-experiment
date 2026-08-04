"""Tests for the target-position analysis (Lost-in-the-Middle check)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analyze_position import (  # noqa: E402
    fisher_middle_vs_edges,
    perm_trend_p,
    split_thirds,
)


def test_thirds_split_sizes_and_order():
    items = [(i / 79, f"t{i}") for i in range(80)]
    first, mid, last = split_thirds(items)
    assert (len(first), len(mid), len(last)) == (26, 26, 28)
    assert max(p for p, _ in first) <= min(p for p, _ in mid)
    assert max(p for p, _ in mid) <= min(p for p, _ in last)


def test_trend_detected_when_benefit_sits_in_the_first_third():
    # benefit only for targets early in the list -> negative trend, small p
    pos = [i / 79 for i in range(80)]
    delta = [1 if p < 0.33 else 0 for p in pos]
    p = perm_trend_p(pos, delta, nperm=5000, seed=1)
    assert p < 0.01


def test_no_trend_when_benefit_is_uniform():
    pos = [i / 79 for i in range(80)]
    delta = [1 if i % 3 == 0 else 0 for i in range(80)]  # unrelated to position
    p = perm_trend_p(pos, delta, nperm=5000, seed=1)
    assert p > 0.1


def test_perm_trend_is_deterministic_for_a_seed():
    pos = [i / 79 for i in range(80)]
    delta = [1 if p < 0.4 else -1 if p > 0.8 else 0 for p in pos]
    assert perm_trend_p(pos, delta, seed=42) == perm_trend_p(pos, delta, seed=42)


def test_fisher_flags_a_deep_middle_dip():
    # middle 1/26 correct vs edges 40/54 -> clearly significant
    p = fisher_middle_vs_edges(mid_ok=1, mid_n=26, edge_ok=40, edge_n=54)
    assert p < 0.001


def test_fisher_accepts_a_flat_profile():
    p = fisher_middle_vs_edges(mid_ok=11, mid_n=26, edge_ok=23, edge_n=54)
    assert p > 0.5
