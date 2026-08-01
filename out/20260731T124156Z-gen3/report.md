# Prompt Repetition Benchmark Report

## Executive summary

- Run date (UTC): 2026-07-31T12:42:16.059Z
- Provider/model: google / gemini-3.5-flash-lite
- Reasoning mode: minimal_not_disableable (not available; thinkingLevel floor is "minimal")
- Dataset SHA-256: ffbe5c9aa5708b3abab695a3ac40d4829d7c83fce0541684264f9623e997384c
- Preset: standard
- Total successful requests: 1360
- Total failed requests: 0

## Headline results

### Stress suite

- n: 160
- baseline: 78 / 160 = 48.8%
- repeat_2: 136 / 160 = 85.0%
- delta: +36.3 percentage points
- fixed / broken: 61 / 3
- exact McNemar p: 4.74e-15
- paired-bootstrap 95% CI: +28.1 to +44.4 pp

### Practical suite

- n: 60
- baseline: 37 / 60 = 61.7%
- repeat_2: 40 / 60 = 66.7%
- delta: +5.0 percentage points
- fixed / broken: 5 / 2
- exact McNemar p: 0.4531
- paired-bootstrap 95% CI: -3.3 to +13.3 pp

## Results by category

| category | n | baseline | repeat_2 | delta pp | fixed | broken | McNemar p | 95% CI pp |
|---|---|---|---|---|---|---|---|---|
| date_interval_ru | 12 | 10 (83.3%) | 12 (100.0%) | +16.7 | 2 | 0 | 0.5000 | +0.0 … +41.7 |
| filter_record_ru | 12 | 10 (83.3%) | 12 (100.0%) | +16.7 | 2 | 0 | 0.5000 | +0.0 … +41.7 |
| letter_count_ru | 12 | 5 (41.7%) | 4 (33.3%) | -8.3 | 1 | 2 | 1.0000 | -33.3 … +16.7 |
| middle_match_en | 40 | 19 (47.5%) | 28 (70.0%) | +22.5 | 11 | 2 | 0.0225 | +7.5 … +37.5 |
| middle_match_ru | 40 | 17 (42.5%) | 32 (80.0%) | +37.5 | 16 | 1 | 0.0003 | +20.0 … +55.0 |
| name_index_en | 40 | 16 (40.0%) | 37 (92.5%) | +52.5 | 21 | 0 | 9.54e-07 | +37.5 … +67.5 |
| name_index_ru | 40 | 26 (65.0%) | 39 (97.5%) | +32.5 | 13 | 0 | 0.0002 | +17.5 … +47.5 |
| receipt_total_ru | 12 | 0 (0.0%) | 0 (0.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |
| spanish_mcq_ru | 12 | 12 (100.0%) | 12 (100.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |

## Token, cost and latency measurements

| metric | baseline | repeat_2 |
|---|---|---|
| requests | 660 | 660 |
| median latency, ms | 438 | 438 |
| mean latency, ms | 454 | 454 |
| p95 latency, ms | 549 | 565 |
| input tokens, total | 141,702 | 283,404 |
| input tokens, mean | 214.7 | 429.4 |
| cached input tokens, total | 0 | 0 |
| output tokens, total | 2,268 | 2,236 |
| output tokens, mean | 3.44 | 3.39 |
| thinking tokens, total | 0 | 0 |
| cost, USD total | $0.04818 | $0.09061 |
| nominal input-token ratio | 1.00 | 2.000 |
| median paired latency delta, ms | — | +3 |

## Corrections and regressions

### Representative corrections

- `name_index_en_001` (name_index_en) — expected `John Walker`; baseline answered `Aaron Baker`, repeat_2 answered `John Walker`
- `middle_match_ru_001` (middle_match_ru) — expected `Юлия Ильина`; baseline answered `Виктор Степанов`, repeat_2 answered `Юлия Ильина`
- `name_index_ru_004` (name_index_ru) — expected `Наталья Морозова`; baseline answered `Евгения Зайцева`, repeat_2 answered `Наталья Морозова`
- `middle_match_en_007` (middle_match_en) — expected `Andrew Campbell`; baseline answered `Cameron Cook`, repeat_2 answered `Andrew Campbell`
- `date_interval_ru_001` (date_interval_ru) — expected `30`; baseline answered `29`, repeat_2 answered `30`

### Representative regressions

- `letter_count_ru_001` (letter_count_ru) — expected `1`; baseline answered `2`, repeat_2 answered `2`
- `middle_match_en_016` (middle_match_en) — expected `Mateo Bailey`; baseline answered `Mateo Bailey`, repeat_2 answered `Robert Hall`
- `middle_match_ru_009` (middle_match_ru) — expected `Любовь Попова`; baseline answered `Любовь Попова`, repeat_2 answered `Дмитрий Тарасов`
- `letter_count_ru_012` (letter_count_ru) — expected `1`; baseline answered `1`, repeat_2 answered `0`
- `middle_match_en_024` (middle_match_en) — expected `Isaiah Cox`; baseline answered `Isaiah Cox`, repeat_2 answered `Kai Young`

## Stability pilot

20 tasks, baseline sent twice: 8 disagreement(s) = 40.0% (threshold 5%) -> repeats_per_condition = 3

With 3 responses per condition, the headline numbers above use the per-task majority vote. All-response accuracy and repeat variability:

- `baseline`: 348/660 responses correct (52.7%); 162/220 tasks (73.6%) returned the identical answer every time; 21 tasks (9.5%) flipped between correct and wrong across repeats
- `repeat_2`: 525/660 responses correct (79.5%); 200/220 tasks (90.9%) returned the identical answer every time; 7 tasks (3.2%) flipped between correct and wrong across repeats

## Failures and parser errors

- technical failures (final, after retries): 0
- retried requests: 0
- parse errors, baseline: 0
- parse errors, repeat_2: 0
- finish reasons: {'STOP': 1320}
- thinking tokens emitted: baseline 0, repeat_2 0

## Interpretation

- stress: delta +36.3 pp, McNemar p = 4.74e-15, CI +28.1 … +44.4 -> repeat_2 is better; McNemar p < 0.05 and the bootstrap CI excludes 0
- practical: delta +5.0 pp, McNemar p = 0.4531, CI -3.3 … +13.3 -> no statistically clear effect on this model and dataset (this is not evidence that the true effect is exactly zero)


## Limitations

- Results apply only to the exact provider, model ID, reasoning mode, request payload, date and dataset above.
- The practical suite is deliberately heterogeneous and should be interpreted descriptively.
- Provider-side hidden prompts, routing, quantization, caching and silent model updates may affect reproducibility.
- A non-significant result is not evidence that the true effect is exactly zero.

## Run-specific limitations

- `max_output_tokens = 64` truncated no responses.
- `gemini-2.0-flash-lite`, the model behind the widely quoted +76 pp NameIndex result, was shut down by Google on 2026-06-01, so an exact replication of that number is no longer possible on the Gemini API.
- The Gemini `generateContent` API exposes no sampling seed, so bit-exact reproducibility is not guaranteed even at `temperature = 0`. The stability pilot measured 40.0% answer disagreement when baseline was sent twice.
- Prompt caching did not engage: 0 and 0 cached input tokens were reported, so the input-token ratio is also the billed ratio.
