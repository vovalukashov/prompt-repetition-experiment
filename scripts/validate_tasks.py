#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

REQUIRED = {
    "id", "suite", "category", "language", "prompt",
    "expected", "answer_type", "metadata"
}
EXPECTED_COUNTS = {
    "name_index_en": 40,
    "name_index_ru": 40,
    "middle_match_en": 40,
    "middle_match_ru": 40,
    "receipt_total_ru": 12,
    "date_interval_ru": 12,
    "letter_count_ru": 12,
    "filter_record_ru": 12,
    "spanish_mcq_ru": 12,
}

def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/tasks.jsonl")
    rows = []
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSON on line {lineno}: {exc}")
            missing = REQUIRED - row.keys()
            if missing:
                raise SystemExit(f"Line {lineno} missing fields: {sorted(missing)}")
            if not str(row["prompt"]).strip() or str(row["expected"]) == "":
                raise SystemExit(f"Line {lineno} has empty prompt/expected")
            rows.append(row)

    ids = [r["id"] for r in rows]
    prompts = [r["prompt"] for r in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("Duplicate task IDs")
    if len(prompts) != len(set(prompts)):
        raise SystemExit("Duplicate prompts")

    counts = Counter(r["category"] for r in rows)
    if counts != Counter(EXPECTED_COUNTS):
        raise SystemExit(f"Unexpected category counts: {dict(counts)}")

    suites = Counter(r["suite"] for r in rows)
    if suites != Counter({"stress": 160, "practical": 60}):
        raise SystemExit(f"Unexpected suite counts: {dict(suites)}")

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"OK: {len(rows)} tasks")
    print(f"Categories: {dict(sorted(counts.items()))}")
    print(f"Suites: {dict(suites)}")
    print(f"SHA-256: {digest}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
