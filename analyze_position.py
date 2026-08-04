#!/usr/bin/env python3
"""Does the repetition benefit depend on where the target sits in the list?

Checks the Lost-in-the-Middle explanation against MiddleMatch, the only
category whose target position varies (NameIndex is always item 25 of 50).
Correctness is re-derived from the raw response text via scoring.score, so the
analysis does not trust the logged `correct` flags.

Usage: analyze_position.py <run_dir> [<run_dir> ...]
"""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import fisher_exact, spearmanr

from scoring import score

ROOT = Path(__file__).resolve().parent


def split_thirds(items: list) -> tuple[list, list, list]:
    """Items are (position, payload); sizes n//3, n//3, rest.

    Sorts by the full tuple so ties in position break by payload, not by input
    order — otherwise group membership at the boundaries would depend on the
    shuffled order of the run log.
    """
    ordered = sorted(items)
    k = len(ordered) // 3
    return ordered[:k], ordered[k:2 * k], ordered[2 * k:]


def perm_trend_p(pos: list[float], delta: list[int], nperm: int = 20000,
                 seed: int = 7) -> float:
    """Two-sided permutation test for a linear trend of delta against position."""
    mx = sum(pos) / len(pos)
    stat = lambda d: sum((x - mx) * v for x, v in zip(pos, d))
    obs = abs(stat(delta))
    rng = random.Random(seed)
    d2 = delta[:]
    hits = 0
    for _ in range(nperm):
        rng.shuffle(d2)
        if abs(stat(d2)) >= obs - 1e-12:
            hits += 1
    return (hits + 1) / (nperm + 1)


def fisher_middle_vs_edges(mid_ok: int, mid_n: int, edge_ok: int, edge_n: int) -> float:
    """Exact two-sided test: is baseline accuracy in the middle third different?"""
    return float(fisher_exact([[mid_ok, mid_n - mid_ok],
                               [edge_ok, edge_n - edge_ok]])[1])


def load_pairs(run_dir: Path, tasks: dict) -> dict:
    """task_id -> {condition: majority-vote correctness re-scored from raw text}."""
    agg: dict = defaultdict(lambda: defaultdict(list))
    for line in (run_dir / "raw_runs.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("phase") != "main" or r["condition"] not in ("baseline", "repeat_2"):
            continue
        t = tasks[r["task_id"]]
        ok = score(r["response_text"], str(t["expected"]), t["answer_type"]).correct
        agg[r["task_id"]][r["condition"]].append(ok)
    return {tid: {c: sum(v) * 2 > len(v) for c, v in conds.items()}
            for tid, conds in agg.items()}


def analyse(run_dir: Path, tasks: dict) -> dict:
    pairs = load_pairs(run_dir, tasks)
    ids = [i for i in pairs if tasks[i]["category"].startswith("middle_match")
           and "baseline" in pairs[i] and "repeat_2" in pairs[i]]
    pos = {i: tasks[i]["metadata"]["target_position_zero_based"]
           / (tasks[i]["metadata"]["n"] - 1) for i in ids}
    delta = {i: int(pairs[i]["repeat_2"]) - int(pairs[i]["baseline"]) for i in ids}

    thirds = split_thirds([(pos[i], i) for i in ids])
    rows = []
    for name, grp in zip(("first", "middle", "last"), thirds):
        g = [i for _, i in grp]
        b = sum(pairs[i]["baseline"] for i in g)
        rows.append({"third": name, "n": len(g), "baseline_ok": b,
                     "baseline_pct": 100 * b / len(g),
                     "delta_pp": 100 * sum(delta[i] for i in g) / len(g)})

    p_u = fisher_middle_vs_edges(
        rows[1]["baseline_ok"], rows[1]["n"],
        rows[0]["baseline_ok"] + rows[2]["baseline_ok"], rows[0]["n"] + rows[2]["n"])
    xs = [pos[i] for i in ids]
    ds = [delta[i] for i in ids]
    rho, p_rho = spearmanr(xs, ds)
    return {
        "run": run_dir.name, "n_pairs": len(ids), "thirds": rows,
        "u_curve_fisher_p": p_u,
        "trend_spearman_rho": float(rho), "trend_spearman_p": float(p_rho),
        "trend_permutation_p": perm_trend_p(xs, ds),
    }


def main() -> int:
    tasks = {t["id"]: t for t in
             (json.loads(l) for l in (ROOT / "data" / "tasks.jsonl")
              .read_text(encoding="utf-8").splitlines() if l.strip())}
    for arg in sys.argv[1:]:
        run_dir = Path(arg) if Path(arg).is_absolute() else ROOT / arg
        res = analyse(run_dir, tasks)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        (run_dir / "position_analysis.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
