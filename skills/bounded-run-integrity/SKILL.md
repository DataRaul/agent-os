---
name: bounded-run-integrity
description: Verify consequential bounded evidence-producing runs from declared contract through execution evidence, persistence, positive and negative postconditions, and final classification. Use when workflow/process success is weaker than proof that the intended candidate actually ran, produced current evidence, preserved protected state, and met declared thresholds.
---

# Bounded Run Integrity

## Purpose

Verify the full lifecycle of a consequential bounded evidence-producing run without replacing the project-native runner.

Use this skill when a run can exit successfully while still producing the wrong, stale, partial, duplicated, corrupted, or insufficient result.

This skill is task-class based. It does not grant execution authority, credentials, API access, file/network permissions, deployment permission, publication permission, or project-specific success thresholds.

## Activation

Activate for work class `BOUNDED_EVIDENCE_PRODUCING_RUN` when process success is weaker than the required project postcondition.

Typical examples include:

- bounded discovery or acquisition pilots;
- corpus ingestion, indexing, repair, migration, or reconciliation runs;
- research or universe-expansion pilots that produce decision evidence;
- scheduled or manual collectors whose persisted output controls a later decision;
- bounded acceptance runs that must prove candidate-specific runtime state.

Do not activate for ordinary lint/unit tests, trivial read-only status checks, small documentation changes, or runs whose deterministic existing checks already prove the complete required postcondition.

## Required inputs

Obtain the smallest sufficient set of:

- project or repository context supplied by the caller;
- exact candidate, commit, version, configuration, or other bounded identity when applicable;
- project-native runner/workflow identity;
- declared inputs/configuration;
- externally established authority source for the underlying run;
- preconditions and success thresholds defined before execution;
- required positive postconditions;
- required negative postconditions;
- persistence requirements;
- protected/frozen state requirements;
- authoritative evidence for the exact run.

If the candidate or evidence binding is ambiguous, return insufficient evidence.

## Procedure

### 1. Freeze the declared run contract

Before evaluating execution, record:

- candidate identity;
- runner identity;
- input/configuration identity or digest;
- required preconditions;
- positive postconditions;
- negative postconditions;
- persistence requirement;
- protected-state checks;
- whether a bounded partial result is explicitly allowed.

Do not infer success thresholds after observing the result.

### 2. Verify preconditions

Confirm that:

- execution authority already exists outside this capability;
- required inputs/configuration are present;
- source/quota/environment preconditions are declared where relevant;
- success thresholds are explicit.

A precondition failure is a run-integrity failure. Unknown required preconditions are insufficient evidence.

### 3. Verify actual execution

Establish that:

- the intended runner executed;
- the intended candidate/configuration executed;
- expected work occurred rather than silently short-circuiting;
- partial source/API failures remain visible.

A green workflow or zero exit code is evidence only. It cannot by itself produce `RUN_INTEGRITY_PASS`.

### 4. Bind outputs to this run

Verify that required artifacts/evidence:

- exist;
- belong to the exact candidate/configuration;
- are fresh enough for the claim;
- satisfy declared volume/coverage/quality thresholds;
- persisted when persistence is required.

Reject stale artifacts, prior-run reuse, wrong-candidate evidence, and cumulative state that hides the current run's shortfall.

### 5. Verify negative postconditions

Check, when relevant:

- no unintended deletion;
- no duplicate effects from retry/resume;
- no protected/frozen state overwrite;
- no stale artifact reused as current evidence;
- no wrong candidate/branch/version persisted;
- no silent partial failure represented as PASS;
- no undeclared authority expansion;
- no workflow-green status substituted for project postcondition proof.

Use `state-mutation-idempotency`, `provenance-freshness`, or other existing skills when their narrower semantics are needed.

### 6. Classify the run

Use exactly one disposition:

- `RUN_INTEGRITY_PASS` — all required evidence, positive postconditions, negative postconditions, persistence, binding, and protected-state checks pass.
- `RUN_INTEGRITY_PARTIAL` — the declared contract explicitly allows a bounded partial result, the partial condition is visible, and every other required integrity check passes.
- `RUN_INTEGRITY_FAILED` — authoritative evidence proves a required precondition/postcondition failed, the wrong/stale candidate was used, expected work did not occur, protected state changed, or disallowed partial/duplicate/corrupt effects occurred.
- `RUN_INTEGRITY_INSUFFICIENT_EVIDENCE` — authoritative evidence, freshness, candidate binding, or another required integrity surface cannot be established.

Project-native PASS/HOLD/FAIL business semantics remain defined by the project/task contract. This disposition only classifies run integrity.

## Receipt contract

Produce a receipt compatible with `schemas/bounded-run-integrity-receipt.schema.json` containing:

- capability and contract version;
- work class;
- candidate identity;
- runner identity;
- declared run-contract digest;
- inputs/configuration digest;
- precondition results;
- execution evidence;
- produced artifact identities;
- positive postcondition results;
- negative postcondition results;
- protected-state checks;
- observed failures/warnings;
- final disposition;
- authority source declaration;
- `authority_granted=false`.

Public receipts and fixtures must remain generic. Do not copy private mappings, secrets, credentials, private thresholds, Knowledge Core material, or private calibration observations into this repository.

## Composition

Use only the smallest sufficient chain.

Typical composition:

- `semantic-pr-review` when the run implementation/configuration changed;
- `state-mutation-idempotency` when durable state mutates;
- `bounded-run-integrity` for the execution lifecycle;
- `provenance-freshness` when lineage/freshness controls evidence quality;
- `research-data-integrity` when the resulting dataset supports analytical conclusions;
- `verified-completion` for the final completion claim.

This skill orchestrates run-lifecycle verification. It does not duplicate the full contracts of those skills.

## Stop conditions

Do not return PASS when:

- authoritative evidence is unavailable;
- candidate/configuration binding is ambiguous;
- expected work may have short-circuited;
- a required threshold is unmet;
- stale or prior-run evidence may have been reused;
- retry/resume safety is unresolved for a mutating run;
- protected-state integrity is unknown;
- an authority boundary would need to be widened.

## Completion rule

The review is complete only when every required lifecycle surface has an explicit PASS, FAIL, PARTIAL-allowed, or insufficient-evidence disposition and the receipt is bound to the exact run contract.
