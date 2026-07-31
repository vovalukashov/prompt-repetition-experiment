#!/usr/bin/env python3
"""Compares every repetition variant against baseline within one run.

The primary pipeline (analyze.py) answers one question: baseline vs repeat_2.
This one handles a run that carries several repetition conditions at once, so
each variant is paired against baseline on exactly the same tasks.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from analyze import fmt_p  # noqa: E402
from scoring import exact_mcnemar_p, interpretation_label, paired_bootstrap_ci  # noqa: E402

ROOT = Path(__file__).resolve().parent
SUITES = ("stress", "practical")
COLORS = {"baseline": "#6b7280", "repeat_2": "#2563eb",
          "repeat_3": "#7c3aed", "repeat_verbose": "#ea580c"}


def build_tasks(rows: list[dict]) -> dict[str, dict]:
    tasks: dict[str, dict] = {}
    for r in rows:
        if r.get("phase") != "main":
            continue
        t = tasks.setdefault(r["task_id"], {
            "task_id": r["task_id"], "suite": r["suite"], "category": r["category"],
            "language": r["language"], "expected": r["expected"], "by_condition": {},
        })
        t["by_condition"][r["condition"]] = r
    return tasks


def compare(tasks: list[dict], variant: str, resamples: int, seed: int) -> dict:
    usable = [t for t in tasks if "baseline" in t["by_condition"] and variant in t["by_condition"]]
    n = len(usable)
    if n == 0:
        return {"n": 0}
    pairs = [(t["by_condition"]["baseline"]["correct"], t["by_condition"][variant]["correct"])
             for t in usable]
    b = sum(x for x, _ in pairs)
    v = sum(y for _, y in pairs)
    fixed = sum(1 for x, y in pairs if not x and y)
    broken = sum(1 for x, y in pairs if x and not y)
    delta_pp = 100 * (v - b) / n
    p = exact_mcnemar_p(fixed, broken)
    ci = paired_bootstrap_ci(pairs, resamples=resamples, seed=seed)
    return {
        "n": n, "baseline_correct": b, "variant_correct": v,
        "baseline_accuracy": b / n, "variant_accuracy": v / n, "delta_pp": delta_pp,
        "fixed": fixed, "broken": broken,
        "mcnemar_exact_p": p, "bootstrap_ci_95_pp": [ci[0], ci[1]],
        "verdict": interpretation_label(delta_pp, p, ci),
    }


def per_condition_efficiency(rows: list[dict], conditions: list[str]) -> dict:
    out = {}
    for cond in conditions:
        sel = [r for r in rows if r.get("phase") == "main" and r["condition"] == cond
               and r.get("error") is None]
        if not sel:
            continue
        lat = sorted(r["latency_ms"] for r in sel if r["latency_ms"] is not None)
        tin = [r["input_tokens"] for r in sel if r["input_tokens"] is not None]
        out[cond] = {
            "n": len(sel),
            "input_tokens_total": sum(tin),
            "input_tokens_mean": statistics.fmean(tin) if tin else None,
            "output_tokens_total": sum(r["output_tokens"] or 0 for r in sel),
            "thoughts_tokens_total": sum(r["thoughts_tokens"] or 0 for r in sel),
            "latency_ms_median": statistics.median(lat) if lat else None,
            "cost_usd_total": sum(r["cost_usd"] or 0 for r in sel),
            "parse_errors": sum(1 for r in sel if r.get("parse_error")),
            "truncated": sum(1 for r in sel if r.get("finish_reason") == "MAX_TOKENS"),
        }
    base = out.get("baseline", {}).get("input_tokens_mean")
    for cond, d in out.items():
        d["input_token_ratio"] = (d["input_tokens_mean"] / base) if base else None
    return out


def table(rows: list[list[str]], head: list[str]) -> str:
    return "\n".join(["| " + " | ".join(head) + " |",
                      "|" + "|".join(["---"] * len(head)) + "|",
                      *["| " + " | ".join(r) + " |" for r in rows]])


def variant_row(name: str, m: dict) -> list[str]:
    if not m.get("n"):
        return [name, "0", "—", "—", "—", "—", "—", "—", "—"]
    lo, hi = m["bootstrap_ci_95_pp"]
    return [name, str(m["n"]),
            f"{m['baseline_correct']} ({100 * m['baseline_accuracy']:.1f}%)",
            f"{m['variant_correct']} ({100 * m['variant_accuracy']:.1f}%)",
            f"{m['delta_pp']:+.1f}", str(m["fixed"]), str(m["broken"]),
            fmt_p(m["mcnemar_exact_p"]), f"{lo:+.1f} … {hi:+.1f}"]


def make_chart(summary: dict, path: Path) -> None:
    conds = summary["conditions"]
    fig, axes = plt.subplots(1, len(SUITES), figsize=(11, 4.4), sharey=True)
    for ax, suite in zip(axes, SUITES):
        block = summary["by_suite"][suite]
        base_acc = 100 * block[conds[1]]["baseline_accuracy"] if block.get(conds[1], {}).get("n") else 0
        vals = [base_acc] + [100 * block[c]["variant_accuracy"] if block.get(c, {}).get("n") else 0
                             for c in conds[1:]]
        labels = ["baseline"] + conds[1:]
        ax.bar(labels, vals, color=[COLORS.get(c, "#999") for c in labels], width=0.6)
        for i, v in enumerate(vals):
            ax.text(i, v + 1.5, f"{v:.1f}%", ha="center", fontsize=9)
        n = block[conds[1]]["n"] if block.get(conds[1], {}).get("n") else 0
        ax.set_title(f"{suite} (n={n})", fontsize=11)
        ax.set_ylim(0, 100)
        ax.tick_params(axis="x", labelrotation=20, labelsize=9)
        ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("accuracy, %")
    fig.suptitle(f"Repetition variants — {summary['model_id']} ({summary['reasoning_mode']})",
                 fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir

    rows = [json.loads(x) for x in (out_dir / "raw_runs.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    meta = json.loads((out_dir / "run_meta.json").read_text())
    resamples = int(meta["experiment"]["bootstrap_resamples"])
    seed = int(meta["experiment"]["seed"])
    conditions = meta["experiment"].get("conditions") or ["baseline", "repeat_2"]
    variants = [c for c in conditions if c != "baseline"]

    tasks = list(build_tasks(rows).values())
    cats = sorted({t["category"] for t in tasks})
    summary = {
        "run_started_utc": meta["run_started_utc"],
        "provider": meta["model"]["provider"], "model_id": meta["model"]["model_id"],
        "reasoning_mode": meta["model"].get("reasoning_mode"),
        "reasoning_disable_method": meta["model"].get("reasoning_disable_method"),
        "dataset_sha256": meta["dataset_sha256"], "preset": meta["preset"],
        "conditions": conditions, "n_tasks": len(tasks),
        "overall": {v: compare(tasks, v, resamples, seed) for v in variants},
        "by_suite": {s: {v: compare([t for t in tasks if t["suite"] == s], v, resamples, seed)
                         for v in variants} for s in SUITES},
        "by_category": {c: {v: compare([t for t in tasks if t["category"] == c], v, resamples, seed)
                            for v in variants} for c in cats},
        "efficiency": per_condition_efficiency(rows, conditions),
        "spent_usd": meta.get("spent_usd"),
    }
    (out_dir / "ablation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    make_chart(summary, out_dir / "charts" / "ablation_variants.png")

    head = ["variant", "n", "baseline", "variant", "delta pp", "fixed", "broken", "McNemar p", "95% CI pp"]
    doc = [f"# Repetition variants — {summary['model_id']}", "",
           f"- Run (UTC): {summary['run_started_utc']}",
           f"- Reasoning mode: {summary['reasoning_mode']} ({summary['reasoning_disable_method']})",
           f"- Conditions: {', '.join(conditions)}",
           f"- Dataset SHA-256: {summary['dataset_sha256']}",
           f"- Tasks: {summary['n_tasks']}, spend: ${summary['spent_usd']:.4f}", "",
           "Every variant is paired against `baseline` on the same tasks inside this run, "
           "so the comparisons do not depend on the earlier primary run.", ""]
    for suite in SUITES:
        doc += [f"## {suite} suite", "",
                table([variant_row(v, summary["by_suite"][suite][v]) for v in variants], head), ""]
    doc += ["## All tasks", "", table([variant_row(v, summary["overall"][v]) for v in variants], head), ""]
    doc += ["## By category", ""]
    for c in cats:
        doc += [f"### {c}", "",
                table([variant_row(v, summary["by_category"][c][v]) for v in variants], head), ""]
    eff_head = ["condition", "requests", "mean input tokens", "input ratio",
                "output tokens", "thinking tokens", "median latency ms", "parse errors",
                "truncated", "cost USD"]
    eff_rows = [[c, str(d["n"]), f"{d['input_tokens_mean']:.1f}",
                 f"{d['input_token_ratio']:.3f}" if d["input_token_ratio"] else "—",
                 f"{d['output_tokens_total']:,}", f"{d['thoughts_tokens_total']:,}",
                 f"{d['latency_ms_median']:.0f}", str(d["parse_errors"]), str(d["truncated"]),
                 f"${d['cost_usd_total']:.5f}"]
                for c, d in summary["efficiency"].items()]
    doc += ["## Cost of each variant", "", table(eff_rows, eff_head), ""]
    (out_dir / "ablations.md").write_text("\n".join(doc))

    print(json.dumps({s: {v: {k: summary["by_suite"][s][v].get(k) for k in
                              ("n", "baseline_correct", "variant_correct", "delta_pp",
                               "fixed", "broken", "mcnemar_exact_p", "verdict")}
                          for v in variants} for s in SUITES}, ensure_ascii=False, indent=2))
    print("\nwrote:", out_dir / "ablations.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
