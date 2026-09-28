# P3 vendor catalog baseline

## Goal

Establish a provenance- and authority-aware baseline for the initial public tooling sources before any broad capability admission.

## Completed source audits

| Source | Evidence boundary | Baseline disposition |
| --- | --- | --- |
| Agent Skills specification | `69ef37e9424c0a7ea9dd2293b559e43ec8176379` | `KEEP_REFERENCE_ONLY` |
| OpenAI plugin marketplace | `5fd93af4cd0c623e020d0cc7e9ce178b4ac1f70f` | `KEEP_REFERENCE_ONLY` |
| DuckDB skills | `7feda8e01e22bc0886c86123f3884947e36d8c69` | `KEEP_REFERENCE_ONLY` |
| Cloudflare skills | `626547c06881a20b3322bdc2ed6e6451b33a4fb6` | `KEEP_REFERENCE_ONLY` |
| Microsoft Playwright skills | implementation `74354ecc7a43da16d91a9bc54fa8db8283a3fcf5`; docs `1cc5be996c1785fde93e6ba075ab83e271173008` | `KEEP_REFERENCE_ONLY` |

`REFERENCE_ONLY` is not a rejection of the source. It means source-level trust is intentionally not widened into automatic execution authority.

## What P3 established

- exact upstream evidence boundaries;
- vendor/package capability audit records;
- per-subcapability risk tags and dispositions;
- update/re-review rules;
- a marketplace provenance boundary for externally referenced repositories;
- narrow future admission candidates instead of blanket plugin approval.

## Next phase: P4 tooling layer expansion

P4 converts the broad audited sources into a normalized tooling inventory and evaluates narrowly scoped capabilities.

Sequence:

1. build a machine-readable capability inventory;
2. classify each candidate by read/write/destructive/publish/credential/network/local-execution surfaces;
3. prioritize portable read-only/reference capabilities before write-capable integrations;
4. bind every candidate to exact upstream evidence;
5. admit only a narrow capability whose authority surface is explicit and whose evaluation demonstrates value;
6. keep broad packages reference-only even when one subcapability is admitted;
7. run deterministic validation, publication gate, semantic review and exact-main verification for every admission change.

P4 must not install, authenticate, deploy, publish, send, delete, purchase or mutate external state merely to inventory a capability.

## Terminal state

`P3_VENDOR_CATALOG_BASELINE_COMPLETE__P4_TOOLING_INVENTORY_NEXT`
