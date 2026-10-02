# Bounded Run Integrity V1

Status: `PUBLIC_GENERIC_CAPABILITY_CANDIDATE`

## Purpose

`bounded-run-integrity` verifies consequential bounded evidence-producing runs whose process success is weaker than the project postcondition that matters.

The capability does not execute a project runner. It verifies evidence produced by an already-authorized project-native run and classifies whether the run lifecycle is sufficiently proven.

Work class:

`BOUNDED_EVIDENCE_PRODUCING_RUN`

## Activation model

The capability is not always on.

Activate it when a bounded run produces evidence or durable state that controls a later decision and a zero exit code, green workflow, or successful API response does not prove the intended outcome.

Do not activate it for ordinary deterministic tests whose existing assertions already prove the complete required postcondition.

## Lifecycle contract

A run-integrity review binds together:

1. caller-supplied context identity plus exact run, candidate, and runner identity;
2. declared inputs/configuration;
3. preconditions and predeclared thresholds;
4. evidence that the intended work actually occurred;
5. fresh output/artifact identity;
6. persistence when required;
7. positive postconditions;
8. negative postconditions;
9. protected-state checks when applicable;
10. final run-integrity disposition.

The contract fails closed when candidate/evidence binding or authoritative evidence is unavailable.

## Dispositions

- `RUN_INTEGRITY_PASS`
- `RUN_INTEGRITY_PARTIAL`
- `RUN_INTEGRITY_FAILED`
- `RUN_INTEGRITY_INSUFFICIENT_EVIDENCE`

`RUN_INTEGRITY_PARTIAL` is valid only when the declared run contract explicitly permits a bounded partial result and every other required integrity check passes.

These dispositions classify the integrity of the run lifecycle. Project-specific business or research PASS/HOLD/FAIL semantics remain outside this capability.

## Deterministic public evidence

The public implementation contains:

- skill contract: `skills/bounded-run-integrity/SKILL.md`;
- deterministic generic evals: `evals/bounded-run-integrity/cases.json`;
- classifier: `scripts/bounded_run_integrity.py`;
- deterministic tests: `scripts/test_bounded_run_integrity.py`;
- receipt schema: `schemas/bounded-run-integrity-receipt.schema.json`.

The eval corpus covers clean success, runner-green threshold failure, visible partial-source failure, stale evidence, wrong candidate binding, retry duplication, protected-state corruption, unavailable authoritative evidence, and explicitly allowed partial results.

No public fixture contains a private project identity or project-specific threshold.

## Receipt

The classifier emits a `BOUNDED_RUN_INTEGRITY_RECEIPT` that includes:

- capability and contract version;
- work class;
- caller context identity digest plus run, candidate, and runner identity;
- run-contract and input/configuration digests;
- precondition results;
- execution evidence;
- artifact identities;
- positive and negative postcondition results;
- protected-state checks;
- observed failures/warnings;
- final disposition;
- authority source declaration;
- `authority_granted=false`.

The receipt is evidence, not execution permission.

## Composition

Use the smallest sufficient capability chain.

When relevant:

- use `semantic-pr-review` if the run implementation or configuration changed;
- use `state-mutation-idempotency` for durable mutation/retry safety;
- use `bounded-run-integrity` for the actual execution lifecycle;
- use `provenance-freshness` for evidence lineage/freshness;
- use `research-data-integrity` when the resulting dataset supports analytical conclusions;
- use `verified-completion` for the final completion claim.

The new capability owns orchestration-level lifecycle verification and intentionally does not reproduce those narrower contracts.

## Authority and privacy boundary

Registry membership grants no authority.

The capability does not:

- trigger workflows;
- call external APIs;
- use credentials;
- write project state;
- deploy or publish;
- select a private project;
- create scheduled infrastructure;
- define private project thresholds.

A consumer or private overlay supplies project eligibility, authority, routing, and any private calibration evidence. Public Agent OS remains independent of that overlay.

## Calibration boundary

Real project calibration may occur only in the consuming environment after the exact public candidate is reviewed and adopted there.

Public Agent OS must not fabricate real calibration evidence. Synthetic fixtures prove only deterministic contract behavior.
