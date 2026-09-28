# P1 capability baseline

P1 expands the public reusable capability library while preserving the public/private firewall and the smallest-sufficient-agent principle.

## Capability sequence

| Order | Capability | Target | State | Purpose |
| --- | --- | --- | --- | --- |
| 1 | `verified-completion` | skill | IMPLEMENTED | Prove that a completion claim matches authoritative final state rather than command success, green CI, or intermediate evidence. |
| 2 | `state-mutation-idempotency` | skill | IMPLEMENTED | Review retries, partial writes, duplicates, overwrite/delete hazards, and recovery semantics. |
| 3 | `provenance-freshness` | skill | IMPLEMENTED | Verify evidence provenance, source hierarchy, timestamps, and stale-state risk. |
| 4 | `research-data-integrity` | skill | PLANNED | Detect leakage, invalid joins, survivorship/look-ahead errors, duplicate observations, and unsupported inference. |
| 5 | `authority-boundary-review` | skill | PLANNED | Ensure capability availability is not mistaken for permission or execution authority. |
| 6 | `semantic-pr-review` | skill | PLANNED | Review pull requests for semantic correctness and system effects beyond lint/tests/CI. |

## Build contract

Every new public capability must:

1. have a stable capability ID and narrow reusable purpose;
2. state activation conditions, required inputs, output contract, stop conditions, and authority boundary;
3. remain generic and independent of private repositories or private state;
4. include public-safe synthetic evaluation cases covering easy, normal, deceptive, control, and adversarial conditions;
5. pass deterministic repository validation;
6. receive semantic review before merge;
7. be merged through a pull request;
8. be verified on the exact resulting default-branch state before completion is claimed.

## Evaluation dimensions

When comparing a capability with a primary-agent-only baseline, measure where practical:

- material defects missed;
- false-positive findings;
- incremental coverage or decision value;
- tool/latency overhead;
- whether C2/C3 escalation is justified.

## Specialist reviewers planned after sufficient skill evidence

- `research-validity-reviewer`
- `evidence-provenance-reviewer`
- `runtime-postcondition-verifier`

Reviewer roles should be added only when independent context or evidence creates measurable value.
