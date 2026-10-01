# DuckDB local CSV aggregate capability V1

Status: `PUBLIC_ADAPTER_AVAILABLE__CONSUMER_AUTHORITY_REQUIRED`

Capability ID: `duckdb-local-csv-aggregate`

Implementation: `scripts/query_local_csv.py`

Deterministic contract test: `scripts/test_query_local_csv_adapter.py`

Admission evidence: `catalog/p4-duckdb-local-csv-admission.json`

## Purpose

This public adapter performs one bounded aggregate over one explicitly supplied local CSV using a caller-supplied DuckDB CLI v1.4.1 binary.

It supports exactly:

- `count` with no column;
- `sum` over one simple column identifier.

## Preconditions

The consuming environment must independently authorize the exact input file read and provide the reviewed DuckDB CLI binary. Registry membership grants neither permission.

The adapter requires:

- one existing regular `.csv` file;
- no symlink input;
- exact DuckDB CLI version v1.4.1;
- no installation fallback;
- no shared session state or `-init` path.

## Runtime boundaries

The adapter invokes the CLI directly without a shell, uses `:memory:`, restricts `allowed_paths` to the resolved input file, disables external access and persistent secrets, locks configuration, bounds execution time, and caps stdout at 4096 bytes.

It does not accept arbitrary SQL, discover files or state, install extensions, use credentials, fetch remote data, or write user data.

## Authority

`AVAILABLE` means the reusable public adapter contract exists at the pinned Agent OS SHA. It does not authorize the adapter to read any particular file and does not authorize installation or use of an arbitrary DuckDB binary.

Consumers must supply file-read and local-process authority. Private project mapping remains outside the public repository.

## Vendor boundary

The official DuckDB skills package remains `REFERENCE_ONLY`. This adapter is a separately implemented, narrowed Agent OS capability derived from the audited local ad-hoc pattern; admission does not admit the broader upstream `query` skill.

## Terminal

`DUCKDB_LOCAL_CSV_AGGREGATE_PUBLIC_ADAPTER_ADMITTED_V1`
