# Prompt Repetition Benchmark Report

## Executive summary

- Run date (UTC): 2026-07-31T11:46:09.051Z
- Provider/model: google / gemini-2.5-flash-lite
- Reasoning mode: disabled (generationConfig.thinkingConfig.thinkingBudget=0)
- Dataset SHA-256: ffbe5c9aa5708b3abab695a3ac40d4829d7c83fce0541684264f9623e997384c
- Preset: standard
- Total successful requests: 480
- Total failed requests: 0

## Headline results

### Stress suite

- n: 160
- baseline: 58 / 160 = 36.3%
- repeat_2: 120 / 160 = 75.0%
- delta: +38.8 percentage points
- fixed / broken: 73 / 11
- exact McNemar p: 2.25e-12
- paired-bootstrap 95% CI: +28.7 to +48.1 pp

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
| middle_match_en | 40 | 16 (40.0%) | 19 (47.5%) | +7.5 | 8 | 5 | 0.5811 | -10.0 … +25.0 |
| middle_match_ru | 40 | 13 (32.5%) | 21 (52.5%) | +20.0 | 14 | 6 | 0.1153 | +0.0 … +40.0 |
| name_index_en | 40 | 11 (27.5%) | 40 (100.0%) | +72.5 | 29 | 0 | 3.73e-09 | +57.5 … +85.0 |
| name_index_ru | 40 | 18 (45.0%) | 40 (100.0%) | +55.0 | 22 | 0 | 4.77e-07 | +40.0 … +70.0 |
| receipt_total_ru | 12 | 0 (0.0%) | 0 (0.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |
| spanish_mcq_ru | 12 | 12 (100.0%) | 12 (100.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |

## Token, cost and latency measurements

| metric | baseline | repeat_2 |
|---|---|---|
| requests | 220 | 220 |
| median latency, ms | 471 | 468 |
| mean latency, ms | 471 | 488 |
| p95 latency, ms | 585 | 609 |
| input tokens, total | 47,234 | 94,468 |
| input tokens, mean | 214.7 | 429.4 |
| cached input tokens, total | 0 | 0 |
| output tokens, total | 774 | 993 |
| output tokens, mean | 3.52 | 4.51 |
| thinking tokens, total | 0 | 0 |
| cost, USD total | $0.00503 | $0.00984 |
| nominal input-token ratio | 1.00 | 2.000 |
| median paired latency delta, ms | — | -2 |

## Corrections and regressions

### Representative corrections

- `name_index_en_001` (name_index_en) — expected `John Walker`; baseline answered `James Miller`, repeat_2 answered `John Walker`
- `name_index_ru_001` (name_index_ru) — expected `Михаил Киселёв`; baseline answered `Елена Сергеева`, repeat_2 answered `Михаил Киселёв`
- `middle_match_ru_002` (middle_match_ru) — expected `Диана Полякова`; baseline answered `Елена Волкова`, repeat_2 answered `Диана Полякова`
- `middle_match_en_007` (middle_match_en) — expected `Andrew Campbell`; baseline answered `Christian Taylor`, repeat_2 answered `Andrew Campbell`
- `filter_record_ru_001` (filter_record_ru) — expected `F95`; baseline answered `B65`, repeat_2 answered `F95`

### Representative regressions

- `middle_match_ru_016` (middle_match_ru) — expected `Татьяна Дмитриева`; baseline answered `Татьяна Дмитриева`, repeat_2 answered `Елена Павлова`
- `middle_match_en_019` (middle_match_en) — expected `Julian Young`; baseline answered `Julian Young`, repeat_2 answered `Nathan Ramos`
- `letter_count_ru_001` (letter_count_ru) — expected `1`; baseline answered `1`, repeat_2 answered `2`
- `date_interval_ru_009` (date_interval_ru) — expected `13`; baseline answered `13`, repeat_2 answered `92`
- `middle_match_ru_018` (middle_match_ru) — expected `Светлана Соколова`; baseline answered `Светлана Соколова`, repeat_2 answered `Полина Александрова`

## Stability pilot

20 tasks, baseline sent twice: 0 disagreement(s) = 0.0% (threshold 5%) -> repeats_per_condition = 1

## Failures and parser errors

- technical failures (final, after retries): 0
- retried requests: 1
- parse errors, baseline: 0
- parse errors, repeat_2: 4
- finish reasons: {'STOP': 436, 'MAX_TOKENS': 4}
- thinking tokens emitted: baseline 0, repeat_2 0

## Interpretation

- stress: delta +38.8 pp, McNemar p = 2.25e-12, CI +28.7 … +48.1 -> repeat_2 is better; McNemar p < 0.05 and the bootstrap CI excludes 0
- practical: delta +5.0 pp, McNemar p = 0.5811, CI -6.7 … +16.7 -> no statistically clear effect on this model and dataset (this is not evidence that the true effect is exactly zero)


## Limitations

- Results apply only to the exact provider, model ID, reasoning mode, request payload, date and dataset above.
- The practical suite is deliberately heterogeneous and should be interpreted descriptively.
- Provider-side hidden prompts, routing, quantization, caching and silent model updates may affect reproducibility.
- A non-significant result is not evidence that the true effect is exactly zero.

## Run-specific limitations

- `max_output_tokens = 64` truncated 4 response(s) (by condition: {'repeat_2': 4}; by suite: {'practical': 4}). Every truncated response began writing a step-by-step solution despite the prompt asking for a bare value, so it is scored as a format violation. Because the truncations are not evenly split across conditions, the affected suite's delta carries this artefact; see the separate output-cap sensitivity run if one was performed.
- `gemini-2.0-flash-lite`, the model behind the widely quoted +76 pp NameIndex result, was shut down by Google on 2026-06-01, so an exact replication of that number is no longer possible on the Gemini API.
- The Gemini `generateContent` API exposes no sampling seed, so bit-exact reproducibility is not guaranteed even at `temperature = 0`. The stability pilot measured 0.0% answer disagreement when baseline was sent twice.
- Prompt caching did not engage: 0 and 0 cached input tokens were reported, so the input-token ratio is also the billed ratio.
