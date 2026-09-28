---
name: provenance-freshness
description: Verify that evidence comes from the right source, can be traced to its origin, is current enough for the claim, and is bound to the correct candidate or state. Use for research, status checks, validations, generated reports, cached data, mirrored sources, or completion claims where stale or weakly sourced evidence could mislead.
---

# Provenance and Freshness

## Purpose

Verify that evidence is attributable, authoritative enough for the claim, current enough for the decision, and tied to the exact object or state being evaluated.

This skill evaluates evidence quality. It does not grant authority to act on that evidence.

## Required inputs

Obtain the smallest sufficient set of:

- the claim being supported;
- the evidence items used to support it;
- source identities and source hierarchy;
- retrieval, publication, observation, or generation timestamps;
- candidate/version/environment identifiers when applicable;
- transformation lineage for derived evidence;
- the freshness requirement implied by the claim.

If origin, date, candidate binding, or source authority is materially unknown, report insufficient evidence rather than silently accepting the evidence.

## Review procedure

### 1. Define the claim and its freshness horizon

State what is being claimed and how current the evidence must be.

Examples:

- a historical fact may tolerate older authoritative evidence;
- a live deployment status requires current target-state evidence;
- a market, policy, schedule, availability, or runtime claim may become stale quickly;
- a generated validation report is only relevant to the candidate it actually evaluated.

Do not apply one universal age threshold. Freshness is claim-dependent.

### 2. Establish provenance

For each material evidence item identify:

- original source;
- direct or derived status;
- retrieval/publication/observation time;
- transformation steps;
- candidate/version/environment binding;
- whether the source is authoritative, secondary, cached, mirrored, or inferred.

A citation or URL alone does not prove provenance if the underlying material is copied, cached, or transformed without lineage.

### 3. Establish source hierarchy

Prefer evidence from the system or source that owns the truth being claimed.

Check for conflicts between:

- authoritative state and cached summaries;
- primary records and secondary reports;
- live state and generated artifacts;
- current candidate state and evidence from an earlier version.

When sources conflict, do not average them. Explain which source controls the claim and why.

### 4. Check candidate and scope binding

Verify that evidence actually applies to:

- the correct commit/artifact/version;
- the correct environment or population;
- the correct time period;
- the correct geographic or organizational scope;
- the correct dataset slice or denominator.

Evidence can be authentic yet irrelevant to the claim if it is bound to the wrong candidate or scope.

### 5. Check staleness

Look for:

- evidence produced before a material mutation;
- cached views without refresh guarantees;
- reports generated from older snapshots;
- undated screenshots or exports;
- latest-known values presented as current without a retrieval time;
- long-lived summaries whose source data changes independently.

Classify evidence as current, stale, or freshness-unknown relative to the claim.

### 6. Check derivation integrity

For derived evidence, verify that the lineage is understandable enough to reproduce or audit.

Look for:

- missing source identifiers;
- transformations without timestamps;
- aggregation that hides dropped inputs;
- generated reports detached from the candidate they evaluated;
- copied values whose upstream version is unknown.

### 7. Produce a provenance disposition

Use one of:

- `PROVENANCE_FRESHNESS_PASS` — material evidence has adequate origin, authority, scope binding, and freshness;
- `STALE_EVIDENCE` — material evidence is too old relative to the claim;
- `PROVENANCE_MISMATCH` — evidence comes from the wrong source, scope, candidate, or environment;
- `CONFLICTING_AUTHORITATIVE_EVIDENCE` — authoritative sources disagree and the conflict is unresolved;
- `INSUFFICIENT_EVIDENCE` — provenance or freshness cannot be established.

## Output contract

Return:

```text
claim:
freshness_requirement:
source_hierarchy:
evidence_items:
candidate_scope_binding:
staleness_checks:
derivation_lineage:
disposition:
unresolved_gaps:
smallest_next_verification:
```

## Stop conditions

Do not upgrade evidence quality when:

- an authoritative source is unavailable and only a stale proxy remains;
- the evidence predates a material candidate change;
- the population/environment/scope differs from the claim;
- source lineage is missing for a consequential derived result;
- authoritative sources materially conflict.

## Completion rule

A provenance review is complete only when each material evidence item has an explicit origin, scope, freshness, and candidate-binding disposition.

This skill verifies evidence quality. It does not authorize execution or replace domain-specific validity review.
