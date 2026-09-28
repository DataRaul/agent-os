# Vendor capability admission

## Goal

Evaluate external skills, plugins, and tool bundles without treating official provenance or technical availability as execution authority.

Vendor admission is capability-specific and evidence-bound. A source can be trustworthy enough to reference while still being too broad to execute automatically.

## Required audit record

Each vendor capability considered beyond catalog discovery must have a public audit record in `catalog/vendor-audits/<source-id>.json`.

The record must identify:

1. source ID matching `catalog/trusted-sources.json`;
2. official upstream owner and repository;
3. exact reviewed commit and version when available;
4. verified date and license;
5. repository shape, including executable scripts/hooks;
6. declared tools and local filesystem access;
7. network access and remote endpoints/classes;
8. credential handling;
9. external side effects;
10. update/pinning strategy;
11. narrower capability alternatives;
12. per-subcapability risk/disposition;
13. final audit disposition.

## Evidence rule

Audit the exact upstream candidate.

A repository-level label such as "official" does not prove that every contained skill has the same risk profile. Review the actual instructions/scripts that can execute, especially:

- shell or code execution;
- installers/updaters;
- package or extension installation;
- credential-chain use;
- remote storage/network access;
- local state or output writes;
- session/history access;
- destructive or publish/deploy actions.

## Admission states

The canonical catalog states remain:

- `REFERENCE_ONLY`
- `SKILL_ALLOWED`
- `PLUGIN_ALLOWED`
- `PIN_REQUIRED`
- `REJECTED`

An audit may conclude `KEEP_REFERENCE_ONLY` without changing the catalog admission state.

Use `SKILL_ALLOWED` only when the reviewed instructions can operate with a sufficiently bounded tool surface and side effects. Use `PLUGIN_ALLOWED` only when the plugin-level tool surface and update behavior are reviewed as a unit.

If safe use requires freezing a specific version or commit, use `PIN_REQUIRED` and record the reviewed identity.

## Narrowing rule

Prefer admitting a narrow subcapability over an entire plugin when:

- only some skills need network access;
- only some skills handle credentials;
- installers/updaters have broader authority than read/query skills;
- session/history readers cross a privacy boundary;
- file writers or remote mutations are not needed for the intended use.

Do not copy vendor instructions into Agent OS merely to avoid upstream review. Reference the reviewed upstream identity and keep local policy separate.

## Update rule

Any upstream change after the reviewed commit is a new candidate if it changes:

- scripts/hooks;
- requested tools;
- permissions;
- credential behavior;
- network endpoints/classes;
- external side effects;
- material instructions.

Do not silently inherit admission from an older audit.

## Delivery gate

A vendor-audit change must pass:

- deterministic Agent OS validation;
- publication safety gate;
- semantic review;
- exact post-merge default-branch verification.

## Current program

Completed bounded package/surface audits:

- DuckDB official `duckdb-skills`: `KEEP_REFERENCE_ONLY`.
- Cloudflare official `cloudflare/skills`: `KEEP_REFERENCE_ONLY`.
- Microsoft Playwright CLI skills and installation guidance: `KEEP_REFERENCE_ONLY`.

Next catalog candidates remain reference-only until separately audited. Package-level audit outcomes do not automatically decide narrower subcapability admission.
