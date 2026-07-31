"""End-to-end smoke test of analyze.py + make_post.py on a synthetic run.

Exercises the whole artifact pipeline without spending a single API request, so
a formatting bug cannot surface only after the paid run.
"""
from __future__ import annotations

import json
import random
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = str(ROOT / ".venv" / "bin" / "python")


def synth_run(out_dir: Path, stress_delta: int, practical_delta: int) -> None:
    """Writes a raw_runs.jsonl whose pairing produces a known-ish effect size."""
    tasks = [json.loads(x) for x in (ROOT / "data" / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    rng = random.Random(7)
    (out_dir / "charts").mkdir(parents=True, exist_ok=True)
    rows = []
    counters = {"stress": 0, "practical": 0}
    for t in tasks:
        idx = counters[t["suite"]]
        counters[t["suite"]] += 1
        delta = stress_delta if t["suite"] == "stress" else practical_delta
        base_ok = idx % 2 == 0
        rep_ok = base_ok
        if idx < abs(delta):
            rep_ok = delta > 0 or not base_ok
            base_ok = delta < 0 or not rep_ok
        for cond, ok in (("baseline", base_ok), ("repeat_2", rep_ok)):
            n_in = 300 if cond == "baseline" else 600
            rows.append({
                "run_id": f"main-{t['id']}-{cond}-r1", "timestamp_utc": "2026-07-31T00:00:00.000Z",
                "phase": "main", "task_id": t["id"], "suite": t["suite"], "category": t["category"],
                "language": t["language"], "provider": "google", "model_id": "test-model",
                "model_version_reported": "test-model-001", "reasoning_mode": "disabled",
                "condition": cond, "pair_order": "AB", "repeat_index": 1,
                "prompt_sha256": "0" * 64, "request_payload_redacted": {},
                "response_text": t["expected"] if ok else "wrong",
                "finish_reason": "STOP",
                "parsed_answer": str(t["expected"]) if ok else "wrong",
                "expected": str(t["expected"]), "correct": ok, "parse_error": False,
                "latency_ms": rng.uniform(400, 900) * (1.15 if cond == "repeat_2" else 1.0),
                "latency_ms_with_retries": 500.0,
                "input_tokens": n_in, "output_tokens": 5, "cached_input_tokens": 0,
                "thoughts_tokens": 0, "cost_usd": n_in / 1e6 * 0.1,
                "http_status": 200, "retry_count": 0, "error": None, "attempts": [],
            })
    (out_dir / "raw_runs.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    (out_dir / "run_meta.json").write_text(json.dumps({
        "run_started_utc": "2026-07-31T00:00:00.000Z", "run_finished_utc": "2026-07-31T00:20:00.000Z",
        "preset": "standard", "n_tasks": len(tasks), "dataset_sha256": "a" * 64,
        "model": {"provider": "google", "model_id": "test-model", "reasoning_mode": "disabled",
                  "reasoning_disable_method": "generationConfig.thinkingConfig.thinkingBudget=0"},
        "request_defaults": {"temperature": 0, "max_output_tokens": 64},
        "experiment": {"seed": 20260731, "bootstrap_resamples": 2000, "repeats_per_condition": 1},
        "warmup": [], "stability_pilot": {"n_tasks": 20, "disagreements": 0,
                                          "disagreement_rate": 0.0, "repeats_recommended": 1, "rows": []},
        "spent_usd": 0.02,
    }, ensure_ascii=False), encoding="utf-8")


def run_pipeline(out_dir: Path) -> None:
    for cmd in (["analyze.py", str(out_dir)], ["make_post.py", str(out_dir)]):
        proc = subprocess.run([PY, str(ROOT / cmd[0]), *cmd[1:]], capture_output=True, text=True, cwd=ROOT)
        assert proc.returncode == 0, f"{cmd[0]} failed:\n{proc.stdout}\n{proc.stderr}"


@pytest.mark.parametrize("stress_delta,practical_delta", [(30, 2), (-12, 0), (0, 0)])
def test_pipeline_produces_every_artifact(tmp_path, stress_delta, practical_delta):
    out = tmp_path / "run"
    synth_run(out, stress_delta, practical_delta)
    run_pipeline(out)
    for name in ("summary.json", "report.md", "failures.md", "telegram_post_final.md",
                 "charts/accuracy_by_suite.png", "charts/fixed_vs_broken.png",
                 "charts/latency_and_tokens.png"):
        assert (out / name).exists(), f"missing artifact: {name}"


def test_no_placeholders_survive_in_report_or_post(tmp_path):
    out = tmp_path / "run"
    synth_run(out, 30, 2)
    run_pipeline(out)
    for name in ("report.md", "telegram_post_final.md"):
        text = (out / name).read_text()
        assert "{{" not in text and "}}" not in text, f"{name} still has placeholders"


def test_summary_pairs_every_task_and_matches_raw_counts(tmp_path):
    out = tmp_path / "run"
    synth_run(out, 30, 2)
    run_pipeline(out)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["n_pairs"] == 220
    assert summary["by_suite"]["stress"]["n"] == 160
    assert summary["by_suite"]["practical"]["n"] == 60
    rows = [json.loads(x) for x in (out / "raw_runs.jsonl").read_text().splitlines()]
    base_correct = sum(1 for r in rows if r["condition"] == "baseline" and r["correct"] and r["suite"] == "stress")
    assert summary["by_suite"]["stress"]["baseline_correct"] == base_correct


def test_large_positive_effect_is_reported_as_improvement(tmp_path):
    out = tmp_path / "run"
    synth_run(out, 30, 0)
    run_pipeline(out)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["by_suite"]["stress"]["verdict"] == "improvement"
    assert summary["by_suite"]["stress"]["delta_pp"] > 0


def test_negative_effect_is_reported_as_regression(tmp_path):
    out = tmp_path / "run"
    synth_run(out, -12, 0)
    run_pipeline(out)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["by_suite"]["stress"]["verdict"] == "regression"


def test_zero_effect_is_reported_as_unclear(tmp_path):
    out = tmp_path / "run"
    synth_run(out, 0, 0)
    run_pipeline(out)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["by_suite"]["stress"]["verdict"] == "unclear"


def test_post_length_is_within_the_telegram_guideline(tmp_path):
    out = tmp_path / "run"
    synth_run(out, 30, 2)
    run_pipeline(out)
    n = len((out / "telegram_post_final.md").read_text())
    assert 2500 <= n <= 4000, f"post is {n} characters, outside 2500-4000"
