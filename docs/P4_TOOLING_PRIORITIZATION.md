# P4 tooling prioritization

## Purpose

P4.1 converts the normalized tooling inventory into a deterministic, fail-closed candidate queue for narrow P4.2 audits.

Prioritization is not admission. It does not install a plugin, authenticate an account, run vendor code, connect an MCP server, or grant authority.

## Deterministic policy

Only `SOURCE_AUDITED` subcapabilities can enter the initial queue. Marketplace entries whose write, destructive, publish, or credential scopes remain unknown are deferred until a narrow audit resolves those surfaces.

Risk signals are mapped by precedence into the six P4 groups:

1. specification/reference-only helpers;
2. local deterministic analysis/validation;
3. isolated read-only observation;
4. authenticated or sensitive reads;
5. write, execution, or installation surfaces;
6. destructive, publication, send, financial, security-policy, or broad-administration surfaces.

The initial P4.2 queue draws only from groups 1–3, sorts deterministically by group and capability ID, and is capped at five entries.

The executable policy is `scripts/build_tooling_priority_queue.py`; the committed result is `catalog/tooling-priority-queue.json`.

## Current result

- 48 source-audited subcapabilities classified;
- 65 marketplace entries deferred because their authority remains unresolved;
- priority groups: 2 / 0 / 1 / 6 / 28 / 11;
- initial queue: 3 candidates.

Initial P4.2 audit order:

1. `agent-skills-standard:skill-format-specification`;
2. `agent-skills-standard:skills-ref-reference-library`;
3. `microsoft-playwright-skills:browser-observation`.

All three remain `REFERENCE_ONLY` until their P4.2 audit and P4.3 evidence justify a different disposition.

## Explicitly authorized second tranche

The deterministic initial queue remains unchanged. A later explicit bounded authorization selected all six already-classified priority-group 4 candidates for a separate source-reconciled, non-runtime follow-up: `cloudflare-skills:cloudflare`, four DuckDB surfaces (`convert-file`, `query`, `read-memories`, `s3-explore`), and `microsoft-playwright-skills:persistent-and-attached-sessions`.

That follow-up does not reinterpret group 4 as automatically admissible and does not widen the marketplace. See `docs/P4_SECOND_TOOLING_TRANCHE.md`.

## Terminal

`P4_TOOLING_PRIORITIZATION_V1_READY__P4_2_NARROW_AUDITS_NEXT`
