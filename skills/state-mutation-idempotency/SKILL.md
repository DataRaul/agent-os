---
name: state-mutation-idempotency
description: Review state-changing operations for safe retries, partial writes, duplicate effects, overwrite or delete hazards, and restart/recovery correctness. Use before approving or claiming completion for migrations, sync jobs, refreshes, imports, deployments, reconciliations, or other workflows that may be retried or interrupted.
---

# State Mutation and Idempotency

## Purpose

Verify that a state-changing workflow has bounded, understandable effects under success, failure, interruption, and retry.

This skill does not grant authority to perform mutations. It reviews mutation semantics and recovery safety.

## Required inputs

Obtain the smallest sufficient set of:

- the intended state transition;
- the operation sequence or implementation diff;
- the authoritative state store or target;
- identifiers or uniqueness constraints used to distinguish operations;
- retry, resume, checkpoint, rollback, or reconciliation behavior;
- relevant transaction or atomicity guarantees;
- required positive and negative postconditions.

If mutation ordering, uniqueness semantics, or recovery behavior cannot be determined, return insufficient evidence rather than assuming retries are safe.

## Review procedure

### 1. Model the transition

Describe:

- pre-state;
- intended mutation;
- post-state;
- external side effects;
- irreversible steps;
- retryable steps.

Separate logical idempotency from transport success. A repeated request returning success is not proof that repeated execution is harmless.

### 2. Identify mutation identity

Determine how duplicate execution is recognized.

Check for:

- stable operation or event IDs;
- natural or explicit idempotency keys;
- uniqueness constraints;
- compare-and-set/version guards;
- deduplication windows;
- source checkpoints.

If the operation has no stable identity, determine whether duplicate side effects are possible.

### 3. Check ordering and atomicity

Review whether partial progress can expose an invalid state.

Look for:

- delete-before-insert windows;
- truncate-then-rebuild behavior;
- multi-table writes without atomicity or reconciliation;
- external side effect before durable checkpoint;
- checkpoint before side effect is actually complete;
- state publication before dependent writes finish.

When atomicity is unavailable, require an explicit recovery/reconciliation path.

### 4. Exercise retry classes

Reason through at least:

- retry before any write;
- retry after partial local write;
- retry after durable write but before acknowledgement;
- retry after external side effect but before checkpoint;
- process restart from checkpoint;
- concurrent duplicate invocation when relevant.

For each class, identify whether the result is:

- same final state;
- harmless duplicate;
- detected conflict;
- repairable partial state;
- unsafe ambiguity.

### 5. Check overwrite and lost-update risk

Look for:

- blind replacement of newer state;
- stale snapshot writes;
- last-write-wins hiding concurrent change;
- recovery that restores obsolete state;
- broad delete/update predicates;
- missing version checks.

### 6. Verify negative postconditions

Check that retries or failures do not cause:

- duplicate records/events/messages/charges;
- accidental deletion;
- skipped work;
- double application of increments;
- lost newer state;
- unbounded repeated side effects;
- falsely advanced checkpoints;
- unrecoverable partial state.

### 7. Classify recovery

Use the narrowest applicable classification:

- `IDEMPOTENT_BY_DESIGN` — repeated execution converges to the same intended state;
- `IDEMPOTENT_WITH_GUARD` — retries are safe because a defined key/version/constraint prevents duplicate effects;
- `RECONCILABLE_NON_IDEMPOTENT` — duplicates or partial effects can occur but are deterministically detected and repaired;
- `UNSAFE_MUTATION` — a plausible retry/failure path can create material duplicate, loss, corruption, or irreversible ambiguity;
- `INSUFFICIENT_EVIDENCE` — mutation or recovery semantics cannot be established.

## Output contract

Return:

```text
mutation:
authoritative_state:
operation_identity:
atomicity:
retry_cases:
overwrite_risk:
negative_postconditions:
recovery_class:
findings:
smallest_fix_or_verification:
```

## Stop conditions

Do not infer safety when:

- the operation identity is unknown;
- retries can reach an external side effect whose duplicate semantics are unknown;
- a destructive step can precede durable replacement without proven recovery;
- concurrent writers exist but conflict semantics are unavailable;
- checkpoints cannot be tied to completed effects.

## Completion rule

A mutation review is complete only when success, interruption, retry, and recovery paths have explicit dispositions and the required negative postconditions are either proven or identified as unresolved.

This skill reviews mutation behavior. It does not execute the mutation or grant permission to do so.
