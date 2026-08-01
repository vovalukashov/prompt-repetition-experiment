# Prompt Repetition Benchmark Report

## Executive summary

- Run date (UTC): 2026-08-01T11:33:34.095Z
- Provider/model: google / gemini-3.5-flash-lite
- Reasoning mode: high (not applicable; thinking deliberately enabled)
- Dataset SHA-256: ffbe5c9aa5708b3abab695a3ac40d4829d7c83fce0541684264f9623e997384c
- Preset: standard
- Total successful requests: 160
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
- baseline: 60 / 60 = 100.0%
- repeat_2: 59 / 60 = 98.3%
- delta: -1.7 percentage points
- fixed / broken: 0 / 1
- exact McNemar p: 1.0000
- paired-bootstrap 95% CI: -5.0 to +0.0 pp

## Results by category

| category | n | baseline | repeat_2 | delta pp | fixed | broken | McNemar p | 95% CI pp |
|---|---|---|---|---|---|---|---|---|
| date_interval_ru | 12 | 12 (100.0%) | 12 (100.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |
| filter_record_ru | 12 | 12 (100.0%) | 12 (100.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |
| letter_count_ru | 12 | 12 (100.0%) | 11 (91.7%) | -8.3 | 0 | 1 | 1.0000 | -25.0 … +0.0 |
| receipt_total_ru | 12 | 12 (100.0%) | 12 (100.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |
| spanish_mcq_ru | 12 | 12 (100.0%) | 12 (100.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |

## Token, cost and latency measurements

| metric | baseline | repeat_2 |
|---|---|---|
| requests | 60 | 60 |
| median latency, ms | 2068 | 2053 |
| mean latency, ms | 2385 | 2581 |
| p95 latency, ms | 4292 | 5811 |
| input tokens, total | 7,299 | 14,598 |
| input tokens, mean | 121.7 | 243.3 |
| cached input tokens, total | 0 | 0 |
| output tokens, total | 150 | 150 |
| output tokens, mean | 2.54 | 2.50 |
| thinking tokens, total | 48,162 | 49,302 |
| cost, USD total | $0.12297 | $0.12801 |
| nominal input-token ratio | 1.00 | 2.000 |
| median paired latency delta, ms | — | -51 |

## Corrections and regressions

### Representative corrections

_none_

### Representative regressions

- `letter_count_ru_008` (letter_count_ru) — expected `1`; baseline answered `1`, repeat_2 answered `2`

## Stability pilot

20 tasks, baseline sent twice: 0 disagreement(s) = 0.0% (threshold 5%) -> repeats_per_condition = 1

## Failures and parser errors

- technical failures (final, after retries): 0
- retried requests: 0
- parse errors, baseline: 0
- parse errors, repeat_2: 0
- finish reasons: {'STOP': 120}
- thinking tokens emitted: baseline 48162, repeat_2 49302

## Interpretation

- stress: delta +nan pp, McNemar p = 1.0000, CI +nan … +nan -> no statistically clear effect on this model and dataset (this is not evidence that the true effect is exactly zero)
- practical: delta -1.7 pp, McNemar p = 1.0000, CI -5.0 … +0.0 -> no statistically clear effect on this model and dataset (this is not evidence that the true effect is exactly zero)
- practical baseline accuracy is >= 95%: the suite is near ceiling and headroom is limited


## Limitations

- Results apply only to the exact provider, model ID, reasoning mode, request payload, date and dataset above.
- The practical suite is deliberately heterogeneous and should be interpreted descriptively.
- Provider-side hidden prompts, routing, quantization, caching and silent model updates may affect reproducibility.
- A non-significant result is not evidence that the true effect is exactly zero.

## Run-specific limitations

- `max_output_tokens = 64` truncated no responses.
- `gemini-2.0-flash-lite`, the model behind the widely quoted +76 pp NameIndex result, was shut down by Google on 2026-06-01, so an exact replication of that number is no longer possible on the Gemini API.
- The Gemini `generateContent` API exposes no sampling seed, so bit-exact reproducibility is not guaranteed even at `temperature = 0`. The stability pilot measured 0.0% answer disagreement when baseline was sent twice.
- Prompt caching did not engage: 0 and 0 cached input tokens were reported, so the input-token ratio is also the billed ratio.
