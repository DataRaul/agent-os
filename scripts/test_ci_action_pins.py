"""Deterministic tests for immutable workflow dependency validation."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_ci_action_pins.py"
PIN = "3d3c42e5aac5ba805825da76410c181273ba90b1"


def fail(message: str) -> None:
    raise SystemExit(f"CI_ACTION_PIN_TEST_FAIL: {message}")


def load_module():
    spec = importlib.util.spec_from_file_location("validate_ci_action_pins", MODULE_PATH)
    if spec is None or spec.loader is None:
        fail("could not load action-pin validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_error(module, root: Path, contains: str) -> None:
    try:
        module.validate_workflows(root)
    except module.PinValidationError as exc:
        if contains not in str(exc):
            fail(f"wrong rejection for {contains!r}: {exc}")
    else:
        fail(f"expected rejection containing: {contains}")


def write_workflow(root: Path, text: str) -> None:
    workflow = root / ".github" / "workflows" / "test.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(text, encoding="utf-8")


def main() -> None:
    module = load_module()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_workflow(
            root,
            "jobs:\n"
            "  test:\n"
            "    steps:\n"
            f"      - uses: actions/checkout@{PIN} # reviewed\n"
            "      - uses: './local-action'\n"
            f"  reusable:\n    uses: owner/repo/.github/workflows/reuse.yml@{PIN}\n",
        )
        module.validate_workflows(root)

    for value in (
        "actions/checkout@v7",
        "actions/checkout@3d3c42e",
        '"actions/checkout@v7"',
        "owner/repo/.github/workflows/reuse.yml@main",
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_workflow(root, f"jobs:\n  test:\n    uses: {value}\n")
            expect_error(module, root, "exact 40-character lowercase commit SHA")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_workflow(root, "jobs:\n  test:\n    steps:\n      - uses: ./local-action\n")
        module.validate_workflows(root)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_workflow(root, "jobs:\n  test:\n    steps:\n      - uses: docker://alpine:latest\n")
        expect_error(module, root, "docker action references are outside")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_workflow(root, "jobs:\n  test:\n    uses: 'actions/checkout@v7\n")
        expect_error(module, root, "quoted uses value is unterminated")

    print("CI_ACTION_PIN_TEST_PASS")


if __name__ == "__main__":
    main()
