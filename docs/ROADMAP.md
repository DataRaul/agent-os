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

Status: `BLINDED_RUN_PACKET_V1_READY__EXECUTION_RECEIPT_V1_READY__PER_RUN_COLLECTION_V1_READY__ATTEMPT_LEDGER_V1_READY`

The deterministic benchmark/scorer is paired with oracle-isolated baseline and reviewer run packets plus packet-bound execution-receipt tooling. Whole-packet single-session receipts remain supported; deterministic oracle-free tooling now preserves one fresh executor-session reference per case/replicate and an append-only attempt ledger can safely resume interrupted manual execution without erasing failed attempts or accepting post-completion reruns. The assembler requires disjoint baseline/reviewer executor sessions, matching model configuration labels, exact packet digests, and no declared oracle/peer-output exposure before it can produce scorer input. Specialist reviewers are admitted only when actual independent comparative runs demonstrate incremental value over the primary-agent + skills baseline. No specialist candidate is implemented or admitted by packet or receipt infrastructure.

## P3 — Vendor/source trust baseline

Status: `COMPLETE`

Official/vendor provenance is catalogued and audited without granting blanket execution authority.

## P4 — Tooling layer expansion

Status: `P4_BOUNDED_TRANCHE_COMPLETE__MARKETPLACE_REFERENCE_AUDIT_V1`

- P4.0 inventory — complete;
- P4.1 deterministic prioritization — complete;
- P4.2 bounded narrow audits — complete;
- P4.3 admission/value evidence — complete;
- P4.4 delivery gate — complete for the initial bounded tranche.

P4 is bounded capability evaluation, not a mandate to exhaust every marketplace entry.

A local CSV query adapter candidate is documented in `docs/P4_DUCKDB_LOCAL_ADHOC_ADAPTER.md`. Its narrow invocation and fail-closed boundaries are deterministically contract-tested in CI; it remains evaluation-only, outside the capability registry and without runtime admission.

A bounded OpenAI plugin-format reference audit is documented in `docs/P4_OPENAI_PLUGIN_FORMAT_REFERENCE_AUDIT.md`. It admits only read-only manifest/marketplace format evidence as `REFERENCE_ONLY`; plugin installation, authentication, MCP connection, creator-script execution, filesystem writes, and marketplace mutation remain excluded.

## P4R — Public capability registry

Status: `FOUNDATION_V1__STRUCTURAL_VALIDATION_HARDENED`

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

Status: `DECLARATIVE_CONTRACT_V1_COMPLETE__PIN_AND_REGISTRY_DIGEST_BINDING_V1_COMPLETE`

The first bounded tranche defines a public, vendor-neutral selection-request schema and public-safe structural cases. A deterministic pinned-registry verifier now confirms SHA/ID/contract-version binding against an already reviewed local registry while explicitly granting no authority. It performs no selection, composition, adapter execution, network lookup, or authority grant. See `docs/P5_GENERIC_SELECTION_CONTRACT.md`. Any executable router/adapter work requires a separate bounded selection and approval; private activation remains behind its own portfolio gate.

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


## Cross-cutting public hardening

Status: `VALIDATION_PUBLICATION_REGISTRY_AND_P2_RESUME_HARDENING_V1`

The bounded hardening tranche strengthens publication-gate self-tests and credential-path detection, registry/path/version invariants, optional exact registry-digest binding, and resumable P2 manual-attempt evidence. It adds no reviewer admission, executable routing, private dependency, external installation, authentication, or paid model execution.
