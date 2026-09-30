"""Deterministic tests for P5 pinned registry binding verification."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "scripts" / "verify_capability_selection_binding.py"
REGISTRY_PATH = ROOT / "catalog" / "capability-registry.json"
PIN = "a" * 40


def fail(message: str) -> None:
    raise SystemExit(f"CAPABILITY_BINDING_TEST_FAIL: {message}")


def load_verifier():
    spec = importlib.util.spec_from_file_location("binding_verifier", VERIFIER_PATH)
    if spec is None or spec.loader is None:
        fail("could not load binding verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def request() -> dict:
    return {
        "schema_version": 1,
        "public_base_sha": PIN,
        "capability_id": "verified-completion",
        "capability_contract_version": 1,
        "work_class": "code-change",
        "complexity_class": "C1",
        "declared_authority_class": "read-only",
        "required_preconditions": ["authoritative state identified"],
        "output_postcondition_contract": {
            "output_type": "verification record",
            "postconditions": ["claimed state checked against authority"],
        },
    }


def expect_failure(verifier, req, registry, pin, contains: str) -> None:
    try:
        verifier.verify_binding(req, registry, pin)
    except verifier.BindingError as exc:
        if contains not in str(exc):
            fail(f"wrong failure: {exc}")
    else:
        fail(f"expected failure containing: {contains}")


def main() -> None:
    verifier = load_verifier()
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    digest = verifier.canonical_sha256(registry)
    result = verifier.verify_binding(request(), registry, PIN, digest)
    if result["binding"] != "CAPABILITY_BINDING_VERIFIED":
        fail("valid binding did not verify")
    if result["authority_granted"] is not False:
        fail("binding verification must never grant authority")
    if result["registry_sha256"] != digest:
        fail("binding result did not preserve exact registry digest")

    expect_failure(verifier, request(), registry, "b" * 40, "does not match")

    try:
        verifier.verify_binding(request(), registry, PIN, "0" * 64)
    except verifier.BindingError as exc:
        if "registry SHA-256" not in str(exc):
            fail(f"wrong registry digest failure: {exc}")
    else:
        fail("wrong registry digest was accepted")

    bad_registry_version = copy.deepcopy(registry)
    bad_registry_version["registry_version"] = True
    expect_failure(
        verifier,
        request(),
        bad_registry_version,
        PIN,
        "positive integer",
    )

    bad_registry_status = copy.deepcopy(registry)
    bad_registry_status["status"] = "UNEXPECTED"
    expect_failure(
        verifier,
        request(),
        bad_registry_status,
        PIN,
        "status mismatch",
    )

    unknown = request()
    unknown["capability_id"] = "unknown-capability"
    expect_failure(verifier, unknown, registry, PIN, "exactly one")

    wrong_version = request()
    wrong_version["capability_contract_version"] = 999
    expect_failure(verifier, wrong_version, registry, PIN, "version mismatch")

    unavailable_registry = copy.deepcopy(registry)
    for item in unavailable_registry["capabilities"]:
        if item["capability_id"] == "verified-completion":
            item["state"] = "DEPRECATED"
    expect_failure(verifier, request(), unavailable_registry, PIN, "not AVAILABLE")

    authority_registry = copy.deepcopy(registry)
    for item in authority_registry["capabilities"]:
        if item["capability_id"] == "verified-completion":
            item["grants_authority"] = True
    expect_failure(verifier, request(), authority_registry, PIN, "grant no authority")

    duplicate_registry = copy.deepcopy(registry)
    duplicate_registry["capabilities"].append(
        copy.deepcopy(
            next(
                item
                for item in duplicate_registry["capabilities"]
                if item["capability_id"] == "verified-completion"
            )
        )
    )
    expect_failure(verifier, request(), duplicate_registry, PIN, "exactly one")

    malformed = request()
    malformed["project_route"] = "not-allowed"
    expect_failure(verifier, malformed, registry, PIN, "structural contract")

    print("P5_CAPABILITY_BINDING_VERIFIER_PASS")


if __name__ == "__main__":
    main()
