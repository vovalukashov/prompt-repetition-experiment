# Output-cap sensitivity (ablation, not part of the headline number)

Run after the primary A/B was complete and frozen. Practical suite only,
60 tasks x 2 conditions, `max_output_tokens = 512` instead of 64. Everything
else identical: same model, same dataset, `temperature = 0`, thinking off.

## Why it was run

In the primary run 4 responses hit `finishReason = MAX_TOKENS`, and all 4 sat
on one side of the comparison: `repeat_2`, practical suite, 0 on baseline.
If the 64-token cap were truncating otherwise-correct answers, the practical
delta would be an artefact of the cap rather than a property of the technique.

## Result

| grading | baseline | repeat_2 | delta pp | fixed | broken | McNemar p | 95% CI pp | verdict |
|---|---|---|---|---|---|---|---|---|
| primary run, 64-token cap, strict | 31/60 | 34/60 | +5.0 | 8 | 5 | 0.5811 | -6.7 … +16.7 | unclear |
| this run, 512-token cap, strict | 31/60 | 34/60 | +5.0 | 8 | 5 | 0.5811 | -6.7 … +16.7 | unclear |
| this run, 512-token cap, lenient | 31/60 | 38/60 | +11.7 | 12 | 5 | 0.1435 | -1.7 … +25.0 | unclear |

"Strict" is the protocol grading of EXPERIMENT_SPEC.md §11: the prompts say
"ответь только числом", so a response that shows its working has more than one
candidate value, is marked `parse_error` and scored wrong. "Lenient" is a
secondary view that accepts the final value of a shown solution; it is reported
for transparency only and is applied symmetrically to both conditions.

## What it shows

1. **The cap was not the cause.** With 512 output tokens no response is
   truncated (`STOP` for all 120), and the strict result is byte-identical to
   the primary run: 31 → 34, +5.0 pp. The 4 truncated responses were already
   going to be scored wrong as format violations.

2. **Repetition made the model chattier, and that is a real cost.** Format
   violations in the primary run split 0 (baseline) vs 4 (`repeat_2`), all in
   the practical suite. On the same tasks the single-copy prompt returned a bare
   number and the doubled prompt started explaining, despite both copies
   carrying the same "answer with only a number" instruction. In the 512-token
   run those explanations do reach the right value — for example
   `receipt_total_ru_002` ends with `80.91`, which is correct — but they still
   break the requested output format.

3. **The practical conclusion is robust.** Under all three gradings the effect
   on ordinary tasks stays statistically unclear: the most favourable variant
   still gives p = 0.14 with a CI crossing zero.

The headline numbers in `report.md` remain those of the primary run under strict
grading. Nothing in this ablation is mixed into them.
