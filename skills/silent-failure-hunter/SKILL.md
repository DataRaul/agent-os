---
name: silent-failure-hunter
description: Review a material implementation or pull request for semantic defects that can survive green CI. Use after implementation and before merge when tests may not cover the full requirement, especially for state changes, migrations, data pipelines, fallbacks, retries, integrations, or completion claims.
---

# Silent Failure Hunter

## Purpose

Find defects that can remain hidden even when configured tests and CI are green.

This skill is an independent semantic review. It does not replace repository tests, security review, or domain authority.

## Required inputs

Obtain the smallest sufficient set of:

- requested outcome / acceptance criteria;
- final candidate diff;
- tests and CI actually run against that candidate;
- relevant state, schema, migration, integration, or runtime contracts;
- authoritative postconditions required for completion.

If the final candidate identity is unclear, report insufficient evidence instead of treating older green results as proof.

## Review procedure

### 1. Reconstruct the actual claim

State what the change claims to accomplish.

Separate:
- implemented behavior;
- tested behavior;
- merged/integrated state;
- deployed/external state;
- operational completion.

Do not silently collapse them.

### 2. Compare intent with the entire diff

Look for:
- unrelated changes;
- omitted integration surfaces;
- partial implementations;
- stale callers/config/docs;
- compatibility assumptions;
- changed behavior not represented in tests.

### 3. Hunt silent-failure classes

Review at least these classes when relevant:

**Coverage gaps**
- happy path tested but negative/edge path absent;
- narrow test promoted into a broad claim;
- focused rerun used as full final-candidate validation.

**State mutation / idempotency**
- delete-before-insert or replace windows;
- partial writes without reconciliation;
- retries that can duplicate side effects;
- lost-update or stale-state overwrite risk;
- resume/checkpoint logic that skips or repeats work.

**Error and fallback semantics**
- exceptions swallowed;
- plausible fallback returned as success;
- missing data converted into favorable/default state;
- partial source failure hidden;
- warnings that should be blockers.

**Data/research integrity**
- denominator silently changes;
- dropped/missing rows silently reweighted or excluded;
- train/test, future-data, or point-in-time leakage;
- stale source treated as current;
- generated evidence from a different candidate/version.

**Schema/version/migration**
- reader/writer version mismatch;
- backward-compatibility gap;
- migration not atomic/restart-safe;
- new field defaults change old semantics;
- serialization round-trip not covered.

**Integration and authority boundaries**
- local pass represented as system-wide pass;
- one component changes without dependent consumer update;
- advisory output treated as execution authorization;
- tool success treated as real-world postcondition success.

### 4. Check negative postconditions

Ask what must **not** have happened.

Examples:
- no accidental deletion;
- no duplicate record/event;
- no silent reweighting;
- no public exposure of private material;
- no stale configuration left active;
- no older green run reused for a mutated final candidate.

Verify deterministically when possible.

### 5. Produce a bounded finding set

Use one of:

- `NO_MATERIAL_FINDING`
- `MATERIAL_FINDINGS`
- `INSUFFICIENT_EVIDENCE`

For each finding provide:

```text
finding:
severity:
evidence:
why_ci_may_miss_it:
user_or_system_impact:
smallest_verification_or_fix:
```

Do not invent defects to justify the review. A clean result is valid.

## Stop conditions

Escalate rather than infer when:
- required authority is missing;
- external state is ambiguous after a write;
- final candidate identity cannot be established;
- evidence needed for a consequential claim is unavailable.

## Completion rule

This skill finishes when every relevant silent-failure class has either:
- concrete evidence of a finding;
- concrete evidence it is covered; or
- an explicit not-applicable / insufficient-evidence disposition.

It does not merge, deploy, publish, or grant authority.
