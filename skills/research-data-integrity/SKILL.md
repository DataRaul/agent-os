---
name: research-data-integrity
description: Review research and analytical data workflows for leakage, look-ahead bias, survivorship bias, invalid joins, duplicate observations, missing-data distortions, denominator changes, and unsupported inference. Use before relying on research results, backtests, experiments, metrics, or derived datasets for consequential conclusions.
---

# Research Data Integrity

## Purpose

Verify that an analytical result is supported by data whose construction, timing, joins, missingness, and inference boundaries preserve the meaning of the research question.

This skill reviews integrity of research evidence. It does not decide business, scientific, investment, medical, legal, or policy conclusions.

## Required inputs

Obtain the smallest sufficient set of:

- research question or hypothesis;
- target population/universe and time period;
- raw or authoritative source definitions;
- transformation and filtering steps;
- join keys and temporal alignment rules;
- missing-data and duplicate handling;
- train/test or estimation/evaluation boundaries when applicable;
- metric definitions and denominators;
- final analytical output and the claim derived from it.

If temporal provenance, universe construction, or material transformation logic is unavailable, return insufficient evidence rather than assuming the dataset is valid.

## Review procedure

### 1. Reconstruct the analysis contract

State explicitly:

- unit of observation;
- target population/universe;
- time interval;
- outcome/target variable;
- predictors/exposures;
- sampling or inclusion rules;
- metric and denominator;
- intended inference scope.

Do not review only the final number. Review the dataset construction that gives the number meaning.

### 2. Check temporal integrity

Look for:

- future information used in past decisions;
- revised data substituted for point-in-time values;
- labels or outcomes leaking into feature construction;
- publication or availability lags ignored;
- timestamps normalized in a way that changes ordering;
- train/test splits that allow future information to influence earlier observations.

For historical decision simulation, distinguish event time, publication time, availability time, and processing time when relevant.

### 3. Check universe and survivorship integrity

Verify that inclusion rules do not silently condition on future survival or success.

Look for:

- present-day constituents used for historical analysis;
- delisted/failed entities omitted;
- only completed cases retained;
- late-arriving members backfilled as if always eligible;
- filters defined using outcomes not known at selection time.

### 4. Check joins and entity identity

Review:

- join keys and cardinality;
- one-to-many/many-to-many expansion;
- stale identifiers;
- entity renames or identifier reuse;
- date alignment and timezone handling;
- nearest-date/as-of join direction;
- unmatched rows and fallback behavior.

Measure row counts before and after material joins. Unexpected expansion or contraction requires explanation.

### 5. Check duplicates and weighting

Look for:

- duplicate source observations;
- repeated events counted independently;
- duplicated rows created by joins;
- aggregation that double-counts entities;
- implicit reweighting after filters;
- weights that no longer sum or normalize as intended.

### 6. Check missing-data semantics

Determine whether missingness is:

- excluded;
- imputed;
- assigned a default value;
- forward/back-filled;
- treated as zero;
- converted into a favorable/unfavorable category.

Verify that the treatment is explicit and does not silently change the population or denominator.

### 7. Check denominator and metric integrity

For every reported rate, average, hit rate, accuracy, return, conversion, or success measure:

- identify numerator;
- identify denominator;
- compare pre/post-filter denominators;
- verify whether excluded observations remain represented appropriately;
- check whether aggregation weights match the intended question.

A plausible numerator with a silently reduced denominator is a material integrity failure.

### 8. Check evaluation leakage and overfitting surfaces

When models, rules, signals, or parameter choices are evaluated, check for:

- tuning on the final test set;
- repeated hypothesis selection using the same holdout;
- feature selection using future outcomes;
- threshold choice after observing evaluation results;
- contamination across grouped/related observations;
- benchmark construction using the evaluated result itself.

This skill flags leakage and selection risk. It does not prescribe one universal statistical method.

### 9. Bound the inference

Separate:

- descriptive result;
- association;
- predictive evidence;
- causal claim;
- generalization beyond the observed population/time period.

Do not allow a narrower analysis to silently support a broader claim.

## Dispositions

Use one of:

- `RESEARCH_DATA_INTEGRITY_PASS`
- `MATERIAL_DATA_INTEGRITY_FINDINGS`
- `INFERENCE_SCOPE_OVERSTATED`
- `INSUFFICIENT_EVIDENCE`

## Output contract

Return:

```text
research_question:
unit_population_period:
temporal_integrity:
universe_survivorship:
joins_identity:
duplicates_weighting:
missing_data:
metric_denominator:
evaluation_leakage:
inference_scope:
disposition:
findings:
smallest_fix_or_verification:
```

## Stop conditions

Do not certify integrity when:

- point-in-time requirements exist but source availability timing is unknown;
- material joins lack cardinality or unmatched-row evidence;
- denominator changes cannot be reconstructed;
- duplicate handling is unknown for a repeated-observation source;
- evaluation data influenced model/rule selection without a valid independent check;
- the stated inference exceeds what the design can support.

## Completion rule

A research-data review is complete only when the temporal, universe, join, duplication, missingness, denominator, evaluation, and inference-scope surfaces have explicit dispositions.

This skill validates research-data integrity. It does not grant authority to act on the research result.
