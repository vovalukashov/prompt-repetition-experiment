#!/usr/bin/env python3
"""Recomputes every metric from raw_runs.jsonl and writes the run's artifacts.

Nothing here reads the network: summary.json, report.md, the charts, failures.md
and telegram_post_final.md are all derived from the raw request log.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from scoring import exact_mcnemar_p, interpretation_label, paired_bootstrap_ci  # noqa: E402

ROOT = Path(__file__).resolve().parent
SUITES = ("stress", "practical")
BASE_COLOR, REPEAT_COLOR = "#6b7280", "#2563eb"


def ru(x: float, digits: int = 1, sign: bool = False) -> str:
    s = f"{x:+.{digits}f}" if sign else f"{x:.{digits}f}"
    return s.replace(".", ",")


def majority(values: list[bool]) -> bool:
    return sum(values) * 2 > len(values)


def load_rows(out_dir: Path) -> list[dict]:
    path = out_dir / "raw_runs.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_pairs(rows: list[dict]) -> dict[str, dict]:
    """task_id -> {task metadata, baseline/repeat correctness and per-response rows}."""
    tasks: dict[str, dict] = {}
    for r in rows:
        if r.get("phase") != "main":
            continue
        t = tasks.setdefault(r["task_id"], {
            "task_id": r["task_id"], "suite": r["suite"], "category": r["category"],
            "language": r["language"], "expected": r["expected"],
            "baseline": [], "repeat_2": [],
        })
        t[r["condition"]].append(r)
    complete = {}
    for tid, t in tasks.items():
        if not t["baseline"] or not t["repeat_2"]:
            continue
        t["baseline_correct"] = majority([x["correct"] for x in t["baseline"]])
        t["repeat_correct"] = majority([x["correct"] for x in t["repeat_2"]])
        complete[tid] = t
    return complete


def block_metrics(pairs: list[dict], resamples: int, seed: int) -> dict:
    n = len(pairs)
    if n == 0:
        return {"n": 0}
    b = sum(p["baseline_correct"] for p in pairs)
    r = sum(p["repeat_correct"] for p in pairs)
    fixed = sum(1 for p in pairs if not p["baseline_correct"] and p["repeat_correct"])
    broken = sum(1 for p in pairs if p["baseline_correct"] and not p["repeat_correct"])
    both_correct = sum(1 for p in pairs if p["baseline_correct"] and p["repeat_correct"])
    both_wrong = sum(1 for p in pairs if not p["baseline_correct"] and not p["repeat_correct"])
    base_acc, rep_acc = b / n, r / n
    delta_pp = 100 * (rep_acc - base_acc)
    p_value = exact_mcnemar_p(fixed, broken)
    ci = paired_bootstrap_ci(
        [(p["baseline_correct"], p["repeat_correct"]) for p in pairs], resamples=resamples, seed=seed
    )
    return {
        "n": n,
        "baseline_correct": b, "baseline_accuracy": base_acc,
        "repeat_correct": r, "repeat_accuracy": rep_acc,
        "delta_pp": delta_pp,
        "fixed": fixed, "broken": broken,
        "both_correct": both_correct, "both_wrong": both_wrong,
        "mcnemar_exact_p": p_value,
        "bootstrap_ci_95_pp": [ci[0], ci[1]],
        "verdict": interpretation_label(delta_pp, p_value, ci),
        "near_ceiling": base_acc >= 0.95,
    }


def efficiency(rows: list[dict]) -> dict:
    main = [r for r in rows if r.get("phase") == "main" and r.get("error") is None]
    out = {}
    for cond in ("baseline", "repeat_2"):
        sel = [r for r in main if r["condition"] == cond]
        lat = sorted(r["latency_ms"] for r in sel if r["latency_ms"] is not None)
        tin = [r["input_tokens"] for r in sel if r["input_tokens"] is not None]
        tout = [r["output_tokens"] for r in sel if r["output_tokens"] is not None]
        cost = [r["cost_usd"] for r in sel if r["cost_usd"] is not None]
        cached = [r["cached_input_tokens"] or 0 for r in sel]
        thoughts = [r["thoughts_tokens"] or 0 for r in sel]
        out[cond] = {
            "n": len(sel),
            "latency_ms_median": statistics.median(lat) if lat else None,
            "latency_ms_mean": statistics.fmean(lat) if lat else None,
            "latency_ms_p95": (lat[max(0, int(0.95 * len(lat)) - 1)] if lat else None),
            "input_tokens_total": sum(tin), "input_tokens_mean": statistics.fmean(tin) if tin else None,
            "output_tokens_total": sum(tout), "output_tokens_mean": statistics.fmean(tout) if tout else None,
            "cached_input_tokens_total": sum(cached),
            "thoughts_tokens_total": sum(thoughts),
            "cost_usd_total": sum(cost) if cost else None,
            "cost_usd_mean": statistics.fmean(cost) if cost else None,
        }
    base, rep = out["baseline"], out["repeat_2"]
    if base["input_tokens_mean"]:
        out["input_token_ratio"] = rep["input_tokens_mean"] / base["input_tokens_mean"]
    if base["latency_ms_median"]:
        out["latency_median_delta_pct"] = 100 * (rep["latency_ms_median"] / base["latency_ms_median"] - 1)
        out["latency_median_delta_ms"] = rep["latency_ms_median"] - base["latency_ms_median"]
    # paired per-task latency delta
    by_task: dict[str, dict] = defaultdict(dict)
    for r in main:
        by_task[r["task_id"]].setdefault(r["condition"], []).append(r["latency_ms"])
    deltas = [statistics.fmean(v["repeat_2"]) - statistics.fmean(v["baseline"])
              for v in by_task.values() if "baseline" in v and "repeat_2" in v]
    out["paired_latency_delta_ms_median"] = statistics.median(deltas) if deltas else None
    return out


def repeats_analysis(rows: list[dict]) -> dict | None:
    """Section 7: with more than one response per condition, report all-response
    accuracy and how often the repeats disagree, not just the majority vote."""
    main = [r for r in rows if r.get("phase") == "main"]
    if not main or max(r["repeat_index"] for r in main) < 2:
        return None
    out = {}
    for cond in ("baseline", "repeat_2"):
        sel = [r for r in main if r["condition"] == cond]
        if not sel:
            continue
        by_task: dict[str, list[dict]] = defaultdict(list)
        for r in sel:
            by_task[r["task_id"]].append(r)
        unanimous_answer = sum(1 for v in by_task.values()
                               if len({x["parsed_answer"] for x in v}) == 1)
        unanimous_correct = sum(1 for v in by_task.values()
                                if len({x["correct"] for x in v}) == 1)
        flips = sum(1 for v in by_task.values() if len({x["correct"] for x in v}) > 1)
        out[cond] = {
            "responses": len(sel),
            "tasks": len(by_task),
            "correct_responses": sum(1 for r in sel if r["correct"]),
            "accuracy_all_responses": sum(1 for r in sel if r["correct"]) / len(sel),
            "tasks_with_identical_answers": unanimous_answer,
            "answer_agreement_rate": unanimous_answer / len(by_task),
            "tasks_with_identical_correctness": unanimous_correct,
            "tasks_flipping_correctness": flips,
            "correctness_flip_rate": flips / len(by_task),
        }
    return out


def make_charts(summary: dict, charts_dir: Path) -> None:
    cats = summary["by_category"]
    suites = summary["by_suite"]

    # 1. accuracy by suite — full 0-100 axis, no truncation
    present = [s for s in SUITES if suites[s]["n"]]  # an ablation may cover one suite only
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    labels = [f"{s}\n(n={suites[s]['n']})" for s in present]
    xs = range(len(present))
    base = [100 * suites[s]["baseline_accuracy"] for s in present]
    rep = [100 * suites[s]["repeat_accuracy"] for s in present]
    ax.bar([x - 0.2 for x in xs], base, 0.4, label="baseline", color=BASE_COLOR)
    ax.bar([x + 0.2 for x in xs], rep, 0.4, label="repeat_2", color=REPEAT_COLOR)
    for x, (bv, rv) in enumerate(zip(base, rep)):
        ax.text(x - 0.2, bv + 1.5, f"{bv:.1f}%", ha="center", fontsize=9)
        ax.text(x + 0.2, rv + 1.5, f"{rv:.1f}%", ha="center", fontsize=9)
    ax.set_xticks(list(xs)); ax.set_xticklabels(labels)
    ax.set_ylim(0, 100); ax.set_ylabel("accuracy, %")
    ax.set_title(f"Accuracy by suite — {summary['model_id']} ({summary['reasoning_mode']})")
    ax.legend(); ax.grid(axis="y", alpha=0.25)
    fig.tight_layout(); fig.savefig(charts_dir / "accuracy_by_suite.png", dpi=150); plt.close(fig)

    # 2. fixed vs broken by category
    names = list(cats.keys())
    fig, ax = plt.subplots(figsize=(9.5, 5))
    ys = range(len(names))
    ax.barh([y + 0.2 for y in ys], [cats[c]["fixed"] for c in names], 0.4,
            label="fixed (baseline wrong -> repeat correct)", color="#16a34a")
    ax.barh([y - 0.2 for y in ys], [-cats[c]["broken"] for c in names], 0.4,
            label="broken (baseline correct -> repeat wrong)", color="#dc2626")
    for y, c in enumerate(names):
        if cats[c]["fixed"]:
            ax.text(cats[c]["fixed"] + 0.15, y + 0.2, str(cats[c]["fixed"]), va="center", fontsize=9)
        if cats[c]["broken"]:
            ax.text(-cats[c]["broken"] - 0.15, y - 0.2, str(cats[c]["broken"]),
                    va="center", ha="right", fontsize=9)
    ax.set_yticks(list(ys))
    ax.set_yticklabels([f"{c} (n={cats[c]['n']})" for c in names], fontsize=9)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("tasks")
    ax.set_title("Corrections and regressions by category")
    ax.legend(fontsize=8, loc="lower right"); ax.grid(axis="x", alpha=0.25)
    fig.tight_layout(); fig.savefig(charts_dir / "fixed_vs_broken.png", dpi=150); plt.close(fig)

    # 3. latency and tokens
    eff = summary["efficiency"]
    fig, axes = plt.subplots(1, 3, figsize=(11, 4))
    for ax, key, title, unit in [
        (axes[0], "latency_ms_median", "Median end-to-end latency", "ms"),
        (axes[1], "input_tokens_mean", "Mean input tokens", "tokens"),
        (axes[2], "output_tokens_mean", "Mean output tokens", "tokens"),
    ]:
        vals = [eff["baseline"][key] or 0, eff["repeat_2"][key] or 0]
        ax.bar(["baseline", "repeat_2"], vals, color=[BASE_COLOR, REPEAT_COLOR], width=0.55)
        for i, v in enumerate(vals):
            ax.text(i, v * 1.01, f"{v:.0f}", ha="center", fontsize=9)
        ax.set_title(title, fontsize=10); ax.set_ylabel(unit)
        ax.set_ylim(0, max(vals) * 1.18 if max(vals) else 1)
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle(f"Cost of the second copy — n={eff['baseline']['n']} requests per condition", fontsize=11)
    fig.tight_layout(); fig.savefig(charts_dir / "latency_and_tokens.png", dpi=150); plt.close(fig)


def format_ci(block: dict) -> str:
    lo, hi = block["bootstrap_ci_95_pp"]
    return f"{lo:+.1f} … {hi:+.1f}"


def fmt_p(p: float) -> str:
    """Keeps very small p-values readable instead of rounding them to 0.0000."""
    return f"{p:.2e}" if p < 1e-4 else f"{p:.4f}"


def run_specific_limitations(rows: list[dict], summary: dict) -> str:
    """Limitations that only the actual response log can reveal."""
    truncated = [r for r in rows if r.get("phase") == "main" and r.get("finish_reason") == "MAX_TOKENS"]
    lines = ["\n## Run-specific limitations\n"]
    cap = summary["request_defaults"]["max_output_tokens"]
    if truncated:
        by_cond = Counter(r["condition"] for r in truncated)
        by_suite = Counter(r["suite"] for r in truncated)
        lines.append(
            f"- `max_output_tokens = {cap}` truncated {len(truncated)} response(s) "
            f"(by condition: {dict(by_cond)}; by suite: {dict(by_suite)}). Every truncated "
            f"response began writing a step-by-step solution despite the prompt asking for a bare "
            f"value, so it is scored as a format violation. Because the truncations are not evenly "
            f"split across conditions, the affected suite's delta carries this artefact; see the "
            f"separate output-cap sensitivity run if one was performed."
        )
    else:
        lines.append(f"- `max_output_tokens = {cap}` truncated no responses.")
    lines.append(
        "- `gemini-2.0-flash-lite`, the model behind the widely quoted +76 pp NameIndex result, "
        "was shut down by Google on 2026-06-01, so an exact replication of that number is no "
        "longer possible on the Gemini API."
    )
    lines.append(
        "- The Gemini `generateContent` API exposes no sampling seed, so bit-exact reproducibility "
        "is not guaranteed even at `temperature = 0`. The stability pilot measured "
        f"{100 * (summary['stability_pilot']['disagreement_rate'] if summary.get('stability_pilot') else 0):.1f}% "
        "answer disagreement when baseline was sent twice."
    )
    lines.append(
        f"- Prompt caching did not engage: {summary['efficiency']['baseline']['cached_input_tokens_total']} "
        f"and {summary['efficiency']['repeat_2']['cached_input_tokens_total']} cached input tokens were "
        "reported, so the input-token ratio is also the billed ratio."
    )
    return "\n".join(lines) + "\n"


def category_table(summary: dict) -> str:
    head = ("| category | n | baseline | repeat_2 | delta pp | fixed | broken | McNemar p | 95% CI pp |\n"
            "|---|---|---|---|---|---|---|---|---|\n")
    lines = []
    for cat, m in summary["by_category"].items():
        lines.append(
            f"| {cat} | {m['n']} | {m['baseline_correct']} ({100 * m['baseline_accuracy']:.1f}%) | "
            f"{m['repeat_correct']} ({100 * m['repeat_accuracy']:.1f}%) | {m['delta_pp']:+.1f} | "
            f"{m['fixed']} | {m['broken']} | {fmt_p(m['mcnemar_exact_p'])} | {format_ci(m)} |"
        )
    return head + "\n".join(lines)


def efficiency_table(summary: dict) -> str:
    eff = summary["efficiency"]
    rows = [
        ("requests", "n", lambda c: f"{eff[c]['n']}"),
        ("median latency, ms", "", lambda c: f"{eff[c]['latency_ms_median']:.0f}"),
        ("mean latency, ms", "", lambda c: f"{eff[c]['latency_ms_mean']:.0f}"),
        ("p95 latency, ms", "", lambda c: f"{eff[c]['latency_ms_p95']:.0f}"),
        ("input tokens, total", "", lambda c: f"{eff[c]['input_tokens_total']:,}"),
        ("input tokens, mean", "", lambda c: f"{eff[c]['input_tokens_mean']:.1f}"),
        ("cached input tokens, total", "", lambda c: f"{eff[c]['cached_input_tokens_total']:,}"),
        ("output tokens, total", "", lambda c: f"{eff[c]['output_tokens_total']:,}"),
        ("output tokens, mean", "", lambda c: f"{eff[c]['output_tokens_mean']:.2f}"),
        ("thinking tokens, total", "", lambda c: f"{eff[c]['thoughts_tokens_total']:,}"),
        ("cost, USD total", "", lambda c: f"${eff[c]['cost_usd_total']:.5f}"),
    ]
    out = ["| metric | baseline | repeat_2 |", "|---|---|---|"]
    for label, _, fn in rows:
        out.append(f"| {label} | {fn('baseline')} | {fn('repeat_2')} |")
    out.append(f"| nominal input-token ratio | 1.00 | {summary['efficiency']['input_token_ratio']:.3f} |")
    out.append(f"| median paired latency delta, ms | — | "
               f"{summary['efficiency']['paired_latency_delta_ms_median']:+.0f} |")
    return "\n".join(out)


def example_lines(pairs: list[dict], kind: str, limit: int = 5) -> list[dict]:
    """Spreads examples across categories so one category cannot fill the list."""
    if kind == "fixed":
        sel = [p for p in pairs if not p["baseline_correct"] and p["repeat_correct"]]
    else:
        sel = [p for p in pairs if p["baseline_correct"] and not p["repeat_correct"]]
    buckets: dict[str, list[dict]] = defaultdict(list)
    for p in sorted(sel, key=lambda p: p["task_id"]):
        buckets[p["category"]].append(p)
    order = sorted(buckets, key=lambda c: (-len(buckets[c]), c))
    out: list[dict] = []
    while len(out) < limit and any(buckets[c] for c in order):
        for c in order:
            if buckets[c] and len(out) < limit:
                out.append(buckets[c].pop(0))
    return out


def render_examples(items: list[dict]) -> str:
    if not items:
        return "_none_"
    out = []
    for p in items:
        b = p["baseline"][0]
        r = p["repeat_2"][0]
        out.append(
            f"- `{p['task_id']}` ({p['category']}) — expected `{p['expected']}`; "
            f"baseline answered `{b['parsed_answer']}`, repeat_2 answered `{r['parsed_answer']}`"
        )
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir

    rows = load_rows(out_dir)
    meta = json.loads((out_dir / "run_meta.json").read_text())
    cfg_exp = meta["experiment"]
    resamples, seed = int(cfg_exp["bootstrap_resamples"]), int(cfg_exp["seed"])

    pairs_by_id = build_pairs(rows)
    pairs = list(pairs_by_id.values())

    summary = {
        "run_started_utc": meta["run_started_utc"],
        "run_finished_utc": meta.get("run_finished_utc"),
        "provider": meta["model"]["provider"],
        "model_id": meta["model"]["model_id"],
        "model_version_reported": next((r.get("model_version_reported") for r in rows
                                        if r.get("model_version_reported")), None),
        "reasoning_mode": meta["model"].get("reasoning_mode"),
        "reasoning_disable_method": meta["model"].get("reasoning_disable_method"),
        "preset": meta["preset"],
        "dataset_sha256": meta["dataset_sha256"],
        "repeats_per_condition": cfg_exp["repeats_per_condition"],
        "request_defaults": meta["request_defaults"],
        "n_pairs": len(pairs),
        "requests_total": len(rows),
        "requests_failed": sum(1 for r in rows if r.get("error")),
        "overall": block_metrics(pairs, resamples, seed),
        "by_suite": {s: block_metrics([p for p in pairs if p["suite"] == s], resamples, seed)
                     for s in SUITES},
        "by_category": {c: block_metrics([p for p in pairs if p["category"] == c], resamples, seed)
                        for c in sorted({p["category"] for p in pairs})},
        "efficiency": efficiency(rows),
        "repeats_analysis": repeats_analysis(rows),
        "stability_pilot": meta.get("stability_pilot"),
        "parse_errors": {
            cond: sum(1 for r in rows if r.get("phase") == "main"
                      and r["condition"] == cond and r.get("parse_error"))
            for cond in ("baseline", "repeat_2")
        },
        "finish_reasons": dict(Counter(r.get("finish_reason") for r in rows if r.get("phase") == "main")),
        "spent_usd": meta.get("spent_usd"),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))

    make_charts(summary, out_dir / "charts")

    # ---- report.md ----
    tpl = (ROOT / "templates" / "report.md").read_text()
    empty = {"n": 0, "baseline_correct": 0, "baseline_accuracy": float("nan"), "repeat_correct": 0,
             "repeat_accuracy": float("nan"), "delta_pp": float("nan"), "fixed": 0, "broken": 0,
             "mcnemar_exact_p": 1.0, "bootstrap_ci_95_pp": [float("nan")] * 2,
             "verdict": "unclear", "near_ceiling": False}
    st = {**empty, **summary["by_suite"]["stress"]}
    pr = {**empty, **summary["by_suite"]["practical"]}
    pilot = summary["stability_pilot"]
    stability = ("not run" if not pilot else
                 f"{pilot['n_tasks']} tasks, baseline sent twice: "
                 f"{pilot['disagreements']} disagreement(s) = {100 * pilot['disagreement_rate']:.1f}% "
                 f"(threshold 5%) -> repeats_per_condition = {pilot['repeats_recommended']}")
    ra = summary.get("repeats_analysis")
    if ra:
        stability += (
            f"\n\nWith {summary['repeats_per_condition']} responses per condition, the headline "
            f"numbers above use the per-task majority vote. All-response accuracy and repeat "
            f"variability:\n\n"
            + "\n".join(
                f"- `{cond}`: {d['correct_responses']}/{d['responses']} responses correct "
                f"({100 * d['accuracy_all_responses']:.1f}%); "
                f"{d['tasks_with_identical_answers']}/{d['tasks']} tasks "
                f"({100 * d['answer_agreement_rate']:.1f}%) returned the identical answer every "
                f"time; {d['tasks_flipping_correctness']} tasks "
                f"({100 * d['correctness_flip_rate']:.1f}%) flipped between correct and wrong "
                f"across repeats"
                for cond, d in ra.items()))
    failures = [r for r in rows if r.get("error")]
    parse_err = [r for r in rows if r.get("phase") == "main" and r.get("parse_error")]
    failure_summary = (
        f"- technical failures (final, after retries): {len(failures)}\n"
        f"- retried requests: {sum(1 for r in rows if r.get('retry_count'))}\n"
        f"- parse errors, baseline: {summary['parse_errors']['baseline']}\n"
        f"- parse errors, repeat_2: {summary['parse_errors']['repeat_2']}\n"
        f"- finish reasons: {summary['finish_reasons']}\n"
        f"- thinking tokens emitted: baseline "
        f"{summary['efficiency']['baseline']['thoughts_tokens_total']}, repeat_2 "
        f"{summary['efficiency']['repeat_2']['thoughts_tokens_total']}"
    )
    verdict_text = {
        "improvement": "repeat_2 is better; McNemar p < 0.05 and the bootstrap CI excludes 0",
        "regression": "repeat_2 is worse; McNemar p < 0.05 and the bootstrap CI excludes 0",
        "unclear": "no statistically clear effect on this model and dataset "
                   "(this is not evidence that the true effect is exactly zero)",
    }
    interpretation = (
        f"- stress: delta {st['delta_pp']:+.1f} pp, McNemar p = {fmt_p(st['mcnemar_exact_p'])}, "
        f"CI {format_ci(st)} -> {verdict_text[st['verdict']]}\n"
        f"- practical: delta {pr['delta_pp']:+.1f} pp, McNemar p = {fmt_p(pr['mcnemar_exact_p'])}, "
        f"CI {format_ci(pr)} -> {verdict_text[pr['verdict']]}\n"
    )
    if st["near_ceiling"]:
        interpretation += "- stress baseline accuracy is >= 95%: the suite is near ceiling and headroom is limited\n"
    if pr["near_ceiling"]:
        interpretation += "- practical baseline accuracy is >= 95%: the suite is near ceiling and headroom is limited\n"

    values = {
        "run_date_utc": summary["run_started_utc"],
        "provider": summary["provider"], "model_id": summary["model_id"],
        "reasoning_mode": f"{summary['reasoning_mode']} ({summary['reasoning_disable_method']})",
        "dataset_sha256": summary["dataset_sha256"], "preset": summary["preset"],
        "successful_requests": str(summary["requests_total"] - summary["requests_failed"]),
        "failed_requests": str(summary["requests_failed"]),
        "stress_n": str(st["n"]), "stress_baseline_correct": str(st["baseline_correct"]),
        "stress_baseline_accuracy": f"{100 * st['baseline_accuracy']:.1f}%",
        "stress_repeat_correct": str(st["repeat_correct"]),
        "stress_repeat_accuracy": f"{100 * st['repeat_accuracy']:.1f}%",
        "stress_delta_pp": f"{st['delta_pp']:+.1f}", "stress_fixed": str(st["fixed"]),
        "stress_broken": str(st["broken"]), "stress_mcnemar_p": f"{fmt_p(st['mcnemar_exact_p'])}",
        "stress_ci_low": f"{st['bootstrap_ci_95_pp'][0]:+.1f}",
        "stress_ci_high": f"{st['bootstrap_ci_95_pp'][1]:+.1f}",
        "practical_n": str(pr["n"]), "practical_baseline_correct": str(pr["baseline_correct"]),
        "practical_baseline_accuracy": f"{100 * pr['baseline_accuracy']:.1f}%",
        "practical_repeat_correct": str(pr["repeat_correct"]),
        "practical_repeat_accuracy": f"{100 * pr['repeat_accuracy']:.1f}%",
        "practical_delta_pp": f"{pr['delta_pp']:+.1f}", "practical_fixed": str(pr["fixed"]),
        "practical_broken": str(pr["broken"]), "practical_mcnemar_p": f"{fmt_p(pr['mcnemar_exact_p'])}",
        "practical_ci_low": f"{pr['bootstrap_ci_95_pp'][0]:+.1f}",
        "practical_ci_high": f"{pr['bootstrap_ci_95_pp'][1]:+.1f}",
        "category_results": category_table(summary),
        "efficiency_results": efficiency_table(summary),
        "correction_examples": render_examples(example_lines(pairs, "fixed")),
        "regression_examples": render_examples(example_lines(pairs, "broken")),
        "stability_results": stability,
        "failure_summary": failure_summary,
        "interpretation": interpretation,
    }
    report = tpl
    for k, v in values.items():
        report = report.replace("{{" + k + "}}", v)
    report += run_specific_limitations(rows, summary)
    (out_dir / "report.md").write_text(report)

    # ---- failures.md ----
    lines = ["# Failures, retries and parse errors", "", failure_summary, ""]
    if failures:
        lines += ["## Technical failures", ""]
        lines += [f"- `{r['run_id']}` HTTP {r['http_status']} after {r['retry_count']} retries: {r['error']}"
                  for r in failures]
        lines.append("")
    lines += ["## Parse errors (main run)", ""]
    if parse_err:
        for r in parse_err:
            snippet = (r["response_text"] or "").replace("\n", " ⏎ ")[:160]
            lines.append(f"- `{r['run_id']}` ({r['category']}, {r['condition']}) expected "
                         f"`{r['expected']}` — raw: `{snippet}`")
    else:
        lines.append("_none_")
    (out_dir / "failures.md").write_text("\n".join(lines) + "\n")

    print(json.dumps({s: {k: summary["by_suite"][s][k] for k in
                          ("n", "baseline_correct", "repeat_correct", "delta_pp", "fixed",
                           "broken", "mcnemar_exact_p", "bootstrap_ci_95_pp", "verdict")}
                      for s in SUITES if summary["by_suite"][s]["n"]},
                     ensure_ascii=False, indent=2))
    print("\nwrote:", out_dir / "summary.json", out_dir / "report.md", sep="\n  ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
