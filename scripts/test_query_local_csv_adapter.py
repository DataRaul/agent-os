"""Deterministic contract tests for the bounded public local CSV DuckDB adapter."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATH = ROOT / "scripts" / "query_local_csv.py"


def fail(message: str) -> None:
    raise SystemExit(f"LOCAL_CSV_ADAPTER_TEST_FAIL: {message}")


def load_adapter():
    spec = importlib.util.spec_from_file_location("query_local_csv", ADAPTER_PATH)
    if spec is None or spec.loader is None:
        fail("could not load adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_fake_cli(path: Path, capture: Path, *, version: str = "v1.4.1 fake", output: str = "result\n2\n") -> None:
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


def expect_value_error(fn, contains: str) -> None:
    try:
        fn()
    except ValueError as exc:
        if contains not in str(exc):
            fail(f"wrong ValueError: {exc}")
    else:
        fail(f"expected ValueError containing: {contains}")


def main() -> None:
    adapter = load_adapter()
    source = ADAPTER_PATH.read_text(encoding="utf-8")
    if "shell=True" in source:
        fail("adapter must not invoke a shell")
    if '"-init"' in source or "'-init'" in source:
        fail("adapter must not use DuckDB -init")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        csv_path = root / "sample.csv"
        csv_path.write_text("value\n7\n11\n", encoding="utf-8")
        original = csv_path.read_bytes()

        capture = root / "capture.json"
        cli = root / "duckdb"
        write_fake_cli(cli, capture)

        result = adapter.query(csv_path, "count", None, cli)
        if result != "result\n2\n":
            fail("unexpected adapter output")

        invocation = json.loads(capture.read_text(encoding="utf-8"))
        if invocation["argv"] != [":memory:", "-csv"]:
            fail(f"unexpected CLI arguments: {invocation['argv']}")
        sql = invocation["stdin"]
        resolved = str(csv_path.resolve()).replace("'", "''")
        required = [
            f"SET allowed_paths=['{resolved}'];",
            "SET enable_external_access=false;",
            "SET allow_persistent_secrets=false;",
            "SET lock_configuration=true;",
            "SELECT count() AS result",
        ]
        for fragment in required:
            if fragment not in sql:
                fail(f"missing SQL boundary: {fragment}")
        if csv_path.read_bytes() != original:
            fail("adapter mutated input CSV")

        sum_result = adapter.query(csv_path, "sum", "value", cli)
        if sum_result != "result\n2\n":
            fail("sum path did not execute")
        sum_sql = json.loads(capture.read_text(encoding="utf-8"))["stdin"]
        if 'SELECT sum("value") AS result' not in sum_sql:
            fail("sum query not constrained to requested simple identifier")

        expect_value_error(
            lambda: adapter.query(csv_path, "sum", 'value;DROP', cli),
            "simple column identifier",
        )
        expect_value_error(
            lambda: adapter.query(csv_path, "count", "value", cli),
            "does not accept a column",
        )

        symlink = root / "linked.csv"
        symlink.symlink_to(csv_path)
        expect_value_error(
            lambda: adapter.query(symlink, "count", None, cli),
            "not a symlink",
        )

        wrong_cli = root / "wrong-duckdb"
        wrong_capture = root / "wrong-capture.json"
        write_fake_cli(wrong_cli, wrong_capture, version="v1.5.0 fake")
        expect_value_error(
            lambda: adapter.query(csv_path, "count", None, wrong_cli),
            "version must be v1.4.1",
        )

        huge_cli = root / "huge-duckdb"
        huge_capture = root / "huge-capture.json"
        write_fake_cli(huge_cli, huge_capture, output="x" * 5000)
        try:
            adapter.query(csv_path, "count", None, huge_cli)
        except RuntimeError as exc:
            if "output exceeds bound" not in str(exc):
                fail(f"wrong output-bound failure: {exc}")
        else:
            fail("oversized output was not rejected")

    print("P4_DUCKDB_LOCAL_ADAPTER_CONTRACT_PASS")


if __name__ == "__main__":
    main()
