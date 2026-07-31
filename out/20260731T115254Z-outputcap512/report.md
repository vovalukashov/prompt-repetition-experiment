# Prompt Repetition Benchmark Report

## Executive summary

- Run date (UTC): 2026-07-31T11:52:57.637Z
- Provider/model: google / gemini-2.5-flash-lite
- Reasoning mode: disabled (generationConfig.thinkingConfig.thinkingBudget=0)
- Dataset SHA-256: ffbe5c9aa5708b3abab695a3ac40d4829d7c83fce0541684264f9623e997384c
- Preset: standard
- Total successful requests: 120
- Total failed requests: 0

## Headline results

### Stress suite

- n: 0
- baseline: 0 / 0 = nan%
- repeat_2: 0 / 0 = nan%
- delta: +nan percentage points
- fixed / broken: 0 / 0
- exact McNemar p: 1.0000
- paired-bootstrap 95% CI: +nan to +nan pp

### Practical suite

- n: 60
- baseline: 31 / 60 = 51.7%
- repeat_2: 34 / 60 = 56.7%
- delta: +5.0 percentage points
- fixed / broken: 8 / 5
- exact McNemar p: 0.5811
- paired-bootstrap 95% CI: -6.7 to +16.7 pp

## Results by category

| category | n | baseline | repeat_2 | delta pp | fixed | broken | McNemar p | 95% CI pp |
|---|---|---|---|---|---|---|---|---|
| date_interval_ru | 12 | 5 (41.7%) | 6 (50.0%) | +8.3 | 2 | 1 | 1.0000 | -16.7 … +33.3 |
| filter_record_ru | 12 | 8 (66.7%) | 12 (100.0%) | +33.3 | 4 | 0 | 0.1250 | +8.3 … +58.3 |
| letter_count_ru | 12 | 6 (50.0%) | 4 (33.3%) | -16.7 | 2 | 4 | 0.6875 | -58.3 … +25.0 |
| receipt_total_ru | 12 | 0 (0.0%) | 0 (0.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |
| spanish_mcq_ru | 12 | 12 (100.0%) | 12 (100.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |

## Token, cost and latency measurements

| metric | baseline | repeat_2 |
|---|---|---|
| requests | 60 | 60 |
| median latency, ms | 473 | 473 |
| mean latency, ms | 483 | 535 |
| p95 latency, ms | 607 | 940 |
| input tokens, total | 7,299 | 14,598 |
| input tokens, mean | 121.7 | 243.3 |
| cached input tokens, total | 0 | 0 |
| output tokens, total | 158 | 1,261 |
| output tokens, mean | 2.63 | 21.02 |
| thinking tokens, total | 0 | 0 |
| cost, USD total | $0.00079 | $0.00196 |
| nominal input-token ratio | 1.00 | 2.000 |
| median paired latency delta, ms | — | +2 |

## Corrections and regressions

### Representative corrections

- `filter_record_ru_001` (filter_record_ru) — expected `F95`; baseline answered `B65`, repeat_2 answered `F95`
- `date_interval_ru_005` (date_interval_ru) — expected `11`; baseline answered `9`, repeat_2 answered `11`
- `letter_count_ru_003` (letter_count_ru) — expected `2`; baseline answered `1`, repeat_2 answered `2`
- `filter_record_ru_004` (filter_record_ru) — expected `A25`; baseline answered `B37`, repeat_2 answered `A25`
- `date_interval_ru_012` (date_interval_ru) — expected `243`; baseline answered `242`, repeat_2 answered `243`

### Representative regressions

- `letter_count_ru_001` (letter_count_ru) — expected `1`; baseline answered `1`, repeat_2 answered `2`
- `date_interval_ru_009` (date_interval_ru) — expected `13`; baseline answered `13`, repeat_2 answered `92`
- `letter_count_ru_004` (letter_count_ru) — expected `1`; baseline answered `1`, repeat_2 answered `2`
- `letter_count_ru_005` (letter_count_ru) — expected `1`; baseline answered `1`, repeat_2 answered `2`
- `letter_count_ru_006` (letter_count_ru) — expected `1`; baseline answered `1`, repeat_2 answered `2`

## Stability pilot

not run

## Failures and parser errors

- technical failures (final, after retries): 0
- retried requests: 1
- parse errors, baseline: 0
- parse errors, repeat_2: 4
- finish reasons: {'STOP': 120}
- thinking tokens emitted: baseline 0, repeat_2 0

## Interpretation

- stress: delta +nan pp, McNemar p = 1.0000, CI +nan … +nan -> no statistically clear effect on this model and dataset (this is not evidence that the true effect is exactly zero)
- practical: delta +5.0 pp, McNemar p = 0.5811, CI -6.7 … +16.7 -> no statistically clear effect on this model and dataset (this is not evidence that the true effect is exactly zero)


## Limitations

- Results apply only to the exact provider, model ID, reasoning mode, request payload, date and dataset above.
- The practical suite is deliberately heterogeneous and should be interpreted descriptively.
- Provider-side hidden prompts, routing, quantization, caching and silent model updates may affect reproducibility.
- A non-significant result is not evidence that the true effect is exactly zero.

## Run-specific limitations

- `max_output_tokens = 512` truncated no responses.
- `gemini-2.0-flash-lite`, the model behind the widely quoted +76 pp NameIndex result, was shut down by Google on 2026-06-01, so an exact replication of that number is no longer possible on the Gemini API.
- The Gemini `generateContent` API exposes no sampling seed, so bit-exact reproducibility is not guaranteed even at `temperature = 0`. The stability pilot measured 0.0% answer disagreement when baseline was sent twice.
- Prompt caching did not engage: 0 and 0 cached input tokens were reported, so the input-token ratio is also the billed ratio.
