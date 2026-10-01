"""Deterministic integration tests for the P5 DuckDB local CSV execution profile."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "p5_duckdb_local_csv_router.py"
REGISTRY_PATH = ROOT / "catalog" / "capability-registry.json"
SCHEMA_PATH = ROOT / "schemas" / "p5-duckdb-local-csv-execution-receipt.schema.json"


def fail(message: str) -> None:
    raise SystemExit(f"P5_DUCKDB_LOCAL_CSV_ROUTER_TEST_FAIL: {message}")


def load_module():
    spec = importlib.util.spec_from_file_location("p5_duckdb_local_csv_router", MODULE_PATH)
    if spec is None or spec.loader is None:
        fail("could not load DuckDB router module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_fake_cli(
    path: Path,
    capture: Path,
    *,
    version: str = "v1.4.1 fake",
    output: str = "result\n2\n",
) -> None:
    script = f"""#!/usr/bin/env python3
import json
import sys
from pathlib import Path
if "--version" in sys.argv:
    print({version!r})
    raise SystemExit(0)
payload = {{"argv": sys.argv[1:], "stdin": sys.stdin.read()}}
Path({str(capture)!r}).write_text(json.dumps(payload), encoding="utf-8")
sys.stdout.write({output!r})
"""
    path.write_text(script, encoding="utf-8")
    os.chmod(path, 0o755)


def expect_error(module, fn, contains: str) -> None:
    try:
        fn()
    except module.RouterError as exc:
        if contains not in str(exc):
            fail(f"wrong error for {contains!r}: {exc}")
    else:
        fail(f"expected RouterError containing {contains!r}")


def make_request(module, pin: str) -> dict:
    return {
        "schema_version": 1,
        "public_base_sha": pin,
        "capability_id": module.SUPPORTED_CAPABILITY_ID,
        "capability_contract_version": module.SUPPORTED_CAPABILITY_VERSION,
        "work_class": "research-evidence",
        "complexity_class": "C1",
        "declared_authority_class": "read-only",
        "required_preconditions": list(module.SUPPORTED_PRECONDITIONS),
        "output_postcondition_contract": {
            "output_type": module.SUPPORTED_OUTPUT_TYPE,
            "postconditions": list(module.SUPPORTED_POSTCONDITIONS),
        },
    }


def make_checks(module) -> list[dict]:
    return [
        {
            "check_id": module.SUPPORTED_PRECONDITIONS[0],
            "status": "PASS",
            "evidence": "caller explicitly authorized this one CSV read",
        },
        {
            "check_id": module.SUPPORTED_PRECONDITIONS[1],
            "status": "PASS",
            "evidence": "caller explicitly supplied and authorized the reviewed v1.4.1 CLI",
        },
    ]


def main() -> None:
    module = load_module()
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    pin = "a" * 40
    registry_digest = module.canonical_sha256(registry)
    request = make_request(module, pin)
    checks = make_checks(module)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        csv_path = root / "sample.csv"
        csv_path.write_text("value\n7\n11\n", encoding="utf-8")
        original = csv_path.read_bytes()

        capture = root / "capture.json"
        cli = root / "duckdb"
        write_fake_cli(cli, capture)

        adapter_input = {
            "csv_file": str(csv_path),
            "operation": "count",
            "column": None,
            "duckdb_cli": str(cli),
        }

        result = module.execute_route(
            request,
            registry,
            pin,
            registry_digest,
            checks,
            module.SUPPORTED_ADAPTER_ID,
            adapter_input,
        )
        repeated = module.execute_route(
            request,
            registry,
            pin,
            registry_digest,
            checks,
            module.SUPPORTED_ADAPTER_ID,
            adapter_input,
        )

        if result != repeated:
            fail("identical bounded inputs must produce identical receipts")
        expected_keys = set(schema["properties"])
        if set(result) != expected_keys or set(schema["required"]) != expected_keys:
            fail("receipt shape does not match dedicated schema")
        for key in (
            "schema_version",
            "contract_type",
            "execution_status",
            "runtime_scope",
            "capability_id",
            "capability_contract_version",
            "adapter_id",
            "authority_source",
            "registry_authority_granted",
            "external_authority_used",
            "executable",
        ):
            rule = schema["properties"][key]
            if "const" in rule and result[key] != rule["const"]:
                fail(f"receipt constant mismatch: {key}")

        if result["output"] != {
            "adapter": module.SUPPORTED_ADAPTER_ID,
            "operation": "count",
            "column": None,
            "result": "2",
        }:
            fail("bounded aggregate output mismatch")
        if result["input_file_sha256_before"] != result["input_file_sha256_after"]:
            fail("input file digest changed")
        if csv_path.read_bytes() != original:
            fail("input CSV was mutated")
        if result["side_effects"] != []:
            fail("bounded read-only execution must report no state mutations")
        if result["precondition_result"]["status"] != "PASS":
            fail("preconditions must pass")
        if result["postcondition_result"]["status"] != "PASS":
            fail("postconditions must pass")
        if result["output_sha256"] != module.canonical_sha256(result["output"]):
            fail("output digest mismatch")
        if result["adapter_input_sha256"] != module.canonical_sha256(adapter_input):
            fail("adapter input digest mismatch")

        invocation = json.loads(capture.read_text(encoding="utf-8"))
        if invocation["argv"] != [":memory:", "-csv"]:
            fail(f"unexpected DuckDB CLI arguments: {invocation['argv']}")
        sql = invocation["stdin"]
        resolved = str(csv_path.resolve()).replace("'", "''")
        for fragment in (
            f"SET allowed_paths=['{resolved}'];",
            "SET enable_external_access=false;",
            "SET allow_persistent_secrets=false;",
            "SET lock_configuration=true;",
            "SELECT count() AS result",
        ):
            if fragment not in sql:
                fail(f"missing admitted adapter boundary: {fragment}")

        sum_capture = root / "sum-capture.json"
        sum_cli = root / "sum-duckdb"
        write_fake_cli(sum_cli, sum_capture, output="result\n18\n")
        sum_input = {
            "csv_file": str(csv_path),
            "operation": "sum",
            "column": "value",
            "duckdb_cli": str(sum_cli),
        }
        sum_result = module.execute_route(
            request,
            registry,
            pin,
            registry_digest,
            checks,
            module.SUPPORTED_ADAPTER_ID,
            sum_input,
        )
        if sum_result["output"]["result"] != "18":
            fail("sum path result mismatch")
        if 'SELECT sum("value") AS result' not in json.loads(
            sum_capture.read_text(encoding="utf-8")
        )["stdin"]:
            fail("sum path did not preserve simple-identifier constraint")

        expect_error(
            module,
            lambda: module.execute_route(
                request,
                registry,
                "f" * 40,
                registry_digest,
                checks,
                module.SUPPORTED_ADAPTER_ID,
                adapter_input,
            ),
            "binding rejected",
        )
        expect_error(
            module,
            lambda: module.execute_route(
                request,
                registry,
                pin,
                "0" * 64,
                checks,
                module.SUPPORTED_ADAPTER_ID,
                adapter_input,
            ),
            "binding rejected",
        )

        elevated = copy.deepcopy(request)
        elevated["declared_authority_class"] = "local-write"
        expect_error(
            module,
            lambda: module.execute_route(
                elevated,
                registry,
                pin,
                registry_digest,
                checks,
                module.SUPPORTED_ADAPTER_ID,
                adapter_input,
            ),
            "authority ceiling",
        )

        missing_authority = copy.deepcopy(request)
        missing_authority["required_preconditions"] = [module.SUPPORTED_PRECONDITIONS[0]]
        expect_error(
            module,
            lambda: module.execute_route(
                missing_authority,
                registry,
                pin,
                registry_digest,
                checks,
                module.SUPPORTED_ADAPTER_ID,
                adapter_input,
            ),
            "exact bounded precondition set",
        )

        failed_checks = copy.deepcopy(checks)
        failed_checks[0]["status"] = "FAIL"
        expect_error(
            module,
            lambda: module.execute_route(
                request,
                registry,
                pin,
                registry_digest,
                failed_checks,
                module.SUPPORTED_ADAPTER_ID,
                adapter_input,
            ),
            "must PASS",
        )

        wrong_contract = copy.deepcopy(request)
        wrong_contract["output_postcondition_contract"]["output_type"] = "other"
        expect_error(
            module,
            lambda: module.execute_route(
                wrong_contract,
                registry,
                pin,
                registry_digest,
                checks,
                module.SUPPORTED_ADAPTER_ID,
                adapter_input,
            ),
            "output_type unsupported",
        )

        wrong_adapter = "other-adapter"
        expect_error(
            module,
            lambda: module.execute_route(
                request,
                registry,
                pin,
                registry_digest,
                checks,
                wrong_adapter,
                adapter_input,
            ),
            "adapter ID",
        )

        arbitrary = dict(adapter_input)
        arbitrary["operation"] = "select * from secrets"
        expect_error(
            module,
            lambda: module.execute_route(
                request,
                registry,
                pin,
                registry_digest,
                checks,
                module.SUPPORTED_ADAPTER_ID,
                arbitrary,
            ),
            "unsupported operation",
        )

        bad_column = dict(sum_input)
        bad_column["column"] = 'value;DROP'
        expect_error(
            module,
            lambda: module.execute_route(
                request,
                registry,
                pin,
                registry_digest,
                checks,
                module.SUPPORTED_ADAPTER_ID,
                bad_column,
            ),
            "simple column identifier",
        )

        extra = dict(adapter_input)
        extra["sql"] = "select 1"
        expect_error(
            module,
            lambda: module.execute_route(
                request,
                registry,
                pin,
                registry_digest,
                checks,
                module.SUPPORTED_ADAPTER_ID,
                extra,
            ),
            "must contain only",
        )

        symlink = root / "linked.csv"
        symlink.symlink_to(csv_path)
        symlink_input = dict(adapter_input)
        symlink_input["csv_file"] = str(symlink)
        expect_error(
            module,
            lambda: module.execute_route(
                request,
                registry,
                pin,
                registry_digest,
                checks,
                module.SUPPORTED_ADAPTER_ID,
                symlink_input,
            ),
            "not a symlink",
        )

        wrong_cli = root / "wrong-duckdb"
        wrong_capture = root / "wrong-capture.json"
        write_fake_cli(wrong_cli, wrong_capture, version="v1.5.0 fake")
        wrong_cli_input = dict(adapter_input)
        wrong_cli_input["duckdb_cli"] = str(wrong_cli)
        expect_error(
            module,
            lambda: module.execute_route(
                request,
                registry,
                pin,
                registry_digest,
                checks,
                module.SUPPORTED_ADAPTER_ID,
                wrong_cli_input,
            ),
            "version must be v1.4.1",
        )

        authority_registry = copy.deepcopy(registry)
        for capability in authority_registry["capabilities"]:
            if capability.get("capability_id") == module.SUPPORTED_CAPABILITY_ID:
                capability["grants_authority"] = True
        expect_error(
            module,
            lambda: module.execute_route(
                request,
                authority_registry,
                pin,
                module.canonical_sha256(authority_registry),
                checks,
                module.SUPPORTED_ADAPTER_ID,
                adapter_input,
            ),
            "binding rejected",
        )

        original_query = module.local_csv_query

        def mutating_query(csv_file, operation, column, duckdb_cli):
            csv_file.write_text("value\n999\n", encoding="utf-8")
            return "result\n1\n"

        module.local_csv_query = mutating_query
        try:
            expect_error(
                module,
                lambda: module.execute_route(
                    request,
                    registry,
                    pin,
                    registry_digest,
                    checks,
                    module.SUPPORTED_ADAPTER_ID,
                    adapter_input,
                ),
                "changed during bounded read-only execution",
            )
        finally:
            module.local_csv_query = original_query

    print("P5_DUCKDB_LOCAL_CSV_ROUTER_TEST_PASS")


if __name__ == "__main__":
    main()
