"""Deterministic answer parsing, scoring and paired statistics.

Implements section 11 (parsing) and section 12 (metrics) of EXPERIMENT_SPEC.md.
No LLM is involved in grading: every answer is compared against the dataset's
`expected` value by code.
"""
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import numpy as np

QUOTE_PAIRS = [('"', '"'), ("'", "'"), ("«", "»"), ("“", "”"), ("‘", "’"), ("`", "`")]
TRAILING_MARKS = ".,;:"
INT_RE = re.compile(r"-?\d+")
DEC_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
CHOICE_RE = re.compile(r"(?<![A-Za-z])([A-Da-d])(?![A-Za-z])")


def normalize(text: str) -> str:
    """NFKC, strip, unwrap one quote pair, drop at most one trailing mark."""
    s = unicodedata.normalize("NFKC", text or "").strip()
    mark_removed = False
    for _ in range(3):  # a quoted value may sit inside or outside the trailing mark
        unwrapped = False
        for left, right in QUOTE_PAIRS:
            if len(s) >= 2 and s.startswith(left) and s.endswith(right):
                s = s[1:-1].strip()
                unwrapped = True
                break
        if unwrapped:
            continue
        if not mark_removed and s and s[-1] in TRAILING_MARKS:
            s = s[:-1].strip()
            mark_removed = True
            continue
        break
    return s


def build_repeat_prompt(prompt: str) -> str:
    """Condition B: the whole user prompt twice, separated by one blank line."""
    p = prompt.rstrip()
    return p + "\n\n" + p


@dataclass(frozen=True)
class ScoreResult:
    parsed_answer: str | None
    correct: bool
    parse_error: bool


def _fail(parsed: str | None = None) -> ScoreResult:
    return ScoreResult(parsed_answer=parsed, correct=False, parse_error=True)


def score(response_text: str | None, expected: str, answer_type: str) -> ScoreResult:
    """Grade one response. Ambiguous responses are parse errors, never guesses."""
    if response_text is None:
        return _fail()

    raw = unicodedata.normalize("NFKC", response_text).strip()
    if not raw:
        return _fail()

    if answer_type in ("text", "id"):
        # A bare value is required; an explanation makes the answer ambiguous.
        lines = [ln for ln in raw.splitlines() if ln.strip()]
        if len(lines) != 1:
            return _fail(raw)
        value = normalize(lines[0])
        if not value:
            return _fail(raw)
        return ScoreResult(value, value.casefold() == normalize(expected).casefold(), False)

    if answer_type == "integer":
        found = INT_RE.findall(raw)
        if len(found) != 1:
            return _fail(raw)
        return ScoreResult(found[0], int(found[0]) == int(expected), False)

    if answer_type == "decimal":
        found = DEC_RE.findall(raw)
        if len(found) != 1:
            return _fail(raw)
        try:
            got = Decimal(found[0].replace(",", ".")).quantize(Decimal("0.01"))
            want = Decimal(str(expected).replace(",", ".")).quantize(Decimal("0.01"))
        except InvalidOperation:
            return _fail(found[0])
        return ScoreResult(found[0], got == want, False)

    if answer_type == "choice":
        found = {m.group(1).upper() for m in CHOICE_RE.finditer(raw)}
        if len(found) != 1:
            return _fail(raw)
        letter = found.pop()
        return ScoreResult(letter, letter == str(expected).strip().upper(), False)

    raise ValueError(f"unknown answer_type: {answer_type}")


def exact_mcnemar_p(fixed: int, broken: int) -> float:
    """Two-sided exact binomial test on discordant pairs with p = 0.5."""
    n = fixed + broken
    if n == 0:
        return 1.0
    k = min(fixed, broken)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def paired_bootstrap_ci(
    pairs: list[tuple[bool, bool]],
    resamples: int = 10000,
    seed: int = 20260731,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Percentile CI for delta_pp, resampling whole (baseline, repeat) pairs."""
    n = len(pairs)
    if n == 0:
        return (float("nan"), float("nan"))
    base = np.array([1 if b else 0 for b, _ in pairs], dtype=np.int8)
    rep = np.array([1 if r else 0 for _, r in pairs], dtype=np.int8)
    diff = rep.astype(np.float64) - base.astype(np.float64)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(resamples, n))
    deltas = 100.0 * diff[idx].mean(axis=1)
    lo, hi = np.percentile(deltas, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return (float(lo), float(hi))


def interpretation_label(delta_pp: float, p_value: float, ci: tuple[float, float]) -> str:
    """Section 13: improvement / regression / unclear."""
    lo, hi = ci
    if math.isnan(lo) or math.isnan(hi):
        return "unclear"
    clear = p_value < 0.05 and (lo > 0) == (hi > 0)
    if clear and delta_pp > 0:
        return "improvement"
    if clear and delta_pp < 0:
        return "regression"
    return "unclear"
