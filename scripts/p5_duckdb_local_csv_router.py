"""Bounded P5 execution profile for the admitted DuckDB local CSV aggregate adapter.

This module connects the public P5 binding/precondition/postcondition contracts to the
already-admitted `duckdb-local-csv-aggregate` adapter. It does not select capabilities,
grant file/process authority, install software, discover files, accept arbitrary SQL,
use credentials, access the network, or write user data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path

from capability_decision_contracts import canonical_sha256, check_result, declared_binding_decision
from query_local_csv import query as local_csv_query

MAX_ADAPTER_INPUT_BYTES = 4096
SUPPORTED_CAPABILITY_ID = "duckdb-local-csv-aggregate"
SUPPORTED_CAPABILITY_VERSION = 1
SUPPORTED_ADAPTER_ID = "duckdb-local-csv-aggregate-v1"
SUPPORTED_OUTPUT_TYPE = "duckdb-local-csv-aggregate-result"
SUPPORTED_PRECONDITIONS = [
    "input CSV read explicitly authorized",
    "reviewed DuckDB CLI v1.4.1 process explicitly authorized",
]
SUPPORTED_POSTCONDITIONS = [
    "bounded aggregate completed",
    "input CSV remained unchanged",
]


class RouterError(ValueError):
    pass


def _canonical_bytes(value: object) -> bytes:
    try:
        payload = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise RouterError(f"adapter input must be canonical JSON: {exc}") from exc
    return payload.encode("utf-8")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise RouterError(f"could not hash authorized input CSV: {exc}") from exc
    return digest.hexdigest()


def _validate_precondition_coverage(request: dict, checks: object) -> None:
    required = request.get("required_preconditions")
    if required != SUPPORTED_PRECONDITIONS:
        raise RouterError("DuckDB execution requires the exact bounded precondition set")
    if not isinstance(checks, list):
        raise RouterError("precondition checks must be an array")
    check_ids = [item.get("check_id") for item in checks if isinstance(item, dict)]
    if len(check_ids) != len(checks) or check_ids != SUPPORTED_PRECONDITIONS:
        raise RouterError("precondition checks must exactly cover the bounded preconditions")


def _validate_output_contract(request: dict) -> None:
    contract = request.get("output_postcondition_contract")
    if not isinstance(contract, dict):
        raise RouterError("output postcondition contract missing")
    if contract.get("output_type") != SUPPORTED_OUTPUT_TYPE:
        raise RouterError("DuckDB router output_type unsupported")
    if contract.get("postconditions") != SUPPORTED_POSTCONDITIONS:
        raise RouterError("DuckDB router postconditions unsupported")


def _validate_adapter_input(adapter_input: object) -> tuple[Path, str, str | None, Path]:
    if not isinstance(adapter_input, dict):
        raise RouterError("adapter input must be an object")
    required = {"csv_file", "operation", "column", "duckdb_cli"}
    if set(adapter_input) != required:
        raise RouterError("adapter input must contain only csv_file, operation, column, duckdb_cli")
    if len(_canonical_bytes(adapter_input)) > MAX_ADAPTER_INPUT_BYTES:
        raise RouterError("adapter input exceeds size bound")

    csv_file = adapter_input["csv_file"]
    operation = adapter_input["operation"]
    column = adapter_input["column"]
    duckdb_cli = adapter_input["duckdb_cli"]

    if not isinstance(csv_file, str) or not csv_file:
        raise RouterError("csv_file must be a non-empty path string")
    if not isinstance(duckdb_cli, str) or not duckdb_cli:
        raise RouterError("duckdb_cli must be a non-empty path string")
    if operation not in {"count", "sum"}:
        raise RouterError("unsupported operation")
    if operation == "count" and column is not None:
        raise RouterError("count does not accept a column")
    if operation == "sum" and (not isinstance(column, str) or not column):
        raise RouterError("sum requires a column")
    if column is not None and not isinstance(column, str):
        raise RouterError("column must be a string or null")

    return Path(csv_file), operation, column, Path(duckdb_cli)


def _parse_single_result(stdout: str) -> str:
    try:
        rows = list(csv.reader(io.StringIO(stdout)))
    except csv.Error as exc:
        raise RouterError(f"adapter output is not valid CSV: {exc}") from exc
    if len(rows) != 2 or rows[0] != ["result"] or len(rows[1]) != 1:
        raise RouterError("adapter output must be exactly one result column and one data row")
    return rows[1][0]


def execute_route(
    request: object,
    registry: object,
    expected_public_base_sha: str,
    expected_registry_sha256: str,
    precondition_checks: object,
    adapter_id: str,
    adapter_input: object,
) -> dict:
    if not isinstance(request, dict):
        raise RouterError("selection request must be an object")

    decision = declared_binding_decision(
        request,
        registry,
        expected_public_base_sha,
        expected_registry_sha256,
    )
    if decision.get("disposition") != "BOUND":
        reasons = ",".join(decision.get("reason_codes") or [])
        raise RouterError(f"declared capability binding rejected: {reasons or 'UNKNOWN'}")

    if request.get("declared_authority_class") != "read-only":
        raise RouterError("DuckDB execution authority ceiling is read-only")
    if request.get("capability_id") != SUPPORTED_CAPABILITY_ID:
        raise RouterError("router supports only duckdb-local-csv-aggregate")
    if request.get("capability_contract_version") != SUPPORTED_CAPABILITY_VERSION:
        raise RouterError("DuckDB capability version unsupported")
    if adapter_id != SUPPORTED_ADAPTER_ID:
        raise RouterError("adapter ID does not match the bounded DuckDB adapter")

    _validate_precondition_coverage(request, precondition_checks)
    preconditions = check_result(
        "PRECONDITION_VALIDATION_RESULT",
        decision["public_base_sha"],
        decision["registry_sha256"],
        decision["capability_id"],
        decision["capability_contract_version"],
        precondition_checks,
    )
    if preconditions["status"] != "PASS":
        raise RouterError("all declared preconditions must PASS before execution")

    _validate_output_contract(request)
    csv_file, operation, column, duckdb_cli = _validate_adapter_input(adapter_input)
    input_sha256 = canonical_sha256(adapter_input)
    file_sha256_before = _file_sha256(csv_file)

    try:
        stdout = local_csv_query(csv_file, operation, column, duckdb_cli)
    except (ValueError, RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
        raise RouterError(f"bounded DuckDB adapter failed: {exc}") from exc

    result_value = _parse_single_result(stdout)
    file_sha256_after = _file_sha256(csv_file)
    if file_sha256_after != file_sha256_before:
        raise RouterError("input CSV changed during bounded read-only execution")

    output = {
        "adapter": SUPPORTED_ADAPTER_ID,
        "operation": operation,
        "column": column,
        "result": result_value,
    }
    output_sha256 = canonical_sha256(output)
    postconditions = check_result(
        "POSTCONDITION_VERIFICATION_RESULT",
        decision["public_base_sha"],
        decision["registry_sha256"],
        decision["capability_id"],
        decision["capability_contract_version"],
        [
            {
                "check_id": SUPPORTED_POSTCONDITIONS[0],
                "status": "PASS",
                "evidence": "admitted adapter returned exactly one bounded aggregate result",
            },
            {
                "check_id": SUPPORTED_POSTCONDITIONS[1],
                "status": "PASS",
                "evidence": "SHA-256 of the authorized CSV matched before and after execution",
            },
        ],
        output_sha256,
    )

    return {
        "schema_version": 1,
        "contract_type": "P5_DUCKDB_LOCAL_CSV_EXECUTION_RECEIPT",
        "execution_status": "EXECUTED",
        "runtime_scope": "BOUND_REAL_DUCKDB_LOCAL_CSV_ADAPTER",
        "public_base_sha": decision["public_base_sha"],
        "registry_sha256": decision["registry_sha256"],
        "request_sha256": decision["request_sha256"],
        "capability_id": decision["capability_id"],
        "capability_contract_version": decision["capability_contract_version"],
        "adapter_id": adapter_id,
        "adapter_input_sha256": input_sha256,
        "input_file_sha256_before": file_sha256_before,
        "input_file_sha256_after": file_sha256_after,
        "output_sha256": output_sha256,
        "output": output,
        "precondition_result": preconditions,
        "postcondition_result": postconditions,
        "authority_source": "CALLER_EXPLICIT_LOCAL_READ_AND_PROCESS_AUTHORITY",
        "registry_authority_granted": False,
        "external_authority_used": True,
        "side_effects": [],
        "executable": True,
    }


def _load_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RouterError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RouterError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RouterError(f"{path} must contain a JSON object")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--expected-public-base-sha", required=True)
    parser.add_argument("--expected-registry-sha256", required=True)
    args = parser.parse_args()

    try:
        bundle = _load_object(args.bundle)
        registry = _load_object(args.registry)
        result = execute_route(
            bundle["request"],
            registry,
            args.expected_public_base_sha,
            args.expected_registry_sha256,
            bundle["precondition_checks"],
            bundle["adapter_id"],
            bundle["adapter_input"],
        )
    except (RouterError, KeyError, ValueError) as exc:
        raise SystemExit(f"P5_DUCKDB_LOCAL_CSV_ROUTER_FAIL: {exc}") from None

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
