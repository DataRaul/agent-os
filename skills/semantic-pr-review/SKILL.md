---
name: semantic-pr-review
description: Review a pull request or candidate change for semantic correctness, integration effects, compatibility, state behavior, and requirement coverage beyond lint, types, unit tests, or green CI. Use for material PRs before merge, especially when the diff changes behavior, schemas, configuration, data flows, authority boundaries, integrations, or completion claims.
---

# Semantic PR Review

## Purpose

Determine whether a pull request actually implements its intended contract without introducing material semantic regressions that mechanical checks may miss.

This skill reviews a candidate. It does not merge, deploy, approve authority, or substitute for specialist security/domain review.

## Required inputs

Obtain the smallest sufficient set of:

- requested outcome and acceptance criteria;
- exact final candidate identity;
- complete diff and changed-file list;
- relevant callers, consumers, configuration, schemas, migrations, or interfaces;
- tests and CI run on the exact candidate;
- required positive and negative postconditions;
- authority/human gates relevant to merge or later execution.

If the exact candidate or complete diff is unavailable, return insufficient evidence rather than reviewing a stale or partial candidate.

## Review procedure

### 1. Reconstruct the intended contract

State what the PR claims to change and what must remain unchanged.

Separate:

- intended behavior;
- compatibility promises;
- data/state effects;
- operational effects;
- documentation/configuration obligations;
- merge/deploy authority.

Do not treat the PR title or author summary as sufficient evidence.

### 2. Review the whole diff

Classify every changed file as one or more of:

- implementation;
- tests/evals;
- configuration;
- schema/migration;
- documentation;
- workflow/CI;
- generated artifact;
- dependency/vendor surface.

Look for unrelated changes, missing companion changes, and semantic changes hidden inside mechanical refactors.

### 3. Trace integration surfaces

Identify relevant:

- callers and consumers;
- exported interfaces;
- configuration readers/writers;
- schema versions;
- migration order;
- runtime dependencies;
- external integrations;
- documentation or contracts that control downstream behavior.

A locally correct implementation can still be semantically incomplete if a dependent surface remains stale.

### 4. Compare behavior with tests

Determine what the tests actually prove.

Check for:

- happy-path-only coverage;
- tests asserting implementation detail rather than requirement;
- mocks that bypass the changed integration surface;
- changed defaults without legacy cases;
- negative/error paths absent;
- focused tests promoted into a whole-PR claim;
- CI run against an older candidate.

Green CI is evidence only for its tested scope.

### 5. Review state and data effects

When applicable, apply the relevant checks from:

- `state-mutation-idempotency`;
- `research-data-integrity`;
- `provenance-freshness`;
- `verified-completion`.

Look for:

- partial writes;
- retry hazards;
- stale evidence;
- denominator or join changes;
- schema/version mismatch;
- old state made unreadable;
- runtime effect broader than documented.

### 6. Review authority effects

When the PR changes automation, permissions, tool use, deployment behavior, publishing, or other side effects, apply `authority-boundary-review`.

Check that the change does not silently:

- broaden execution authority;
- convert advisory behavior into automatic action;
- expand write/destructive scope;
- bypass a human gate;
- treat credential/tool availability as permission.

### 7. Check compatibility and failure semantics

Review:

- existing callers;
- stored data;
- config defaults;
- fallback behavior;
- error propagation;
- rollback/recovery expectations;
- feature-disabled state;
- version skew.

Prefer explicit incompatibility over silent semantic drift.

### 8. Check negative postconditions

Ask what must not change or occur.

Examples:

- no unrelated runtime behavior changes;
- no private material exposure;
- no destructive mutation;
- no duplicate side effect;
- no authority expansion;
- no stale config remaining active;
- no old candidate evidence reused.

Verify these where practical.

### 9. Bind validation to the final candidate

Confirm that:

- the reviewed diff is the merge candidate;
- validation ran on that candidate;
- no later material commit invalidated the review;
- merge conflicts or automatic transformations will not change semantics unnoticed.

## Dispositions

Use one of:

- `SEMANTIC_PR_REVIEW_PASS` — no material semantic finding and evidence is sufficient;
- `MATERIAL_SEMANTIC_FINDINGS` — one or more material issues must be fixed or explicitly accepted;
- `SPECIALIST_REVIEW_REQUIRED` — a security, domain-validity, or other specialist question controls the decision;
- `INSUFFICIENT_EVIDENCE` — exact candidate, diff, integration context, or validation evidence is unavailable.

## Output contract

Return:

```text
candidate:
intended_contract:
diff_scope:
integration_surfaces:
test_evidence:
state_data_effects:
authority_effects:
compatibility_failure_semantics:
negative_postconditions:
disposition:
findings:
specialist_gate:
smallest_next_action:
```

## Stop conditions

Do not pass the PR when:

- the exact candidate differs from the validated candidate;
- a material caller/consumer cannot be assessed;
- state migration/recovery semantics are unresolved;
- a required authority gate is missing;
- the change raises a specialist question that materially controls correctness;
- the diff contains unexplained unrelated changes.

## Completion rule

A semantic PR review is complete only when the intended contract, full diff, integration surfaces, test scope, state/data effects, authority effects, compatibility, negative postconditions, and final-candidate identity have explicit dispositions.

This skill reviews merge readiness. It does not itself merge or grant merge authority.
