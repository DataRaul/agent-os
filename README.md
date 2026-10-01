# Agent OS

Agent OS is a public, vendor-neutral operating layer for reliable AI-assisted software, data, research, and project work.

It packages reusable **skills**, **reviewer/verification roles**, **evaluation cases**, **trust rules**, and **routing guidance** without depending on any private project, private knowledge base, credential, or proprietary workflow.

## Design principles

- **Public-safe by construction.** No private repository names, business logic, secrets, credentials, personal data, or sensitive operational state belong here.
- **Skills before swarms.** Prefer one capable agent with the smallest sufficient skills and deterministic tools. Add independent reviewers only when complexity or risk earns the coordination cost.
- **Evidence over narration.** A claim of completion is not completion. Verify the authoritative postcondition.
- **Green CI is scoped evidence.** Passing checks prove only what they actually test.
- **Fail closed on ambiguity.** Missing authority, stale evidence, uncertain side effects, or unverifiable state remain explicit.
- **Portable by default.** Skills follow the open Agent Skills `SKILL.md` convention so they can be reused across compatible clients.
- **Private overlays stay separate.** Project-specific routing, sensitive policies, private eval cases, and private knowledge integrations belong in a separate private layer.

## Intended architecture

```text
Public Agent OS
  ├─ reusable skills
  ├─ generic reviewer/verifier roles
  ├─ eval suites
  ├─ vendor trust metadata
  └─ complexity/routing policy
          │
          ▼
Optional private overlay
  ├─ maps Agent OS capabilities to private projects
  ├─ adds private rules/evals
  └─ routes to private knowledge/reasoning systems
          │
          ▼
Existing project repositories
  └─ remain authoritative for their own code, data, tests, state and permissions
```

## Capability program

V0 established the public core.

P1 established the first reusable capability baseline. Its sequence and build contract are documented in `docs/P1_CAPABILITY_BASELINE.md`.

Current public skills:

- `silent-failure-hunter`
- `verified-completion`
- `state-mutation-idempotency`
- `provenance-freshness`
- `research-data-integrity`
- `authority-boundary-review`
- `semantic-pr-review`

P2 evaluates whether proposed specialist reviewer roles add measurable value beyond one capable primary agent plus the P1 skills. Blinded packets, packet-bound independent execution receipts, deterministic one-run-per-session fragment collection, resumable append-only attempt tracking, and deterministic 90-run manual execution operations are ready; actual comparative model runs remain required before any role can be considered. See `docs/SPECIALIST_REVIEWER_EVALUATION.md`.

P3 completed the initial provenance/authority audit baseline for the public tooling sources. See `docs/P3_VENDOR_CATALOG_BASELINE.md` and `docs/VENDOR_CAPABILITY_ADMISSION.md`.

P4 expands the tooling layer by normalizing and evaluating narrow capabilities from those audited sources, prioritizing bounded read-only/reference capabilities before write-capable integrations. Tooling Inventory V1 is defined in `catalog/tooling-inventory.json`; deterministic P4.1 prioritization is defined in `catalog/tooling-priority-queue.json` and `docs/P4_TOOLING_PRIORITIZATION.md`.

The explicitly authorized P4 second tooling tranche source-reconciles the six priority-group 4 Cloudflare, DuckDB, and Playwright candidates without executing them. All remain non-runtime; no registry promotion or authority grant occurs. See `docs/P4_SECOND_TOOLING_TRANCHE.md`.

Playwright browser observation now also has a two-timepoint synthetic loopback calibration baseline across exact CLI versions 0.1.21 and 0.1.22. It remains pinned and non-runtime. See `docs/P4_PLAYWRIGHT_CALIBRATION.md`.

A third bounded tooling tranche audits five explicitly selected priority-group 5 candidates from Cloudflare, DuckDB, and Playwright without installing or executing them. All remain non-runtime. See `docs/P4_THIRD_TOOLING_TRANCHE.md`.

P5 now also defines deterministic declarative decision, precondition/postcondition, and multi-capability compatibility evidence in `docs/P5_DECLARATIVE_DECISION_CONTRACTS.md`; those contracts explicitly do not create executable routing or grant authority.

The public machine-readable capability interface is `catalog/capability-registry.json`, governed by `docs/CAPABILITY_REGISTRY.md`. Deterministic public release readiness is enforced by `scripts/release_readiness.py` and documented in `docs/RELEASE_READINESS.md`; it emits exact-SHA capability snapshots and fail-closed registry-compatibility evidence but never publishes automatically. Consumers pin an exact Agent OS commit SHA and reference stable capability IDs; registry validation is fail-closed on malformed paths/version metadata, and consumers may additionally bind verification to an exact registry SHA-256. Registry membership never grants execution authority. Public Agent OS never reads or depends on a private overlay. See `docs/ROADMAP.md` for the public-safe phase sequence.

Additional skills or reviewer roles should be added only when they are reusable across projects or ecosystems and the added coordination cost is justified.

## Status

`V0_PUBLIC_CORE_COMPLETE__P1_CAPABILITY_BASELINE_COMPLETE__P2_MANUAL_EXECUTION_OPERATIONS_V1_READY__P3_VENDOR_CATALOG_BASELINE_COMPLETE__P4_BOUNDED_TRANCHE_COMPLETE__P4_SECOND_TOOLING_TRANCHE_V1_COMPLETE__P4_PLAYWRIGHT_CALIBRATION_BASELINE_V1_COMPLETE__P4_THIRD_TOOLING_TRANCHE_V1_COMPLETE__P5_DECLARATIVE_DECISION_CONTRACTS_V1_READY__RELEASE_READINESS_V1`

No release or stability guarantee is implied yet.
