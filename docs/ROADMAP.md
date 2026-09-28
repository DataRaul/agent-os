# Public Agent OS roadmap

This roadmap contains only generic public work. It must remain useful without any private project, private overlay or private knowledge system.

## V0 — Public core

Status: `COMPLETE`

- public/private firewall;
- generic architecture and trust model;
- complexity routing;
- Silent Failure Hunter / Reviewer;
- deterministic validation.

## P1 — Reusable capability baseline

Status: `COMPLETE`

Public skills:

- `silent-failure-hunter`;
- `verified-completion`;
- `state-mutation-idempotency`;
- `provenance-freshness`;
- `research-data-integrity`;
- `authority-boundary-review`;
- `semantic-pr-review`.

## P2 — Specialist reviewer evaluation

Status: `EVALUATION_HARNESS_READY`

Specialist reviewers are admitted only when controlled evaluation demonstrates incremental value over the primary-agent + skills baseline.

## P3 — Vendor/source trust baseline

Status: `COMPLETE`

Official/vendor provenance is catalogued and audited without granting blanket execution authority.

## P4 — Tooling layer expansion

Status: `P4_BOUNDED_TRANCHE_COMPLETE`

- P4.0 inventory — complete;
- P4.1 deterministic prioritization — complete;
- P4.2 bounded narrow audits — complete;
- P4.3 admission/value evidence — complete;
- P4.4 delivery gate — complete for the initial bounded tranche.

P4 is bounded capability evaluation, not a mandate to exhaust every marketplace entry.

## P4R — Public capability registry

Status: `FOUNDATION_V1`

Maintain `catalog/capability-registry.json` as the public machine-readable interface for reusable capabilities.

Rules:

- stable public capability IDs;
- explicit capability contract versions;
- exact repository SHA is the authoritative implementation identity;
- registry membership does not grant execution authority;
- discovered/audited vendor tools do not enter automatically;
- no private mappings, routes, selection decisions or fixtures;
- consumers pin and review before adopting newer public state.

P4R may evolve alongside P4; it does not widen tool admission.

## P5 — Generic capability router / adapter contract

Status: `AWAITS_CONSUMER_SELECTION_EVIDENCE`

Define a public, vendor-neutral interface for selecting and composing registered capabilities without embedding any consumer-specific project mappings.

The public router contract may express generic inputs such as:

- capability ID;
- work/complexity class;
- declared authority class;
- required preconditions;
- output/postcondition contract.

It must not contain private repository identities or require access to a private control plane.

## Dependency invariant

```text
public Agent OS
    ↓ consumed/pinned by
optional private or organizational overlay
    ↓ maps to
local projects
```

Never reverse this arrow. Public development, CI, tests and runtime must not depend on private overlay access.

## Public evolution rule

A private observation may motivate a generic capability, but public evolution uses only a sanitized generic candidate plus public-safe evals. Public changes become consumable only after public validation, publication safety review and exact-main verification.
