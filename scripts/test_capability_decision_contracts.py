"""Deterministic tests for P5 declarative decision/evidence contracts."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "capability_decision_contracts.py"
REGISTRY_PATH = ROOT / "catalog" / "capability-registry.json"
FIXTURES_PATH = ROOT / "benchmarks" / "capability-decision-contract" / "fixtures.json"
SCHEMA_PATH = ROOT / "schemas" / "capability-decision-contracts.schema.json"


def fail(message: str) -> None:
    raise SystemExit(f"P5_DECLARATIVE_DECISION_CONTRACT_TEST_FAIL: {message}")


def load_module():
    spec = importlib.util.spec_from_file_location("capability_decision_contracts", MODULE_PATH)
    if spec is None or spec.loader is None:
        fail("could not load decision-contract module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_error(module, fn, contains: str) -> None:
    try:
        fn()
    except module.DecisionContractError as exc:
        if contains not in str(exc):
            fail(f"wrong failure for {contains!r}: {exc}")
    else:
        fail(f"expected failure containing: {contains}")


def main() -> None:
    module = load_module()
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    fixtures = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    allowed_reasons = set(schema["$defs"]["reasonCode"]["enum"])
    if allowed_reasons != module.REASON_CODES:
        fail("reason-code schema and implementation differ")

    request = fixtures["binding_request"]
    pin = fixtures["public_base_sha"]
    registry_digest = module.canonical_sha256(registry)

    bound = module.declared_binding_decision(request, registry, pin, registry_digest)
    if bound["disposition"] != "BOUND" or bound["reason_codes"]:
        fail("valid declared binding did not bind")
    if bound["authority_granted"] is not False or bound["executable"] is not False:
        fail("binding decision must never authorize or execute")

    stale = module.declared_binding_decision(request, registry, "f" * 40, registry_digest)
    if stale["reason_codes"] != ["STALE_PIN"] or stale["disposition"] != "REJECTED":
        fail("stale pin disposition mismatch")

    wrong_digest = module.declared_binding_decision(request, registry, pin, "0" * 64)
    if wrong_digest["reason_codes"] != ["REGISTRY_DIGEST_MISMATCH"]:
        fail("registry digest mismatch not detected")

    unknown = copy.deepcopy(request)
    unknown["capability_id"] = "unknown-capability"
    no_match = module.declared_binding_decision(unknown, registry, pin, registry_digest)
    if no_match["disposition"] != "NO_MATCH" or no_match["reason_codes"] != ["NO_MATCH"]:
        fail("no-match disposition mismatch")

    duplicate_registry = copy.deepcopy(registry)
    duplicate_registry["capabilities"].append(
        copy.deepcopy(
            next(
                cap
                for cap in duplicate_registry["capabilities"]
                if cap["capability_id"] == request["capability_id"]
            )
        )
    )
    duplicate_digest = module.canonical_sha256(duplicate_registry)
    ambiguous = module.declared_binding_decision(
        request, duplicate_registry, pin, duplicate_digest
    )
    if ambiguous["disposition"] != "AMBIGUOUS_MATCH":
        fail("ambiguous declared binding not detected")

    deprecated_registry = copy.deepcopy(registry)
    for cap in deprecated_registry["capabilities"]:
        if cap["capability_id"] == request["capability_id"]:
            cap["state"] = "DEPRECATED"
    deprecated = module.declared_binding_decision(
        request,
        deprecated_registry,
        pin,
        module.canonical_sha256(deprecated_registry),
    )
    if deprecated["reason_codes"] != ["CAPABILITY_NOT_AVAILABLE"]:
        fail("unavailable capability not rejected")

    wrong_version = copy.deepcopy(request)
    wrong_version["capability_contract_version"] = 999
    version_result = module.declared_binding_decision(
        wrong_version, registry, pin, registry_digest
    )
    if version_result["reason_codes"] != ["CONTRACT_VERSION_MISMATCH"]:
        fail("contract-version mismatch not detected")

    authority_registry = copy.deepcopy(registry)
    for cap in authority_registry["capabilities"]:
        if cap["capability_id"] == request["capability_id"]:
            cap["grants_authority"] = True
    authority_result = module.declared_binding_decision(
        request,
        authority_registry,
        pin,
        module.canonical_sha256(authority_registry),
    )
    if authority_result["reason_codes"] != ["REGISTRY_AUTHORITY_VIOLATION"]:
        fail("registry authority violation not detected")

    malformed = copy.deepcopy(request)
    malformed["private_route"] = "forbidden"
    malformed_result = module.declared_binding_decision(
        malformed, registry, pin, registry_digest
    )
    if malformed_result["reason_codes"] != ["MALFORMED_REQUEST"]:
        fail("malformed request not rejected")

    precondition = module.check_result(
        "PRECONDITION_VALIDATION_RESULT",
        pin,
        fixtures["registry_sha256"],
        "verified-completion",
        1,
        fixtures["precondition_checks"],
    )
    if precondition["status"] != "PASS" or precondition["reason_codes"]:
        fail("passing preconditions summarized incorrectly")

    failed_checks = copy.deepcopy(fixtures["precondition_checks"])
    failed_checks[0]["status"] = "FAIL"
    failed_precondition = module.check_result(
        "PRECONDITION_VALIDATION_RESULT",
        pin,
        fixtures["registry_sha256"],
        "verified-completion",
        1,
        failed_checks,
    )
    if failed_precondition["reason_codes"] != ["PRECONDITION_FAILED"]:
        fail("failed precondition reason mismatch")

    unknown_checks = copy.deepcopy(fixtures["precondition_checks"])
    unknown_checks[0]["status"] = "UNKNOWN"
    unknown_precondition = module.check_result(
        "PRECONDITION_VALIDATION_RESULT",
        pin,
        fixtures["registry_sha256"],
        "verified-completion",
        1,
        unknown_checks,
    )
    if unknown_precondition["reason_codes"] != ["PRECONDITION_UNKNOWN"]:
        fail("unknown precondition reason mismatch")

    postcondition = module.check_result(
        "POSTCONDITION_VERIFICATION_RESULT",
        pin,
        fixtures["registry_sha256"],
        "verified-completion",
        1,
        fixtures["postcondition_checks"],
        "e" * 64,
    )
    if postcondition["status"] != "PASS" or postcondition["output_sha256"] != "e" * 64:
        fail("postcondition result mismatch")
    expect_error(
        module,
        lambda: module.check_result(
            "POSTCONDITION_VERIFICATION_RESULT",
            pin,
            fixtures["registry_sha256"],
            "verified-completion",
            1,
            fixtures["postcondition_checks"],
        ),
        "requires output_sha256",
    )

    composition = module.composition_declaration(
        pin,
        fixtures["registry_sha256"],
        "read-only",
        fixtures["composition_members"],
    )
    if not composition["contract_consistent"] or composition["reason_codes"]:
        fail("compatible composition was rejected")
    if composition["authority_granted"] is not False or composition["executable"] is not False:
        fail("composition declaration must never authorize or execute")

    elevated_members = copy.deepcopy(fixtures["composition_members"])
    elevated_members[1]["declared_authority_class"] = "external-write"
    elevated = module.composition_declaration(
        pin, fixtures["registry_sha256"], "read-only", elevated_members
    )
    if elevated["reason_codes"] != ["AUTHORITY_CEILING_EXCEEDED"]:
        fail("authority ceiling conflict not detected")

    conflicting_members = copy.deepcopy(fixtures["composition_members"])
    conflicting_members[1]["required_preconditions"]["authority-source"] = "different"
    conflicting = module.composition_declaration(
        pin, fixtures["registry_sha256"], "read-only", conflicting_members
    )
    if conflicting["reason_codes"] != ["PRECONDITION_CONFLICT"]:
        fail("precondition conflict not detected")

    duplicate_members = copy.deepcopy(fixtures["composition_members"])
    duplicate_members[1]["capability_id"] = duplicate_members[0]["capability_id"]
    expect_error(
        module,
        lambda: module.composition_declaration(
            pin, fixtures["registry_sha256"], "read-only", duplicate_members
        ),
        "duplicate composition capability_id",
    )

    print("P5_DECLARATIVE_DECISION_CONTRACT_TEST_PASS")


if __name__ == "__main__":
    main()
