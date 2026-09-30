"""Deterministic negative tests for public capability registry validation."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_capability_registry.py"
REGISTRY_PATH = ROOT / "catalog" / "capability-registry.json"


def fail(message: str) -> None:
    raise SystemExit(f"CAPABILITY_REGISTRY_TEST_FAIL: {message}")


def load_validator():
    spec = importlib.util.spec_from_file_location("registry_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        fail("could not load capability registry validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(module, data: dict, contains: str) -> None:
    try:
        module.validate_registry(data, ROOT)
    except module.RegistryError as exc:
        if contains not in str(exc):
            fail(f"wrong rejection for {contains!r}: {exc}")
    else:
        fail(f"expected rejection containing: {contains}")


def capability(data: dict, cid: str) -> dict:
    return next(item for item in data["capabilities"] if item["capability_id"] == cid)


def main() -> None:
    validator = load_validator()
    base = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    validator.validate_registry(base, ROOT)

    bad_version = copy.deepcopy(base)
    bad_version["registry_version"] = True
    expect_rejected(validator, bad_version, "positive integer")

    extra_top = copy.deepcopy(base)
    extra_top["private_route"] = "forbidden"
    expect_rejected(validator, extra_top, "top-level keys mismatch")

    bad_id = copy.deepcopy(base)
    capability(bad_id, "verified-completion")["capability_id"] = "../escape"
    expect_rejected(validator, bad_id, "invalid capability_id")

    traversal = copy.deepcopy(base)
    capability(traversal, "verified-completion")["path"] = "../README.md"
    expect_rejected(validator, traversal, "normalized repository-relative path")

    wrong_kind = copy.deepcopy(base)
    capability(wrong_kind, "verified-completion")["kind"] = "unknown"
    expect_rejected(validator, wrong_kind, "unsupported kind")

    duplicate_path = copy.deepcopy(base)
    capability(duplicate_path, "provenance-freshness")["path"] = capability(
        duplicate_path, "verified-completion"
    )["path"]
    expect_rejected(validator, duplicate_path, "duplicate capability path")

    wrong_eval = copy.deepcopy(base)
    capability(wrong_eval, "verified-completion")["eval_path"] = "README.md"
    expect_rejected(validator, wrong_eval, "eval_path must equal")

    bad_primary = copy.deepcopy(base)
    capability(bad_primary, "silent-failure-reviewer")["primary_skill"] = "missing-skill"
    expect_rejected(validator, bad_primary, "primary_skill not registered")

    missing_skill = copy.deepcopy(base)
    missing_skill["capabilities"] = [
        item for item in missing_skill["capabilities"]
        if item["capability_id"] != "verified-completion"
    ]
    expect_rejected(validator, missing_skill, "registered skills differ from disk skills")

    print("CAPABILITY_REGISTRY_HARDENING_TEST_PASS")


if __name__ == "__main__":
    main()
