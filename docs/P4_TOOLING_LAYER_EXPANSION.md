# P4 tooling layer expansion

## Goal

Turn evidence-bound source catalogs into a normalized capability inventory before any narrow runtime admission.

P4 is intentionally inventory-first. Discovery does not install tools, authenticate accounts, execute vendor scripts, connect MCP servers, deploy, publish, send messages, delete data, or mutate external state.

## Inventory V1

The machine-readable snapshot is `catalog/tooling-inventory.json`.

Current snapshot:

- 5 audited source catalogs;
- 65 OpenAI marketplace plugin entries;
- 48 source-audited subcapability records;
- 31 marketplace entries with MCP manifests;
- 27 marketplace entries with script surfaces;
- 3 marketplace entries sourced from external repositories.

These counts describe structural discovery, not safety or value rankings.

## Fail-closed authority model

Every marketplace plugin discovered from the broad marketplace remains `REFERENCE_ONLY` and `DISCOVERED_NOT_NARROW_AUDITED`.

Until a narrow audit resolves them, the inventory records these authority fields as unknown:

- remote write scope;
- destructive scope;
- publish scope;
- credential scope.

An unknown scope cannot be upgraded by marketplace curation, official provenance, installation availability, or an `allowed-tools` declaration.

## Structural signals

Inventory records observable source structure without pretending structure proves behavior:

- skills present;
- MCP manifest present;
- app manifest present;
- scripts present;
- commands present;
- hooks present;
- agent definitions present;
- marketplace authentication policy;
- local versus external marketplace source.

Semantic side effects still require a narrow audit.

## P4 sequence

### P4.0 — inventory

Status: implemented by Tooling Inventory V1.

### P4.1 — deterministic prioritization

Status: implemented by Tooling Priority Queue V1.

The queue is generated from the inventory by `scripts/build_tooling_priority_queue.py` and committed as `catalog/tooling-priority-queue.json`.

The classifier uses explicit risk-signal precedence rather than subjective scores:

1. specification/reference-only helpers;
2. local deterministic analysis/validation;
3. isolated read-only observation;
4. authenticated or sensitive reads;
5. write, execution or installation surfaces;
6. destructive, publish/send, financial, security-policy or broad-administration surfaces.

Broad marketplace entries remain deferred while their authority scopes are unknown. The initial P4.2 queue is limited to source-audited groups 1–3, sorted deterministically and capped at five candidates.

Current queue:

1. `agent-skills-standard:skill-format-specification`;
2. `agent-skills-standard:skills-ref-reference-library`;
3. `microsoft-playwright-skills:browser-observation`.

No admission state changes in P4.1.

### P4.2 — narrow audits

Status: completed for the bounded initial three-candidate queue. See `catalog/p4-narrow-audits.json`, `catalog/p4-narrow-audit-cases.json`, and `docs/P4_NARROW_AUDITS.md`.

For a selected candidate:

- bind exact upstream commit/path/version;
- inspect instructions, scripts and tool definitions;
- enumerate positive and negative side effects;
- define required authority;
- create public-safe eval cases;
- decide `REFERENCE_ONLY`, `SKILL_ALLOWED`, `PLUGIN_ALLOWED`, `PIN_REQUIRED`, or `REJECTED`.

### P4.3 — admission evidence

Status: completed for the bounded initial tranche. See `catalog/p4-admission-evidence.json` and `docs/P4_ADMISSION_EVIDENCE.md`.

No capability is admitted merely because a narrow audit found no obvious hazard.

Where practical, compare the candidate against the existing Agent OS baseline for:

- incremental task value;
- material errors prevented;
- false positives/failures;
- tool/latency overhead;
- authority cost.

### P4.4 — delivery gate

Every inventory/admission mutation must pass:

- deterministic Agent OS validation;
- publication safety gate;
- semantic review;
- exact-main post-merge verification.

### P4R — capability registry publication

A vendor/tool candidate is not a reusable public Agent OS capability merely because P4 audited it. After the applicable P4.2–P4.4 gates establish a public reusable capability, publish its stable ID and contract metadata in `catalog/capability-registry.json` under `docs/CAPABILITY_REGISTRY.md`.

The registry contains no private selection/mapping and grants no authority. Consumers pin an exact public repository SHA before adopting a registry revision.

## Update rule

`catalog/tooling-inventory.json` is a dated evidence snapshot, not a live auto-update channel.

Upstream changes require a new bounded inventory candidate. Do not silently refresh or inherit admission across changed commits.

## Terminal for this step

`P4_3_ADMISSION_EVIDENCE_COMPLETE__P4_4_DELIVERY_GATE_NEXT`
