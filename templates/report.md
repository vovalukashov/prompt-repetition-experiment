# Prompt Repetition Benchmark Report

## Executive summary

- Run date (UTC): {{run_date_utc}}
- Provider/model: {{provider}} / {{model_id}}
- Reasoning mode: {{reasoning_mode}}
- Dataset SHA-256: {{dataset_sha256}}
- Preset: {{preset}}
- Total successful requests: {{successful_requests}}
- Total failed requests: {{failed_requests}}

## Headline results

### Stress suite

- n: {{stress_n}}
- baseline: {{stress_baseline_correct}} / {{stress_n}} = {{stress_baseline_accuracy}}
- repeat_2: {{stress_repeat_correct}} / {{stress_n}} = {{stress_repeat_accuracy}}
- delta: {{stress_delta_pp}} percentage points
- fixed / broken: {{stress_fixed}} / {{stress_broken}}
- exact McNemar p: {{stress_mcnemar_p}}
- paired-bootstrap 95% CI: {{stress_ci_low}} to {{stress_ci_high}} pp

### Practical suite

- n: {{practical_n}}
- baseline: {{practical_baseline_correct}} / {{practical_n}} = {{practical_baseline_accuracy}}
- repeat_2: {{practical_repeat_correct}} / {{practical_n}} = {{practical_repeat_accuracy}}
- delta: {{practical_delta_pp}} percentage points
- fixed / broken: {{practical_fixed}} / {{practical_broken}}
- exact McNemar p: {{practical_mcnemar_p}}
- paired-bootstrap 95% CI: {{practical_ci_low}} to {{practical_ci_high}} pp

## Results by category

{{category_results}}

## Token, cost and latency measurements

{{efficiency_results}}

## Corrections and regressions

### Representative corrections

{{correction_examples}}

### Representative regressions

{{regression_examples}}

## Stability pilot

{{stability_results}}

## Failures and parser errors

{{failure_summary}}

## Interpretation

{{interpretation}}

## Limitations

- Results apply only to the exact provider, model ID, reasoning mode, request payload, date and dataset above.
- The practical suite is deliberately heterogeneous and should be interpreted descriptively.
- Provider-side hidden prompts, routing, quantization, caching and silent model updates may affect reproducibility.
- A non-significant result is not evidence that the true effect is exactly zero.
