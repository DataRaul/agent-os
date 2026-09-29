# Bounded local CSV query adapter

Status: **EVALUATION_ONLY — NOT REGISTERED OR RUNTIME_ADMITTED**

`scripts/query_local_csv.py` is a public candidate adapter independent of the full upstream DuckDB skill. It accepts one explicit local CSV and only `count` or `sum` on a simple column identifier. It does not accept arbitrary SQL, discover prior state, install software, use credentials, or fetch remote data.

The caller supplies a trusted DuckDB CLI v1.4.1 binary explicitly; the script does not download or install it. For example:

```text
python scripts/query_local_csv.py ./sample.csv count --duckdb-cli /path/to/duckdb
python scripts/query_local_csv.py ./sample.csv sum --column value --duckdb-cli /path/to/duckdb
```

The adapter rejects symlink inputs, resolves the allowed file to an absolute path, invokes the CLI without a shell or `-init`, configures an in-memory database with external access and persistent secrets disabled, locks configuration, and caps execution time and output bytes. Its authority still comes solely from the caller's local file access; this repository supplies no permission to read any file.

Local synthetic verification with DuckDB CLI v1.4.1 returned two rows and sum 18 for an input containing 7 and 11. It rejected a symlink, unsupported operation and malformed column, and left test files unchanged. The separate [bounded evaluation](P4_DUCKDB_LOCAL_ADHOC_EVALUATION.md) records CLI boundary probes and the upstream session-state risk.

CI also runs `scripts/test_query_local_csv_adapter.py` with an inert fake CLI. That deterministic contract test verifies the direct no-shell invocation shape, explicit `:memory:` mode, absence of `-init`, exact v1.4.1 pin enforcement, allowed-path/external-access/secret/config-lock SQL boundaries, simple-column restriction, symlink rejection, input immutability, and output-size cap. The fake-CLI test does not replace the real DuckDB v1.4.1 evaluation and grants no runtime admission.

This is a narrow candidate, not a claim of general DuckDB sandboxing or vendor-skill admission. Registry promotion, private mapping, and real-project use require the applicable selection, authority and calibration gates.
