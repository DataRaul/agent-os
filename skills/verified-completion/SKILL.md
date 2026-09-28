---
name: verified-completion
description: Verify that a claimed completion state is actually true in the authoritative final state. Use before reporting work as done, merged, deployed, migrated, indexed, published, synchronized, or otherwise complete when command success, CI, or intermediate evidence may not prove the required postconditions.
---

# Verified Completion

## Purpose

Turn a completion claim into a bounded, evidence-backed verification of the required final state.

This skill distinguishes successful actions from successful outcomes. It does not grant authority to mutate systems, merge, deploy, publish, or approve work.

## Required inputs

Obtain the smallest sufficient set of:

- the exact completion claim;
- the target object, system, or state;
- the authoritative source or source hierarchy for that claim;
- the candidate identity, version, commit, artifact, or run identifier when applicable;
- required positive postconditions;
- required negative postconditions;
- any freshness or time boundary that makes evidence current enough.

If the authoritative source is unknown or cannot be accessed, do not substitute a convenient proxy without marking the evidence insufficient.

## Verification procedure

### 1. Normalize the claim

Rewrite the claim as explicit state assertions.

Examples:

- "the change is merged" -> the target pull request is merged and the default branch contains the intended candidate;
- "the deployment is complete" -> the intended artifact/version is serving in the target environment;
- "the migration finished" -> the authoritative data/schema state satisfies the migration contract;
- "the index is ready" -> the authoritative index state satisfies expected coverage and integrity constraints.

Separate:

- command/tool success;
- validation success;
- integration/merge state;
- deployed/external state;
- operational completion.

A prior step succeeding is not proof that a later state exists.

### 2. Establish the authority hierarchy

Identify which source can prove each assertion.

Prefer the source that owns the final state, for example:

- default-branch state for repository integration;
- target runtime state for deployment;
- authoritative datastore state for data completion;
- canonical published surface for publication.

Secondary logs, local files, generated reports, cached views, summaries, and agent narration may support a claim but must not override contradictory authoritative state.

### 3. Bind evidence to the exact candidate

Verify that evidence belongs to the candidate being claimed complete.

Check when relevant:

- commit or artifact identity;
- target environment;
- version/schema identifier;
- run identifier;
- timestamp or freshness;
- whether the candidate changed after the evidence was produced.

Older green evidence does not validate a mutated final candidate.

### 4. Verify positive postconditions

Check every required final-state assertion.

For each assertion record:

- required state;
- evidence source;
- observed state;
- pass/fail/unknown.

Do not widen a narrow observation into a broader completion claim.

### 5. Verify negative postconditions

Check what must not have happened.

Examples:

- no duplicate side effect;
- no accidental deletion;
- no partial or stale state presented as complete;
- no wrong environment/version active;
- no private material exposed;
- no unresolved human/authority gate bypassed.

A completion claim is not verified if a required negative postcondition remains materially uncertain.

### 6. Reconcile cross-system claims

When completion spans multiple systems, verify each boundary independently.

Examples:

- merged does not imply deployed;
- deployed does not imply healthy;
- job success does not imply authoritative data completeness;
- file creation does not imply publication;
- tool acceptance does not imply real-world execution.

Report the narrowest state that is actually proven.

## Output contract

Return exactly one disposition:

- `VERIFIED_COMPLETE` — all required positive and negative postconditions are proven against sufficiently fresh authoritative state;
- `VERIFIED_PARTIAL` — a bounded subset is proven, but the original claim is broader;
- `NOT_COMPLETE` — authoritative evidence contradicts at least one required postcondition;
- `INSUFFICIENT_EVIDENCE` — required authoritative or candidate-specific evidence is unavailable or too stale.

Include:

```text
claim:
candidate_identity:
authoritative_sources:
positive_checks:
negative_checks:
freshness:
disposition:
unresolved_blockers:
```

## Stop conditions

Do not infer completion when:

- authoritative state cannot be identified;
- the candidate identity is ambiguous;
- evidence predates a material candidate change;
- external state is inconsistent across authoritative surfaces;
- a required human or system authority gate remains unresolved.

## Completion rule

Use `VERIFIED_COMPLETE` only when every required final-state and negative postcondition is supported by candidate-specific, sufficiently fresh authoritative evidence.

This skill verifies state. It does not create authority or perform the state-changing action itself.
