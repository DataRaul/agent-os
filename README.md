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

V0 established:

1. repository governance and the public/private boundary;
2. trust and vendor-skill admission rules;
3. reusable complexity routing;
4. **Silent Failure Hunter** plus an independent reviewer role;
5. deterministic repository validation and public-safe evals.

P1 expands the reusable capability baseline. Its sequence and build contract are documented in `docs/P1_CAPABILITY_BASELINE.md`.

Current public skills:

- `silent-failure-hunter`
- `verified-completion`

Additional skills should be added only when they are reusable across projects or ecosystems.

## Status

`V0_PUBLIC_CORE_COMPLETE__P1_CAPABILITY_BASELINE_IN_PROGRESS`

No release or stability guarantee is implied yet.
