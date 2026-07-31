"""Tests for answer parsing, scoring and paired statistics."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scoring import (  # noqa: E402
    build_condition_prompt,
    build_repeat_prompt,
    exact_mcnemar_p,
    normalize,
    paired_bootstrap_ci,
    score,
)


# --- normalization ---------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("  John Walker  ", "John Walker"),
    ('"John Walker"', "John Walker"),
    ("«Юлия Ильина»", "Юлия Ильина"),
    ("John Walker.", "John Walker"),
    ("John Walker;", "John Walker"),
    ("'F95',", "F95"),
])
def test_normalize_strips_wrappers_and_one_trailing_mark(raw, expected):
    assert normalize(raw) == expected


def test_normalize_applies_nfkc():
    # full-width digits collapse to ascii under NFKC
    assert normalize("４２") == "42"


def test_normalize_removes_only_one_trailing_mark():
    assert normalize("John Walker..") == "John Walker."


# --- text ------------------------------------------------------------------

def test_text_exact_match_is_case_insensitive():
    r = score("john walker", "John Walker", "text")
    assert r.correct and not r.parse_error


def test_text_rejects_answer_with_trailing_explanation():
    r = score("John Walker is the 25th name", "John Walker", "text")
    assert not r.correct


def test_text_multiline_answer_is_a_parse_error():
    r = score("John Walker\nJane Doe", "John Walker", "text")
    assert r.parse_error and not r.correct


def test_text_empty_answer_is_a_parse_error():
    r = score("   ", "John Walker", "text")
    assert r.parse_error and not r.correct


def test_text_cyrillic_yo_is_not_folded_to_ye():
    r = score("Михаил Киселев", "Михаил Киселёв", "text")
    assert not r.correct


# --- integer ---------------------------------------------------------------

def test_integer_plain():
    assert score("30", "30", "integer").correct


def test_integer_with_surrounding_punctuation():
    assert score("30.", "30", "integer").correct


def test_integer_two_numbers_is_a_parse_error():
    r = score("30 or 31", "30", "integer")
    assert r.parse_error and not r.correct


def test_integer_no_number_is_a_parse_error():
    r = score("тридцать", "30", "integer")
    assert r.parse_error and not r.correct


def test_integer_wrong_value_is_not_a_parse_error():
    r = score("31", "30", "integer")
    assert not r.correct and not r.parse_error


# --- decimal ---------------------------------------------------------------

def test_decimal_accepts_comma_separator():
    assert score("129,12", "129.12", "decimal").correct


def test_decimal_compares_at_two_places():
    assert score("129.1200", "129.12", "decimal").correct


def test_decimal_rejects_rounding_drift():
    assert not score("129.13", "129.12", "decimal").correct


def test_decimal_strips_currency_sign():
    assert score("129.12 €", "129.12", "decimal").correct


def test_decimal_two_numbers_is_a_parse_error():
    r = score("129.12 or 130.00", "129.12", "decimal")
    assert r.parse_error and not r.correct


# --- choice ----------------------------------------------------------------

def test_choice_single_letter():
    assert score("A", "A", "choice").correct


def test_choice_letter_with_dot_and_russian_gloss_still_parses():
    # the letter is the only latin A-D token; cyrillic text cannot collide
    assert score("A. У меня насморк или простуда", "A", "choice").correct


def test_choice_two_letters_is_a_parse_error():
    r = score("A or B", "A", "choice")
    assert r.parse_error and not r.correct


def test_choice_lowercase_is_accepted():
    assert score("b", "B", "choice").correct


# --- id --------------------------------------------------------------------

def test_id_exact_case_insensitive():
    assert score("f95", "F95", "id").correct


def test_id_with_prefix_text_is_not_a_match():
    assert not score("Ответ: F95", "F95", "id").correct


# --- prompt construction ---------------------------------------------------

def test_repeat_prompt_is_exactly_two_copies_joined_by_a_blank_line():
    p = "Question?\n"
    out = build_repeat_prompt(p)
    assert out == "Question?\n\nQuestion?"
    assert out.count("Question?") == 2


def test_baseline_condition_is_the_untouched_prompt():
    assert build_condition_prompt("Question?  \n", "baseline", "en") == "Question?"


def test_repeat_2_condition_matches_the_primary_builder():
    p = "Вопрос?"
    assert build_condition_prompt(p, "repeat_2", "ru") == build_repeat_prompt(p)


def test_repeat_3_is_three_exact_copies_and_adds_no_other_tokens():
    out = build_condition_prompt("Question?", "repeat_3", "en")
    assert out == "Question?\n\nQuestion?\n\nQuestion?"
    assert out.count("Question?") == 3


def test_repeat_verbose_inserts_a_russian_marker_for_russian_prompts():
    out = build_condition_prompt("Вопрос?", "repeat_verbose", "ru")
    assert out == "Вопрос?\n\nПовторяю:\nВопрос?"


def test_repeat_verbose_inserts_an_english_marker_for_english_prompts():
    # a Russian marker on an English prompt would confound language with verbosity
    out = build_condition_prompt("Question?", "repeat_verbose", "en")
    assert out == "Question?\n\nLet me repeat that:\nQuestion?"


def test_every_repeat_condition_preserves_the_prompt_verbatim():
    p = "Списки: A, B, C.\n\nЧто третье? Ответь одним словом."
    for cond in ("repeat_2", "repeat_3", "repeat_verbose"):
        out = build_condition_prompt(p, cond, "ru")
        assert out.startswith(p) and out.endswith(p)


def test_unknown_condition_is_rejected():
    with pytest.raises(ValueError):
        build_condition_prompt("Question?", "repeat_17", "en")


# --- exact McNemar ---------------------------------------------------------

def test_mcnemar_no_discordant_pairs_gives_p_one():
    assert exact_mcnemar_p(0, 0) == 1.0


def test_mcnemar_symmetric_split_gives_p_one():
    assert exact_mcnemar_p(5, 5) == 1.0


def test_mcnemar_known_value_10_vs_0():
    # two-sided exact binomial, n=10, all on one side: 2 * 0.5^10
    assert exact_mcnemar_p(10, 0) == pytest.approx(2 * 0.5 ** 10)


def test_mcnemar_known_value_8_vs_2():
    # 2 * P(X <= 2), X ~ Bin(10, 0.5) = 2 * (1+10+45)/1024
    assert exact_mcnemar_p(8, 2) == pytest.approx(2 * 56 / 1024)


def test_mcnemar_is_symmetric_in_its_arguments():
    assert exact_mcnemar_p(9, 3) == exact_mcnemar_p(3, 9)


def test_mcnemar_never_exceeds_one():
    assert exact_mcnemar_p(1, 1) == 1.0


# --- paired bootstrap ------------------------------------------------------

def test_bootstrap_ci_is_zero_width_when_every_pair_agrees():
    pairs = [(True, True)] * 50
    lo, hi = paired_bootstrap_ci(pairs, resamples=2000, seed=1)
    assert lo == 0.0 and hi == 0.0


def test_bootstrap_ci_excludes_zero_for_a_large_one_sided_effect():
    pairs = [(False, True)] * 40 + [(True, True)] * 60
    lo, hi = paired_bootstrap_ci(pairs, resamples=5000, seed=1)
    assert lo > 0 and hi > 0


def test_bootstrap_ci_brackets_the_point_estimate():
    pairs = [(False, True)] * 10 + [(True, False)] * 4 + [(True, True)] * 86
    delta = 100 * (sum(r for _, r in pairs) - sum(b for b, _ in pairs)) / len(pairs)
    lo, hi = paired_bootstrap_ci(pairs, resamples=5000, seed=7)
    assert lo <= delta <= hi


def test_bootstrap_is_deterministic_for_a_fixed_seed():
    pairs = [(False, True)] * 12 + [(True, False)] * 7 + [(True, True)] * 81
    a = paired_bootstrap_ci(pairs, resamples=3000, seed=42)
    b = paired_bootstrap_ci(pairs, resamples=3000, seed=42)
    assert a == b


def test_bootstrap_empty_input_returns_nan():
    lo, hi = paired_bootstrap_ci([], resamples=100, seed=1)
    assert math.isnan(lo) and math.isnan(hi)
