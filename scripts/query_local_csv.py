"""Bounded public DuckDB CLI adapter for a single explicitly authorized local CSV."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

EXPECTED_VERSION = "v1.4.1"
COLUMN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def query(csv_path: Path, operation: str, column: str | None, cli: Path) -> str:
    if csv_path.is_symlink() or not csv_path.is_file() or csv_path.suffix.lower() != ".csv":
        raise ValueError("input must be an existing, regular CSV file, not a symlink")
    if operation == "sum" and (column is None or not COLUMN.fullmatch(column)):
        raise ValueError("sum requires a simple column identifier")
    if operation == "count" and column is not None:
        raise ValueError("count does not accept a column")
    if operation not in {"count", "sum"}:
        raise ValueError("unsupported operation")

    cli = cli.resolve(strict=True)
    version = subprocess.run([str(cli), "--version"], capture_output=True, text=True, timeout=5)
    if version.returncode or not version.stdout.startswith(EXPECTED_VERSION + " "):
        raise ValueError("DuckDB CLI version must be v1.4.1")

    # The path is supplied as a SQL literal, never interpolated into a shell command.
    path = str(csv_path.resolve()).replace("'", "''")
    expression = "count()" if operation == "count" else f'sum("{column}")'
    sql = (
        f"SET allowed_paths=['{path}'];\n"
        "SET enable_external_access=false;\n"
        "SET allow_persistent_secrets=false;\n"
        "SET lock_configuration=true;\n"
        f"SELECT {expression} AS result FROM '{path}';\n"
    )
    # Explicit :memory: and no -init prevent the upstream skill's state-file path.
    result = subprocess.run(
        [str(cli), ":memory:", "-csv"], input=sql, capture_output=True,
        text=True, timeout=15, cwd=csv_path.parent,
    )
    if result.returncode:
        raise RuntimeError("DuckDB query failed")
    if len(result.stdout.encode("utf-8")) > 4096:
        raise RuntimeError("query output exceeds bound")
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("operation", choices=("count", "sum"))
    parser.add_argument("--column")
    parser.add_argument("--duckdb-cli", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(query(args.csv_file, args.operation, args.column, args.duckdb_cli), end="")
    except (ValueError, RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
        raise SystemExit(f"LOCAL_CSV_QUERY_FAIL: {exc}") from None


if __name__ == "__main__":
    main()
