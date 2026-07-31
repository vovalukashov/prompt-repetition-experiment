#!/usr/bin/env python3
"""Paired A/B runner: baseline vs repeat_2, one request per condition per task.

Implements sections 5-10 of EXPERIMENT_SPEC.md. Every request is an independent
single-turn call with no history, no system prompt and no tools.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

from scoring import CONDITIONS, build_condition_prompt, score

ROOT = Path(__file__).resolve().parent
RETRYABLE_STATUS = {408, 409, 429}
WARMUP_PROMPT = "Reply with the single word: ready."

QUICK_STRESS_PER_CATEGORY = 15
QUICK_PRACTICAL_PER_CATEGORY = 4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        m = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
        if m and not os.environ.get(m.group(1)):
            os.environ[m.group(1)] = m.group(2).strip().strip('"').strip("'")


def load_tasks(path: Path, preset: str) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if preset == "standard":
        return rows
    if preset != "quick":
        raise SystemExit(f"unknown preset: {preset}")
    kept, seen = [], {}
    for row in rows:
        limit = QUICK_STRESS_PER_CATEGORY if row["suite"] == "stress" else QUICK_PRACTICAL_PER_CATEGORY
        n = seen.get(row["category"], 0)
        if n < limit:
            kept.append(row)
            seen[row["category"]] = n + 1
    return kept


class GeminiAdapter:
    """Direct Google Generative Language API, generateContent."""

    def __init__(self, model_cfg: dict, defaults: dict, timeout: float):
        self.cfg = model_cfg
        self.defaults = defaults
        self.model_id = model_cfg["model_id"]
        self.provider = model_cfg["provider"]
        self.url = f"{model_cfg['base_url'].rstrip('/')}/models/{self.model_id}:generateContent"
        key = os.environ.get(model_cfg["api_key_env"])
        if not key:
            raise SystemExit(f"environment variable {model_cfg['api_key_env']} is not set")
        self._key = key
        self.client = httpx.Client(timeout=timeout)

    def build_payload(self, user_content: str) -> dict:
        generation_config: dict = {
            "temperature": self.defaults["temperature"],
            "maxOutputTokens": self.defaults["max_output_tokens"],
            "candidateCount": 1,
        }
        # 2.5 Flash-Lite takes thinkingBudget=0; 3.x rejects it and has no "off"
        # level, so the strongest available setting there is thinkingLevel=minimal.
        thinking = self.cfg.get("thinking_config")
        if thinking:
            generation_config["thinkingConfig"] = dict(thinking)
        elif self.cfg.get("reasoning_mode") == "disabled":
            generation_config["thinkingConfig"] = {"thinkingBudget": 0}
        generation_config.update(self.cfg.get("request_overrides", {}))
        # No systemInstruction, no tools: the user turn is the entire request.
        return {
            "contents": [{"role": "user", "parts": [{"text": user_content}]}],
            "generationConfig": generation_config,
        }

    def redacted(self, payload: dict) -> dict:
        return {
            "method": "POST",
            "url": self.url,
            "headers": {"x-goog-api-key": "<redacted>", "content-type": "application/json"},
            "body": payload,
        }

    def call(self, payload: dict) -> tuple[int, dict | None, float, str | None]:
        """Returns (http_status, parsed_json, latency_ms, error)."""
        start = time.monotonic()
        try:
            resp = self.client.post(
                self.url,
                headers={"x-goog-api-key": self._key, "content-type": "application/json"},
                json=payload,
            )
        except httpx.HTTPError as exc:
            return (0, None, (time.monotonic() - start) * 1000, f"{type(exc).__name__}: {exc}")
        latency_ms = (time.monotonic() - start) * 1000
        try:
            body = resp.json()
        except ValueError:
            return (resp.status_code, None, latency_ms, "invalid JSON in response body")
        return (resp.status_code, body, latency_ms, None)

    @staticmethod
    def extract_text(body: dict) -> str | None:
        candidates = body.get("candidates") or []
        if not candidates:
            return None
        parts = (candidates[0].get("content") or {}).get("parts") or []
        texts = [p["text"] for p in parts if isinstance(p, dict) and "text" in p]
        return "".join(texts) if texts else None

    @staticmethod
    def usage(body: dict) -> dict:
        u = body.get("usageMetadata") or {}
        return {
            "input_tokens": u.get("promptTokenCount"),
            "output_tokens": u.get("candidatesTokenCount"),
            "cached_input_tokens": u.get("cachedContentTokenCount", 0),
            "thoughts_tokens": u.get("thoughtsTokenCount", 0),
            "total_tokens": u.get("totalTokenCount"),
        }


def cost_usd(usage: dict, pricing: dict) -> float | None:
    pin, pout = pricing.get("input_per_million_usd"), pricing.get("output_per_million_usd")
    if pin is None or pout is None or usage["input_tokens"] is None:
        return None
    cached = usage.get("cached_input_tokens") or 0
    pcached = pricing.get("cached_input_per_million_usd")
    fresh_in = max(0, (usage["input_tokens"] or 0) - cached)
    out = (usage.get("output_tokens") or 0) + (usage.get("thoughts_tokens") or 0)
    total = fresh_in / 1e6 * pin + out / 1e6 * pout
    if cached and pcached is not None:
        total += cached / 1e6 * pcached
    return total


class Runner:
    def __init__(self, cfg: dict, out_dir: Path):
        self.cfg = cfg
        self.exp = cfg["experiment"]
        self.model_cfg = cfg["models"][0]
        self.pricing = self.model_cfg.get("pricing") or {}
        self.adapter = GeminiAdapter(
            self.model_cfg, cfg["request_defaults"], float(self.exp["request_timeout_seconds"])
        )
        self.out_dir = out_dir
        self.raw_path = out_dir / "raw_runs.jsonl"
        self.requests_made = 0
        self.spent_usd = 0.0
        self.rng = random.Random(self.exp["seed"])

    def _guard(self) -> None:
        if self.requests_made >= self.exp["max_total_requests"]:
            raise SystemExit(f"request cap reached ({self.exp['max_total_requests']})")
        cap = self.exp.get("max_budget_usd")
        if cap is not None and self.spent_usd > float(cap):
            raise SystemExit(f"budget cap exceeded: ${self.spent_usd:.4f} > ${cap}")

    def request_with_retries(self, user_content: str) -> dict:
        """One logical request; retries only technical failures."""
        payload = self.adapter.build_payload(user_content)
        attempts: list[dict] = []
        total_ms = 0.0
        max_retries = int(self.exp["max_retries"])
        for attempt in range(1, max_retries + 1):
            self._guard()
            status, body, latency_ms, error = self.adapter.call(payload)
            self.requests_made += 1
            total_ms += latency_ms
            attempts.append({"attempt": attempt, "http_status": status, "error": error,
                             "latency_ms": round(latency_ms, 3)})
            technical = (
                error is not None
                or status in RETRYABLE_STATUS
                or status >= 500
                or body is None
            )
            if not technical:
                return {"ok": True, "status": status, "body": body, "latency_ms": latency_ms,
                        "total_ms": total_ms, "attempts": attempts, "payload": payload}
            if attempt < max_retries:
                delay = min(30.0, 1.5 * (2 ** (attempt - 1))) * (0.5 + self.rng.random())
                time.sleep(delay)
        return {"ok": False, "status": attempts[-1]["http_status"], "body": None,
                "latency_ms": attempts[-1]["latency_ms"], "total_ms": total_ms,
                "attempts": attempts, "payload": payload,
                "error": attempts[-1]["error"] or f"HTTP {attempts[-1]['http_status']}"}

    def execute(self, task: dict, condition: str, pair_order: str, repeat_index: int,
                phase: str, condition_order: list[str] | None = None) -> dict:
        user_content = build_condition_prompt(task["prompt"], condition, task["language"])
        result = self.request_with_retries(user_content)
        body = result["body"] or {}
        text = self.adapter.extract_text(body) if result["ok"] else None
        usage = self.adapter.usage(body) if result["ok"] else {
            "input_tokens": None, "output_tokens": None, "cached_input_tokens": None,
            "thoughts_tokens": None, "total_tokens": None}
        scored = score(text, str(task["expected"]), task["answer_type"])
        cost = cost_usd(usage, self.pricing) if result["ok"] else None
        if cost:
            self.spent_usd += cost
        finish_reason = None
        if body.get("candidates"):
            finish_reason = body["candidates"][0].get("finishReason")
        row = {
            "run_id": f"{phase}-{task['id']}-{condition}-r{repeat_index}",
            "timestamp_utc": utc_now(),
            "phase": phase,
            "task_id": task["id"],
            "suite": task["suite"],
            "category": task["category"],
            "language": task["language"],
            "provider": self.adapter.provider,
            "model_id": self.adapter.model_id,
            "model_version_reported": body.get("modelVersion"),
            "reasoning_mode": self.model_cfg.get("reasoning_mode"),
            "condition": condition,
            "pair_order": pair_order,
            "condition_order": condition_order,
            "repeat_index": repeat_index,
            "prompt_sha256": hashlib.sha256(user_content.encode("utf-8")).hexdigest(),
            "request_payload_redacted": self.adapter.redacted(result["payload"]),
            "response_text": text,
            "finish_reason": finish_reason,
            "parsed_answer": scored.parsed_answer,
            "expected": str(task["expected"]),
            "correct": scored.correct,
            "parse_error": scored.parse_error,
            "latency_ms": round(result["latency_ms"], 3),
            "latency_ms_with_retries": round(result["total_ms"], 3),
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
            "cached_input_tokens": usage["cached_input_tokens"],
            "thoughts_tokens": usage["thoughts_tokens"],
            "cost_usd": cost,
            "http_status": result["status"],
            "retry_count": len(result["attempts"]) - 1,
            "error": result.get("error"),
            "attempts": result["attempts"],
        }
        with self.raw_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    def warmup(self) -> list[dict]:
        out = []
        for i in range(int(self.exp["warmup_requests"])):
            res = self.request_with_retries(WARMUP_PROMPT)
            out.append({"i": i + 1, "http_status": res["status"],
                        "latency_ms": round(res["latency_ms"], 3), "ok": res["ok"]})
            print(f"  warmup {i + 1}/{self.exp['warmup_requests']}: "
                  f"HTTP {res['status']} {res['latency_ms']:.0f} ms", flush=True)
        return out

    def stability_pilot(self, tasks: list[dict]) -> dict:
        """Baseline sent twice on a fixed subsample; measures answer instability."""
        n = int(self.exp.get("stability_pilot_tasks", 20))
        sample = random.Random(self.exp["seed"] + 1).sample(tasks, min(n, len(tasks)))
        disagreements, rows = 0, []
        for i, task in enumerate(sample, 1):
            a = self.execute(task, "baseline", "AB", 1, "pilot")
            b = self.execute(task, "baseline", "AB", 2, "pilot")
            same = a["parsed_answer"] == b["parsed_answer"]
            disagreements += 0 if same else 1
            rows.append({"task_id": task["id"], "answer_1": a["parsed_answer"],
                         "answer_2": b["parsed_answer"], "agree": same})
            print(f"  pilot {i}/{len(sample)} {task['id']}: "
                  f"{'same' if same else 'DIFFERENT'}", flush=True)
        rate = disagreements / len(sample) if sample else 0.0
        return {"n_tasks": len(sample), "disagreements": disagreements,
                "disagreement_rate": rate, "threshold": 0.05,
                "repeats_recommended": 3 if rate > 0.05 else 1, "rows": rows}

    def main_run(self, tasks: list[dict], repeats: int, conditions: list[str]) -> None:
        order_rng = random.Random(self.exp["seed"])
        shuffled = tasks[:]
        order_rng.shuffle(shuffled)
        # Each task gets its own condition order so position in the sequence cannot
        # be confounded with the condition.
        plan = []
        for task in shuffled:
            order = conditions[:]
            order_rng.shuffle(order)
            plan.append((task, order))
        total = len(plan) * len(conditions) * repeats
        done = 0
        t0 = time.monotonic()
        for task, order in plan:
            pair_order = "AB" if order.index("baseline") == 0 else "BA"
            for repeat_index in range(1, repeats + 1):
                for condition in order:
                    row = self.execute(task, condition, pair_order, repeat_index, "main", order)
                    done += 1
                    if done % 20 == 0 or done == total:
                        elapsed = time.monotonic() - t0
                        eta = elapsed / done * (total - done)
                        print(f"  {done}/{total} requests | ${self.spent_usd:.4f} | "
                              f"ETA {eta / 60:.1f} min", flush=True)
                    if row["error"]:
                        print(f"  ! {row['run_id']}: {row['error']}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--preset", default=None, help="override config preset")
    ap.add_argument("--probe", action="store_true", help="single request, print raw response, exit")
    ap.add_argument("--pilot-only", action="store_true")
    ap.add_argument("--skip-pilot", action="store_true")
    ap.add_argument("--suite", choices=("stress", "practical"), default=None,
                    help="ablation: restrict the run to one suite")
    ap.add_argument("--max-output-tokens", type=int, default=None,
                    help="ablation: override the output cap")
    ap.add_argument("--tag", default=None, help="suffix for the output directory name")
    ap.add_argument("--conditions", default="baseline,repeat_2",
                    help=f"comma-separated subset of {','.join(CONDITIONS)}")
    ap.add_argument("--model", default=None, help="label of the model entry in config.yaml")
    ap.add_argument("--max-requests", type=int, default=None, help="override the runaway guard")
    ap.add_argument("--repeats", type=int, default=None,
                    help="pin repeats_per_condition instead of letting the pilot choose")
    args = ap.parse_args()

    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    unknown = [c for c in conditions if c not in CONDITIONS]
    if unknown or "baseline" not in conditions:
        raise SystemExit(f"invalid --conditions {conditions}: unknown={unknown}, baseline required")

    load_dotenv(ROOT / ".env")
    cfg = yaml.safe_load((ROOT / args.config).read_text())
    if args.preset:
        cfg["experiment"]["preset"] = args.preset
    if args.max_requests:
        cfg["experiment"]["max_total_requests"] = args.max_requests
    if args.model:
        chosen = [m for m in cfg["models"] if m["label"] == args.model]
        if not chosen:
            raise SystemExit(f"no model labelled {args.model!r} in {args.config}")
        cfg["models"] = chosen + [m for m in cfg["models"] if m["label"] != args.model]
    cfg["experiment"]["conditions"] = conditions
    preset = cfg["experiment"]["preset"]

    if args.max_output_tokens:
        cfg["request_defaults"]["max_output_tokens"] = args.max_output_tokens
    cfg["experiment"]["ablation"] = {"suite": args.suite, "tag": args.tag,
                                     "max_output_tokens": args.max_output_tokens}

    tasks_path = ROOT / "data" / "tasks.jsonl"
    dataset_sha = hashlib.sha256(tasks_path.read_bytes()).hexdigest()
    tasks = load_tasks(tasks_path, preset)
    if args.suite:
        tasks = [t for t in tasks if t["suite"] == args.suite]

    if args.probe:
        adapter = GeminiAdapter(cfg["models"][0], cfg["request_defaults"],
                                float(cfg["experiment"]["request_timeout_seconds"]))
        payload = adapter.build_payload(tasks[0]["prompt"].rstrip())
        status, body, latency, error = adapter.call(payload)
        print("HTTP", status, f"{latency:.0f} ms", "error:", error)
        print(json.dumps(body, ensure_ascii=False, indent=2)[:3000])
        return 0 if status == 200 else 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if args.tag:
        stamp = f"{stamp}-{args.tag}"
    out_dir = ROOT / cfg["output"]["root_dir"] / stamp
    (out_dir / "charts").mkdir(parents=True, exist_ok=True)
    (out_dir / "dataset.sha256").write_text(f"{dataset_sha}  data/tasks.jsonl\n")
    (out_dir / "config_resolved.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))

    runner = Runner(cfg, out_dir)
    print(f"model:   {runner.adapter.model_id} ({runner.adapter.provider})")
    print(f"preset:  {preset} — {len(tasks)} tasks")
    print(f"out:     {out_dir}")
    print("warm-up (not scored):", flush=True)
    warmup = runner.warmup()

    print("stability pilot:", flush=True)
    pilot = None if args.skip_pilot else runner.stability_pilot(tasks)
    repeats = int(cfg["experiment"]["repeats_per_condition"])
    if pilot:
        print(f"  disagreement: {pilot['disagreements']}/{pilot['n_tasks']} "
              f"= {pilot['disagreement_rate']:.1%}")
        repeats = pilot["repeats_recommended"]
        print(f"  -> repeats_per_condition = {repeats}")
    if args.repeats:
        repeats = args.repeats
        print(f"  pinned by --repeats: repeats_per_condition = {repeats}")
    cfg["experiment"]["repeats_per_condition"] = repeats

    meta = {
        "run_started_utc": utc_now(),
        "preset": preset,
        "n_tasks": len(tasks),
        "dataset_sha256": dataset_sha,
        "model": {k: v for k, v in runner.model_cfg.items() if k != "api_key_env"},
        "api_key_env": runner.model_cfg["api_key_env"],
        "request_defaults": cfg["request_defaults"],
        "experiment": cfg["experiment"],
        "warmup": warmup,
        "stability_pilot": pilot,
    }

    if args.pilot_only:
        (out_dir / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
        return 0

    print(f"main run: {len(tasks)} tasks x {len(conditions)} conditions "
          f"({', '.join(conditions)}) x {repeats} repeat(s)", flush=True)
    try:
        runner.main_run(tasks, repeats, conditions)
    finally:
        meta["run_finished_utc"] = utc_now()
        meta["requests_made"] = runner.requests_made
        meta["spent_usd"] = runner.spent_usd
        (out_dir / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"done: {runner.requests_made} requests, ${runner.spent_usd:.4f}")
    print(out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
