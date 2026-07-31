# Prompt Repetition Benchmark Report

## Executive summary

- Run date (UTC): 2026-07-31T12:56:43.106Z
- Provider/model: google / gemini-3.5-flash-lite
- Reasoning mode: high (not applicable; thinking deliberately enabled)
- Dataset SHA-256: ffbe5c9aa5708b3abab695a3ac40d4829d7c83fce0541684264f9623e997384c
- Preset: standard
- Total successful requests: 360
- Total failed requests: 0

## Headline results

### Stress suite

- n: 160
- baseline: 160 / 160 = 100.0%
- repeat_2: 160 / 160 = 100.0%
- delta: +0.0 percentage points
- fixed / broken: 0 / 0
- exact McNemar p: 1.0000
- paired-bootstrap 95% CI: +0.0 to +0.0 pp

### Practical suite

- n: 0
- baseline: 0 / 0 = nan%
- repeat_2: 0 / 0 = nan%
- delta: +nan percentage points
- fixed / broken: 0 / 0
- exact McNemar p: 1.0000
- paired-bootstrap 95% CI: +nan to +nan pp

## Results by category

| category | n | baseline | repeat_2 | delta pp | fixed | broken | McNemar p | 95% CI pp |
|---|---|---|---|---|---|---|---|---|
| middle_match_en | 40 | 40 (100.0%) | 40 (100.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |
| middle_match_ru | 40 | 40 (100.0%) | 40 (100.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |
| name_index_en | 40 | 40 (100.0%) | 40 (100.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |
| name_index_ru | 40 | 40 (100.0%) | 40 (100.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |

## Token, cost and latency measurements

| metric | baseline | repeat_2 |
|---|---|---|
| requests | 160 | 160 |
| median latency, ms | 2423 | 2272 |
| mean latency, ms | 2717 | 2580 |
| p95 latency, ms | 4952 | 4456 |
| input tokens, total | 39,935 | 79,870 |
| input tokens, mean | 249.6 | 499.2 |
| cached input tokens, total | 0 | 0 |
| output tokens, total | 594 | 593 |
| output tokens, mean | 3.71 | 3.71 |
| thinking tokens, total | 168,046 | 155,061 |
| cost, USD total | $0.43358 | $0.41310 |
| nominal input-token ratio | 1.00 | 2.000 |
| median paired latency delta, ms | — | -106 |

## Corrections and regressions

### Representative corrections

_none_

### Representative regressions

_none_

## Stability pilot

20 tasks, baseline sent twice: 0 disagreement(s) = 0.0% (threshold 5%) -> repeats_per_condition = 1

## Failures and parser errors

- technical failures (final, after retries): 0
- retried requests: 0
- parse errors, baseline: 0
- parse errors, repeat_2: 0
- finish reasons: {'STOP': 320}
- thinking tokens emitted: baseline 168046, repeat_2 155061

## Interpretation

- stress: delta +0.0 pp, McNemar p = 1.0000, CI +0.0 … +0.0 -> no statistically clear effect on this model and dataset (this is not evidence that the true effect is exactly zero)
- practical: delta +nan pp, McNemar p = 1.0000, CI +nan … +nan -> no statistically clear effect on this model and dataset (this is not evidence that the true effect is exactly zero)
- stress baseline accuracy is >= 95%: the suite is near ceiling and headroom is limited


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
