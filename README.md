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

## Initial roadmap

V0 establishes:

1. repository governance and public/private boundary;
2. trust and vendor-skill admission rules;
3. a reusable complexity routing model;
4. the first skill: **Silent Failure Hunter**;
5. evaluator cases that test skills against deceptive as well as normal scenarios.

Additional skills should be added only when they are reusable across projects or ecosystems.

## Status

`BOOTSTRAP_V0_IN_PROGRESS`

No release or stability guarantee is implied yet.
