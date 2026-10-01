"""Deterministic mutation tests for the first stable release-candidate guardrails."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_release_candidate.py"
CANDIDATE_PATH = ROOT / "catalog" / "release-candidate.json"
REGISTRY_PATH = ROOT / "catalog" / "capability-registry.json"


def fail(message: str) -> None:
    raise SystemExit(f"RELEASE_CANDIDATE_TEST_FAIL: {message}")


def load_module():
    spec = importlib.util.spec_from_file_location("validate_release_candidate", MODULE_PATH)
    if spec is None or spec.loader is None:
        fail("could not load release-candidate validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_error(module, candidate, registry, contains: str, *, root: Path = ROOT, version: str = "1.0.0-rc.1") -> None:
    try:
        module.validate_candidate(candidate, registry, root, version)
    except module.CandidateError as exc:
        if contains not in str(exc):
            fail(f"wrong failure for {contains!r}: {exc}")
    else:
        fail(f"expected CandidateError containing {contains!r}")


def main() -> None:
    module = load_module()
    candidate = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    module.validate_candidate(candidate, registry, ROOT, "1.0.0-rc.1")

    wrong_digest = copy.deepcopy(candidate)
    wrong_digest["registry_sha256"] = "0" * 64
    expect_error(module, wrong_digest, registry, "registry digest mismatch")

    wrong_version = copy.deepcopy(candidate)
    wrong_version["candidate_version"] = "1.0.0"
    expect_error(module, wrong_version, registry, "candidate version")

    bad_sha = copy.deepcopy(candidate)
    bad_sha["baseline_main_sha"] = "main"
    expect_error(module, bad_sha, registry, "baseline main SHA")

    missing_cap = copy.deepcopy(candidate)
    missing_cap["stable_capability_contracts"] = missing_cap["stable_capability_contracts"][:-1]
    expect_error(module, missing_cap, registry, "do not match AVAILABLE")

    published = copy.deepcopy(candidate)
    published["publication"]["tag_created"] = True
    expect_error(module, published, registry, "publication boundary")

    widened_authority = copy.deepcopy(candidate)
    widened_authority["stability_guarantees"]["registry_membership_grants_authority"] = True
    expect_error(module, widened_authority, registry, "must never grant authority")

    weakened_pin = copy.deepcopy(candidate)
    weakened_pin["stability_guarantees"]["exact_repository_sha_pin_required"] = False
    expect_error(module, weakened_pin, registry, "must be true")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        missing_path = copy.deepcopy(candidate)
        expect_error(module, missing_path, registry, "stable interface path missing", root=root)

    expect_error(module, candidate, registry, "VERSION does not match", version="1.0.0")

    print("RELEASE_CANDIDATE_TEST_PASS")


if __name__ == "__main__":
    main()
