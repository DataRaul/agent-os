# P2 specialist reviewer evaluation

## Goal

Determine whether any planned specialist reviewer earns its coordination cost beyond the established P1 baseline:

```text
one capable primary agent
+ relevant public Agent OS skills
+ deterministic validation
```

The existence of a reviewer concept is not evidence that a separate agent is useful. P2 measures incremental value before any candidate reviewer is promoted into `agents/`.

## Candidates

| Candidate | Baseline skills used in its benchmark |
| --- | --- |
| `research-validity-reviewer` | `research-data-integrity`, `provenance-freshness` |
| `evidence-provenance-reviewer` | `provenance-freshness`, `verified-completion` |
| `runtime-postcondition-verifier` | `verified-completion`, `state-mutation-idempotency`, `authority-boundary-review` |

These are candidate role IDs only. They are not implemented reviewer agents.

## Benchmark structure

Public-safe synthetic cases live in:

- `benchmarks/specialist-reviewer-evaluation/cases.json`
- `benchmarks/specialist-reviewer-evaluation/oracle.json`

The case file contains only the material presented to the evaluated runs. The oracle contains expected finding codes and admission policy and must not be supplied to the evaluated model/agent.

The benchmark is public, so it is not a secret holdout. The separation is procedural: runner inputs must exclude the oracle.

## Fair comparison protocol

For one candidate reviewer:

1. Select that candidate's five cases.
2. Use the same declared model/configuration for baseline and reviewer runs.
3. Run exactly three independent replicates per case, as fixed by the oracle.
4. Baseline run receives the case plus the listed P1 skills. No separate reviewer is used.
5. Reviewer run receives the same case and relevant evidence independently.
6. Do not provide the reviewer the baseline answer, author confidence, hidden reasoning, or oracle.
7. Record only normalized finding codes plus optional tool-call/latency measurements.
8. Score with:

```bash
python scripts/score_specialist_reviewer_eval.py path/to/result.json
```

The scorer combines baseline and independent reviewer findings only for measurement. The reviewer itself must remain independent.

## Result shape

```json
{
  "schema_version": 1,
  "suite": "specialist-reviewer-evaluation",
  "candidate_reviewer": "research-validity-reviewer",
  "model_configuration_id": "same-config-for-baseline-and-reviewer",
  "reviewer_received_baseline_output": false,
  "runs": [
    {
      "case_id": "rvr-easy-01",
      "replicate": 1,
      "baseline_finding_codes": [],
      "reviewer_finding_codes": [],
      "baseline_tool_calls": 0,
      "reviewer_tool_calls": 0,
      "baseline_latency_ms": 0,
      "reviewer_latency_ms": 0
    }
  ]
}
```

Tool-call and latency values are optional. When present they must be non-negative.

## Admission rule

The initial public admission rule is deliberately conservative and simple. A candidate becomes **eligible for role implementation review**, not automatically admitted, only if all of the following hold:

- every candidate case has exactly three valid replicates;
- the independent reviewer finds expected material issues missed by baseline in at least two distinct cases;
- there are at least three incremental expected-finding observations across case/replicate pairs;
- the combined baseline-plus-reviewer expected-finding recall is at least 80%;
- the reviewer adds at most one false-positive observation across the full run;
- reviewer control cases remain false-positive free.

The scorer reports `ELIGIBLE_FOR_ROLE_IMPLEMENTATION_REVIEW` or `NO_INCREMENTAL_VALUE_DEMONSTRATED`.

Eligibility still does not create execution authority or require that a reviewer be added. Semantic review should also consider tool/latency overhead and whether the observed gain is likely to generalize.

## Failure boundaries

Do not admit a reviewer because:

- it agrees with the baseline;
- it uses more words;
- it repeats findings already made by the baseline;
- it has access to the oracle;
- it sees the baseline output before independent review;
- it increases apparent recall by generating many unsupported findings;
- extra replicates are added until a favorable result appears;
- one unusually favorable case drives the result.

Do not copy private project incidents or fixtures into this benchmark.

## Terminal condition

P2 evaluation infrastructure is ready when:

- benchmark cases and oracle validate deterministically;
- the scorer validates and scores normalized run files;
- CI passes on the exact main candidate.

Reviewer roles remain evaluation-gated until actual comparative runs demonstrate incremental value.
