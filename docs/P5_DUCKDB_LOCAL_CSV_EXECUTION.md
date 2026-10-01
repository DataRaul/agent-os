# P5 DuckDB local CSV execution profile V1

Status: `BOUND_REAL_ADAPTER_EXECUTION_PROFILE_V1_COMPLETE`

Capability: `duckdb-local-csv-aggregate`

Router: `scripts/p5_duckdb_local_csv_router.py`

Receipt schema: `schemas/p5-duckdb-local-csv-execution-receipt.schema.json`

Execution contract: `benchmarks/p5-duckdb-local-csv-router/adapter-contract.json`

Deterministic integration test: `scripts/test_p5_duckdb_local_csv_router.py`

## Purpose

This profile connects the P5 exact-pin, registry-digest, precondition and postcondition contracts to one already-admitted public adapter: `duckdb-local-csv-aggregate`.

It is not a generic dynamic adapter loader. The capability and adapter identifiers are hard-coded and fail closed.

## Required authority

Registry membership grants no authority. Before execution, the caller must explicitly provide passing evidence for exactly:

1. `input CSV read explicitly authorized`;
2. `reviewed DuckDB CLI v1.4.1 process explicitly authorized`.

The request authority class must be `read-only`.

The profile does not decide whether a particular file, process, project or environment is authorized. It only validates the caller-supplied declaration and evidence against the bounded execution contract.

## Input boundary

The adapter input contains exactly:

- `csv_file`: one explicit existing regular local `.csv` file, not a symlink;
- `operation`: `count` or `sum`;
- `column`: null for `count`, one simple identifier for `sum`;
- `duckdb_cli`: one caller-supplied executable that the admitted adapter verifies as v1.4.1.

Canonical adapter input is capped at 4096 bytes.

No arbitrary SQL field exists.

## Runtime boundary

Execution delegates to the admitted `scripts/query_local_csv.py` adapter. That adapter:

- invokes the CLI directly without a shell;
- uses an in-memory DuckDB database;
- restricts `allowed_paths` to the explicit CSV;
- disables external access;
- disables persistent secrets;
- locks configuration;
- uses no init file or session restore;
- has bounded version-probe and query timeouts;
- caps stdout at 4096 bytes.

This P5 profile additionally hashes the authorized CSV before and after execution and fails if the file changed.

## Receipt

A successful receipt records:

- the exact declared public-base SHA and registry digest;
- request, adapter-input and output digests;
- input-file SHA-256 before and after execution;
- the bounded aggregate result;
- passing precondition and postcondition results;
- `registry_authority_granted: false`;
- `authority_source: CALLER_EXPLICIT_LOCAL_READ_AND_PROCESS_AUTHORITY`;
- `external_authority_used: true`;
- an empty `side_effects` array.

`external_authority_used: true` means the execution depends on caller-authorized local file-read and process-execution authority. It does not mean Agent OS or the registry granted that authority.

## Evidence boundary

The deterministic integration test uses a fake local CLI to exercise the real admitted adapter implementation without requiring DuckDB installation in CI. It verifies the subprocess argument shape and generated bounded SQL. The adapter's earlier admission evidence contains the separate real DuckDB CLI boundary evaluation.

This tranche does not create project mappings, activate any consumer route, install DuckDB, use credentials, access the network, write user data or widen the capability registry.

Any additional real adapter remains separately gated.

## Terminal

`P5_DUCKDB_LOCAL_CSV_REAL_ADAPTER_PROFILE_COMPLETE__NO_CONSUMER_AUTHORITY_WIDENING`
