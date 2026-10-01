"""Deterministic tests for the P5 bounded executable fixture router."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "p5_bounded_executable_router.py"
FIXTURES_PATH = ROOT / "benchmarks" / "p5-bounded-executable-router" / "fixtures.json"
SCHEMA_PATH = ROOT / "schemas" / "p5-bounded-execution-receipt.schema.json"


def fail(message: str) -> None:
    raise SystemExit(f"P5_BOUNDED_EXECUTABLE_ROUTER_TEST_FAIL: {message}")


def load_module():
    spec = importlib.util.spec_from_file_location("p5_bounded_executable_router", MODULE_PATH)
    if spec is None or spec.loader is None:
        fail("could not load router module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_error(module, fn, contains: str) -> None:
    try:
        fn()
    except module.RouterError as exc:
        if contains not in str(exc):
            fail(f"wrong error for {contains!r}: {exc}")
    else:
        fail(f"expected RouterError containing {contains!r}")


def main() -> None:
    module = load_module()
    fixtures = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    registry = fixtures["registry"]
    request = fixtures["request"]
    checks = fixtures["precondition_checks"]
    adapter_id = fixtures["adapter_id"]
    adapter_input = fixtures["adapter_input"]
    pin = fixtures["public_base_sha"]
    registry_digest = module.canonical_sha256(registry)

    source_digest = module.canonical_sha256(fixtures)
    result = module.execute_route(
        request,
        registry,
        pin,
        registry_digest,
        checks,
        adapter_id,
        adapter_input,
    )
    repeated = module.execute_route(
        request,
        registry,
        pin,
        registry_digest,
        checks,
        adapter_id,
        adapter_input,
    )
    if result != repeated:
        fail("identical execution inputs must produce identical receipts")
    if module.canonical_sha256(fixtures) != source_digest:
        fail("execution mutated fixture inputs")

    expected_keys = set(schema["properties"])
    if set(result) != expected_keys or set(schema["required"]) != expected_keys:
        fail("receipt shape does not match schema")
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
    if result["side_effects"] != []:
        fail("fixture execution must report no side effects")
    if result["output"] != {
        "adapter": "fixture-echo-v1",
        "payload": adapter_input["payload"],
    }:
        fail("fixture adapter output mismatch")
    if result["precondition_result"]["status"] != "PASS":
        fail("preconditions must pass")
    if result["postcondition_result"]["status"] != "PASS":
        fail("postcondition must pass")
    if result["output_sha256"] != module.canonical_sha256(result["output"]):
        fail("output digest mismatch")
    if result["adapter_input_sha256"] != module.canonical_sha256(adapter_input):
        fail("input digest mismatch")

    expect_error(
        module,
        lambda: module.execute_route(
            request, registry, "f" * 40, registry_digest, checks, adapter_id, adapter_input
        ),
        "binding rejected",
    )
    expect_error(
        module,
        lambda: module.execute_route(
            request, registry, pin, "0" * 64, checks, adapter_id, adapter_input
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
            adapter_id,
            adapter_input,
        ),
        "authority ceiling",
    )

    expect_error(
        module,
        lambda: module.execute_route(
            request,
            registry,
            pin,
            registry_digest,
            checks,
            "other-adapter",
            adapter_input,
        ),
        "adapter ID",
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
            adapter_id,
            adapter_input,
        ),
        "must PASS",
    )
    expect_error(
        module,
        lambda: module.execute_route(
            request,
            registry,
            pin,
            registry_digest,
            [],
            adapter_id,
            adapter_input,
        ),
        "exactly cover",
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
            adapter_id,
            adapter_input,
        ),
        "output_type unsupported",
    )

    extra_input = {"payload": "ok", "extra": True}
    expect_error(
        module,
        lambda: module.execute_route(
            request,
            registry,
            pin,
            registry_digest,
            checks,
            adapter_id,
            extra_input,
        ),
        "only payload",
    )
    oversized = {"payload": "x" * 5000}
    expect_error(
        module,
        lambda: module.execute_route(
            request,
            registry,
            pin,
            registry_digest,
            checks,
            adapter_id,
            oversized,
        ),
        "size bound",
    )

    authority_registry = copy.deepcopy(registry)
    authority_registry["capabilities"][0]["grants_authority"] = True
    expect_error(
        module,
        lambda: module.execute_route(
            request,
            authority_registry,
            pin,
            module.canonical_sha256(authority_registry),
            checks,
            adapter_id,
            adapter_input,
        ),
        "binding rejected",
    )

    print("P5_BOUNDED_EXECUTABLE_ROUTER_TEST_PASS")


if __name__ == "__main__":
    main()
