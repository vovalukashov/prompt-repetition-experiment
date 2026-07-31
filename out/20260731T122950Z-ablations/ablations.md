# Repetition variants — gemini-2.5-flash-lite

- Run (UTC): 2026-07-31T12:29:53.036Z
- Reasoning mode: disabled (generationConfig.thinkingConfig.thinkingBudget=0)
- Conditions: baseline, repeat_2, repeat_3, repeat_verbose
- Dataset SHA-256: ffbe5c9aa5708b3abab695a3ac40d4829d7c83fce0541684264f9623e997384c
- Tasks: 220, spend: $0.0393

Every variant is paired against `baseline` on the same tasks inside this run, so the comparisons do not depend on the earlier primary run.

## stress suite

| variant | n | baseline | variant | delta pp | fixed | broken | McNemar p | 95% CI pp |
|---|---|---|---|---|---|---|---|---|
| repeat_2 | 160 | 58 (36.2%) | 120 (75.0%) | +38.8 | 73 | 11 | 2.25e-12 | +28.7 … +48.1 |
| repeat_3 | 160 | 58 (36.2%) | 128 (80.0%) | +43.8 | 78 | 8 | 1.52e-15 | +34.4 … +52.5 |
| repeat_verbose | 160 | 58 (36.2%) | 121 (75.6%) | +39.4 | 73 | 10 | 5.80e-13 | +29.4 … +48.8 |

## practical suite

| variant | n | baseline | variant | delta pp | fixed | broken | McNemar p | 95% CI pp |
|---|---|---|---|---|---|---|---|---|
| repeat_2 | 60 | 31 (51.7%) | 34 (56.7%) | +5.0 | 8 | 5 | 0.5811 | -6.7 … +16.7 |
| repeat_3 | 60 | 31 (51.7%) | 33 (55.0%) | +3.3 | 6 | 4 | 0.7539 | -6.7 … +13.3 |
| repeat_verbose | 60 | 31 (51.7%) | 32 (53.3%) | +1.7 | 6 | 5 | 1.0000 | -8.3 … +11.7 |

## All tasks

| variant | n | baseline | variant | delta pp | fixed | broken | McNemar p | 95% CI pp |
|---|---|---|---|---|---|---|---|---|
| repeat_2 | 220 | 89 (40.5%) | 154 (70.0%) | +29.5 | 81 | 16 | 1.24e-11 | +21.8 … +37.3 |
| repeat_3 | 220 | 89 (40.5%) | 161 (73.2%) | +32.7 | 84 | 12 | 1.83e-14 | +25.0 … +40.5 |
| repeat_verbose | 220 | 89 (40.5%) | 153 (69.5%) | +29.1 | 79 | 15 | 1.15e-11 | +21.4 … +36.8 |

## By category

### date_interval_ru

| variant | n | baseline | variant | delta pp | fixed | broken | McNemar p | 95% CI pp |
|---|---|---|---|---|---|---|---|---|
| repeat_2 | 12 | 5 (41.7%) | 6 (50.0%) | +8.3 | 2 | 1 | 1.0000 | -16.7 … +33.3 |
| repeat_3 | 12 | 5 (41.7%) | 6 (50.0%) | +8.3 | 1 | 0 | 1.0000 | +0.0 … +25.0 |
| repeat_verbose | 12 | 5 (41.7%) | 5 (41.7%) | +0.0 | 1 | 1 | 1.0000 | -25.0 … +25.0 |

### filter_record_ru

| variant | n | baseline | variant | delta pp | fixed | broken | McNemar p | 95% CI pp |
|---|---|---|---|---|---|---|---|---|
| repeat_2 | 12 | 8 (66.7%) | 12 (100.0%) | +33.3 | 4 | 0 | 0.1250 | +8.3 … +58.3 |
| repeat_3 | 12 | 8 (66.7%) | 12 (100.0%) | +33.3 | 4 | 0 | 0.1250 | +8.3 … +58.3 |
| repeat_verbose | 12 | 8 (66.7%) | 12 (100.0%) | +33.3 | 4 | 0 | 0.1250 | +8.3 … +58.3 |

### letter_count_ru

| variant | n | baseline | variant | delta pp | fixed | broken | McNemar p | 95% CI pp |
|---|---|---|---|---|---|---|---|---|
| repeat_2 | 12 | 6 (50.0%) | 4 (33.3%) | -16.7 | 2 | 4 | 0.6875 | -58.3 … +25.0 |
| repeat_3 | 12 | 6 (50.0%) | 3 (25.0%) | -25.0 | 1 | 4 | 0.3750 | -58.3 … +8.3 |
| repeat_verbose | 12 | 6 (50.0%) | 3 (25.0%) | -25.0 | 1 | 4 | 0.3750 | -58.3 … +8.3 |

### middle_match_en

| variant | n | baseline | variant | delta pp | fixed | broken | McNemar p | 95% CI pp |
|---|---|---|---|---|---|---|---|---|
| repeat_2 | 40 | 16 (40.0%) | 19 (47.5%) | +7.5 | 8 | 5 | 0.5811 | -10.0 … +25.0 |
| repeat_3 | 40 | 16 (40.0%) | 23 (57.5%) | +17.5 | 11 | 4 | 0.1185 | +0.0 … +35.0 |
| repeat_verbose | 40 | 16 (40.0%) | 19 (47.5%) | +7.5 | 9 | 6 | 0.6072 | -12.5 … +25.0 |

### middle_match_ru

| variant | n | baseline | variant | delta pp | fixed | broken | McNemar p | 95% CI pp |
|---|---|---|---|---|---|---|---|---|
| repeat_2 | 40 | 13 (32.5%) | 21 (52.5%) | +20.0 | 14 | 6 | 0.1153 | +0.0 … +40.0 |
| repeat_3 | 40 | 13 (32.5%) | 25 (62.5%) | +30.0 | 16 | 4 | 0.0118 | +10.0 … +50.0 |
| repeat_verbose | 40 | 13 (32.5%) | 22 (55.0%) | +22.5 | 13 | 4 | 0.0490 | +2.5 … +40.0 |

### name_index_en

| variant | n | baseline | variant | delta pp | fixed | broken | McNemar p | 95% CI pp |
|---|---|---|---|---|---|---|---|---|
| repeat_2 | 40 | 11 (27.5%) | 40 (100.0%) | +72.5 | 29 | 0 | 3.73e-09 | +57.5 … +85.0 |
| repeat_3 | 40 | 11 (27.5%) | 40 (100.0%) | +72.5 | 29 | 0 | 3.73e-09 | +57.5 … +85.0 |
| repeat_verbose | 40 | 11 (27.5%) | 40 (100.0%) | +72.5 | 29 | 0 | 3.73e-09 | +57.5 … +85.0 |

### name_index_ru

| variant | n | baseline | variant | delta pp | fixed | broken | McNemar p | 95% CI pp |
|---|---|---|---|---|---|---|---|---|
| repeat_2 | 40 | 18 (45.0%) | 40 (100.0%) | +55.0 | 22 | 0 | 4.77e-07 | +40.0 … +70.0 |
| repeat_3 | 40 | 18 (45.0%) | 40 (100.0%) | +55.0 | 22 | 0 | 4.77e-07 | +40.0 … +70.0 |
| repeat_verbose | 40 | 18 (45.0%) | 40 (100.0%) | +55.0 | 22 | 0 | 4.77e-07 | +40.0 … +70.0 |

### receipt_total_ru

| variant | n | baseline | variant | delta pp | fixed | broken | McNemar p | 95% CI pp |
|---|---|---|---|---|---|---|---|---|
| repeat_2 | 12 | 0 (0.0%) | 0 (0.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |
| repeat_3 | 12 | 0 (0.0%) | 0 (0.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |
| repeat_verbose | 12 | 0 (0.0%) | 0 (0.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |

### spanish_mcq_ru

| variant | n | baseline | variant | delta pp | fixed | broken | McNemar p | 95% CI pp |
|---|---|---|---|---|---|---|---|---|
| repeat_2 | 12 | 12 (100.0%) | 12 (100.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |
| repeat_3 | 12 | 12 (100.0%) | 12 (100.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |
| repeat_verbose | 12 | 12 (100.0%) | 12 (100.0%) | +0.0 | 0 | 0 | 1.0000 | +0.0 … +0.0 |

## Cost of each variant

| condition | requests | mean input tokens | input ratio | output tokens | thinking tokens | median latency ms | parse errors | truncated | cost USD |
|---|---|---|---|---|---|---|---|---|---|
| baseline | 220 | 214.7 | 1.000 | 774 | 0 | 470 | 0 | 0 | $0.00503 |
| repeat_2 | 220 | 429.4 | 2.000 | 993 | 0 | 469 | 4 | 4 | $0.00984 |
| repeat_3 | 220 | 644.1 | 3.000 | 1,023 | 0 | 469 | 5 | 3 | $0.01458 |
| repeat_verbose | 220 | 435.4 | 2.028 | 752 | 0 | 466 | 0 | 0 | $0.00988 |
