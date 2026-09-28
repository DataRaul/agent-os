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

Build a small candidate queue using explicit filters rather than subjective ranking. Prefer candidates that can be evaluated without credentials or external writes:

1. specification/reference-only helpers;
2. local deterministic analysis/validation;
3. isolated read-only observation;
4. authenticated remote read;
5. write-capable integrations;
6. destructive, publish/deploy, communication-send, financial or broad-administration surfaces.

Later groups are not rejected; they simply require stronger authority and evaluation evidence.

### P4.2 — narrow audits

For a selected candidate:

- bind exact upstream commit/path/version;
- inspect instructions, scripts and tool definitions;
- enumerate positive and negative side effects;
- define required authority;
- create public-safe eval cases;
- decide `REFERENCE_ONLY`, `SKILL_ALLOWED`, `PLUGIN_ALLOWED`, `PIN_REQUIRED`, or `REJECTED`.

### P4.3 — admission evidence

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

## Update rule

`catalog/tooling-inventory.json` is a dated evidence snapshot, not a live auto-update channel.

Upstream changes require a new bounded inventory candidate. Do not silently refresh or inherit admission across changed commits.

## Terminal for this step

`P4_TOOLING_INVENTORY_V1_READY__P4_1_PRIORITIZATION_NEXT`
