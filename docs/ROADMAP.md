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

Status: `BLINDED_RUN_PACKET_V1_READY__EXECUTION_RECEIPT_V1_READY__PER_RUN_COLLECTION_V1_READY__ATTEMPT_LEDGER_V1_READY__MANUAL_EXECUTION_OPERATIONS_V1_READY`

The deterministic benchmark/scorer is paired with oracle-isolated baseline and reviewer run packets plus packet-bound execution-receipt tooling. Deterministic manual-execution operations now initialize packet-bound ledgers, import preserved attempts, report exact next pending runs, validate baseline/reviewer session separation, and aggregate the canonical three-pair / 90-run progress state without model execution or oracle access. Whole-packet single-session receipts remain supported; deterministic oracle-free tooling now preserves one fresh executor-session reference per case/replicate and an append-only attempt ledger can safely resume interrupted manual execution without erasing failed attempts or accepting post-completion reruns. The assembler requires disjoint baseline/reviewer executor sessions, matching model configuration labels, exact packet digests, and no declared oracle/peer-output exposure before it can produce scorer input. Specialist reviewers are admitted only when actual independent comparative runs demonstrate incremental value over the primary-agent + skills baseline. No specialist candidate is implemented or admitted by packet or receipt infrastructure.

## P3 — Vendor/source trust baseline

Status: `COMPLETE`

Official/vendor provenance is catalogued and audited without granting blanket execution authority.

## P4 — Tooling layer expansion

Status: `P4_BOUNDED_TRANCHE_COMPLETE__MARKETPLACE_REFERENCE_AUDIT_V1__SECOND_TOOLING_TRANCHE_V1_COMPLETE__PLAYWRIGHT_CALIBRATION_BASELINE_V1_COMPLETE__THIRD_TOOLING_TRANCHE_V1_COMPLETE__DUCKDB_LOCAL_CSV_ADAPTER_V1_ADMITTED`

- P4.0 inventory — complete;
- P4.1 deterministic prioritization — complete;
- P4.2 bounded narrow audits — complete;
- P4.3 admission/value evidence — complete;
- P4.4 delivery gate — complete for the initial bounded tranche.
- P4.5 explicitly authorized priority-group 4 follow-up — complete as a source-reconciled, non-runtime tranche.
- P4.6 Playwright observation shadow calibration — two public loopback timepoints established; runtime admission unchanged.
- P4.7 explicitly authorized priority-group 5 subset — five source-reconciled candidates audited; all remain non-runtime.
- P4.8 DuckDB local CSV aggregate — narrow adapter admitted as a public capability; full upstream DuckDB skill remains reference-only.

P4 is bounded capability evaluation, not a mandate to exhaust every marketplace entry.

The local CSV aggregate adapter is documented in `docs/P4_DUCKDB_LOCAL_ADHOC_ADAPTER.md` and `docs/CAPABILITY_DUCKDB_LOCAL_CSV_AGGREGATE.md`. Its narrow invocation and fail-closed boundaries are deterministically contract-tested in CI; the `duckdb-local-csv-aggregate` capability is now AVAILABLE in registry version 2, while registry membership still grants no file/process authority.

A bounded OpenAI plugin-format reference audit is documented in `docs/P4_OPENAI_PLUGIN_FORMAT_REFERENCE_AUDIT.md`. It admits only read-only manifest/marketplace format evidence as `REFERENCE_ONLY`; plugin installation, authentication, MCP connection, creator-script execution, filesystem writes, and marketplace mutation remain excluded.

The second tooling tranche is documented in `docs/P4_SECOND_TOOLING_TRANCHE.md`. It covers the six previously classified priority-group 4 Cloudflare, DuckDB, and Playwright candidates using refreshed source identities plus synthetic public-safe contracts only. It installs or executes no vendor tooling, uses no credentials or private session data, makes no registry promotion, and grants no runtime authority.

Playwright observation calibration is documented in `docs/P4_PLAYWRIGHT_CALIBRATION.md`. Exact 0.1.21 and 0.1.22 public loopback timepoints now form a minimal shadow-calibration baseline; the candidate remains `PIN_REQUIRED`, non-admitted, and outside the capability registry.

The third tooling tranche is documented in `docs/P4_THIRD_TOOLING_TRANCHE.md`. It covers a bounded five-candidate priority-group 5 subset selected under explicit authorization. The tranche is source inspection plus synthetic contract evaluation only; priority groups 5 and 6 remain closed to automatic expansion.

The bounded DuckDB local CSV aggregate adapter is now admitted as public capability `duckdb-local-csv-aggregate` after real synthetic CLI boundary evidence plus deterministic contract tests. Registry membership grants no file/process authority, and the broader DuckDB source package remains reference-only. See `docs/CAPABILITY_DUCKDB_LOCAL_CSV_AGGREGATE.md`.

## P4R — Public capability registry

Status: `FOUNDATION_V1__STRUCTURAL_VALIDATION_HARDENED__DUCKDB_LOCAL_CSV_ADAPTER_V1_ADMITTED`

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

Status: `DECLARATIVE_CONTRACT_V1_COMPLETE__PIN_AND_REGISTRY_DIGEST_BINDING_V1_COMPLETE__DECISION_PRECONDITION_POSTCONDITION_AND_COMPOSITION_V1_COMPLETE__BOUNDED_EXECUTABLE_FIXTURE_ROUTER_V1_COMPLETE`

The first bounded tranche defines a public, vendor-neutral selection-request schema and public-safe structural cases. A deterministic pinned-registry verifier now confirms SHA/ID/contract-version binding against an already reviewed local registry while explicitly granting no authority. It performs no selection, composition, adapter execution, network lookup, or authority grant. See `docs/P5_GENERIC_SELECTION_CONTRACT.md`. Any executable router/adapter work requires a separate bounded selection and approval; private activation remains behind its own portfolio gate. A second declarative tranche adds exact-SHA/digest-bound decision evidence for the already-declared capability, explicit rejection reason codes, precondition and postcondition result shapes, and generic multi-capability compatibility declarations. These contracts perform no dynamic capability search, adapter loading, execution, orchestration, or authority grant. See `docs/P5_DECLARATIVE_DECISION_CONTRACTS.md`.

A separately authorized executable prototype is documented in `docs/P5_BOUNDED_EXECUTABLE_ROUTER.md`. It proves the execution plumbing only with one built-in side-effect-free synthetic adapter and a synthetic registry. It performs no dynamic import, subprocess, network, credential, filesystem mutation, vendor execution, real capability routing, or public-registry promotion. Connecting a real adapter remains separately gated.

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

Status: `VALIDATION_PUBLICATION_REGISTRY_P2_RESUME_AND_RELEASE_READINESS_V1__SNAPSHOT_INPUT_HARDENING_V1__STABLE_V1_0_0_PUBLISHED`

The bounded hardening tranche strengthens publication-gate self-tests and credential-path detection, registry/path/version invariants, optional exact registry-digest binding, and resumable P2 manual-attempt evidence. A deterministic release-readiness gate now cross-checks core validators, public documentation paths, exact-SHA capability snapshots, registry digests, changelog treatment, and compatibility rules for capability evolution without publishing or advancing any consumer pin. Retained snapshots are independently revalidated before compatibility comparison so malformed digests, invalid capability rows, or any authority-bearing snapshot evidence fail closed. It adds no reviewer admission, executable routing, private dependency, external installation, authentication, or paid model execution.

Stable GitHub release `v1.0.0` is published at exact commit `62fd8466971f4c8055ffefa3606d1cb1e28c7974` after deterministic RC stable-surface validation. The stable release remains limited to the AVAILABLE capability contracts and listed public interfaces; P2 specialist candidates, the P5 fixture router as a production runtime, non-admitted vendor tooling, and Playwright observation remain experimental exclusions. Consumer/private-overlay pin advancement has not occurred and remains separately gated.
