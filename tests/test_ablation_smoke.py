"""Smoke test for the multi-condition analyzer on a synthetic 4-condition run."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = str(ROOT / ".venv" / "bin" / "python")
CONDITIONS = ["baseline", "repeat_2", "repeat_3", "repeat_verbose"]
# accuracy each condition is built to hit, as a fraction of tasks
TARGET = {"baseline": 0.30, "repeat_2": 0.80, "repeat_3": 0.75, "repeat_verbose": 0.55}


def synth(out_dir: Path) -> list[dict]:
    tasks = [json.loads(x) for x in (ROOT / "data" / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    (out_dir / "charts").mkdir(parents=True, exist_ok=True)
    rows = []
    for i, t in enumerate(tasks):
        for cond in CONDITIONS:
            ok = (i % 100) < TARGET[cond] * 100
            n_in = 200 * (1 + CONDITIONS.index(cond))
            rows.append({
                "run_id": f"main-{t['id']}-{cond}-r1", "timestamp_utc": "2026-07-31T00:00:00.000Z",
                "phase": "main", "task_id": t["id"], "suite": t["suite"], "category": t["category"],
                "language": t["language"], "provider": "google", "model_id": "test-model",
                "reasoning_mode": "disabled", "condition": cond, "pair_order": "AB",
                "condition_order": CONDITIONS, "repeat_index": 1,
                "response_text": t["expected"] if ok else "wrong",
                "finish_reason": "STOP", "parsed_answer": str(t["expected"]) if ok else "wrong",
                "expected": str(t["expected"]), "correct": ok, "parse_error": False,
                "latency_ms": 500.0, "input_tokens": n_in, "output_tokens": 4,
                "cached_input_tokens": 0, "thoughts_tokens": 0, "cost_usd": n_in / 1e6 * 0.1,
                "http_status": 200, "retry_count": 0, "error": None, "attempts": [],
            })
    (out_dir / "raw_runs.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    (out_dir / "run_meta.json").write_text(json.dumps({
        "run_started_utc": "2026-07-31T00:00:00.000Z", "preset": "standard",
        "n_tasks": len(tasks), "dataset_sha256": "a" * 64,
        "model": {"provider": "google", "model_id": "test-model", "reasoning_mode": "disabled",
                  "reasoning_disable_method": "thinkingBudget=0"},
        "request_defaults": {"temperature": 0, "max_output_tokens": 64},
        "experiment": {"seed": 20260731, "bootstrap_resamples": 2000,
                       "repeats_per_condition": 1, "conditions": CONDITIONS},
        "warmup": [], "stability_pilot": None, "spent_usd": 0.05,
    }, ensure_ascii=False), encoding="utf-8")
    return rows


def run(out_dir: Path) -> None:
    proc = subprocess.run([PY, str(ROOT / "analyze_ablation.py"), str(out_dir)],
                          capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 0, f"analyze_ablation failed:\n{proc.stdout}\n{proc.stderr}"


def test_writes_summary_report_and_chart(tmp_path):
    out = tmp_path / "run"
    synth(out)
    run(out)
    for name in ("ablation_summary.json", "ablations.md", "charts/ablation_variants.png"):
        assert (out / name).exists(), f"missing {name}"


def test_every_variant_is_compared_against_baseline(tmp_path):
    out = tmp_path / "run"
    synth(out)
    run(out)
    s = json.loads((out / "ablation_summary.json").read_text())
    assert set(s["overall"]) == {"repeat_2", "repeat_3", "repeat_verbose"}
    for v, m in s["overall"].items():
        assert m["n"] == 220, f"{v} lost tasks in pairing"
        assert m["baseline_correct"] == s["overall"]["repeat_2"]["baseline_correct"]


def test_deltas_follow_the_synthesized_accuracies(tmp_path):
    out = tmp_path / "run"
    synth(out)
    run(out)
    s = json.loads((out / "ablation_summary.json").read_text())
    d = {v: s["overall"][v]["delta_pp"] for v in s["overall"]}
    assert d["repeat_2"] > d["repeat_3"] > d["repeat_verbose"] > 0


def test_input_token_ratio_is_relative_to_baseline(tmp_path):
    out = tmp_path / "run"
    synth(out)
    run(out)
    eff = json.loads((out / "ablation_summary.json").read_text())["efficiency"]
    assert eff["baseline"]["input_token_ratio"] == 1.0
    assert eff["repeat_2"]["input_token_ratio"] == 2.0
    assert eff["repeat_3"]["input_token_ratio"] == 3.0


def test_report_has_no_unfilled_placeholders(tmp_path):
    out = tmp_path / "run"
    synth(out)
    run(out)
    text = (out / "ablations.md").read_text()
    assert "{{" not in text and "{" not in text.replace("{{", "")
