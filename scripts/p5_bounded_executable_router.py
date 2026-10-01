"""Bounded executable P5 router prototype for a synthetic built-in adapter.

This module proves the execution plumbing behind the declarative P5 contracts without
granting real runtime authority. It can execute exactly one in-process, side-effect-free
fixture adapter against a synthetic registry entry. It does not dynamically import code,
spawn processes, access the filesystem beyond caller-supplied JSON files in CLI mode,
use credentials, access the network, or mutate external state.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from capability_decision_contracts import (
    canonical_sha256,
    check_result,
    declared_binding_decision,
)

MAX_ADAPTER_INPUT_BYTES = 4096
SUPPORTED_CAPABILITY_ID = "fixture-echo"
SUPPORTED_CAPABILITY_VERSION = 1
SUPPORTED_ADAPTER_ID = "fixture-echo-v1"
SUPPORTED_OUTPUT_TYPE = "fixture-echo-result"
SUPPORTED_POSTCONDITIONS = ["output echoes payload"]


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


def _fixture_echo_adapter(adapter_input: object) -> dict:
    if not isinstance(adapter_input, dict) or set(adapter_input) != {"payload"}:
        raise RouterError("fixture adapter input must contain only payload")
    if len(_canonical_bytes(adapter_input)) > MAX_ADAPTER_INPUT_BYTES:
        raise RouterError("fixture adapter input exceeds size bound")
    # Canonical JSON round-trip prevents object identity or custom Python types from
    # becoming part of the executable boundary.
    clean = json.loads(_canonical_bytes(adapter_input).decode("utf-8"))
    return {
        "adapter": SUPPORTED_ADAPTER_ID,
        "payload": clean["payload"],
    }


def _validate_precondition_coverage(request: dict, checks: object) -> None:
    if not isinstance(checks, list):
        raise RouterError("precondition checks must be an array")
    check_ids = [
        item.get("check_id")
        for item in checks
        if isinstance(item, dict)
    ]
    required = request.get("required_preconditions")
    if not isinstance(required, list):
        raise RouterError("request required_preconditions invalid")
    if len(check_ids) != len(checks) or sorted(check_ids) != sorted(required):
        raise RouterError("precondition checks must exactly cover declared preconditions")


def _validate_output_contract(request: dict) -> None:
    contract = request.get("output_postcondition_contract")
    if not isinstance(contract, dict):
        raise RouterError("output postcondition contract missing")
    if contract.get("output_type") != SUPPORTED_OUTPUT_TYPE:
        raise RouterError("fixture router output_type unsupported")
    if contract.get("postconditions") != SUPPORTED_POSTCONDITIONS:
        raise RouterError("fixture router postconditions unsupported")


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
        raise RouterError("prototype execution authority ceiling is read-only")
    if request.get("capability_id") != SUPPORTED_CAPABILITY_ID:
        raise RouterError("prototype supports only fixture-echo capability")
    if request.get("capability_contract_version") != SUPPORTED_CAPABILITY_VERSION:
        raise RouterError("fixture capability version unsupported")
    if adapter_id != SUPPORTED_ADAPTER_ID:
        raise RouterError("adapter ID does not match the single built-in adapter")

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
    input_sha256 = canonical_sha256(adapter_input)
    output = _fixture_echo_adapter(adapter_input)
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
                "evidence": "deterministic fixture adapter returned the canonical payload unchanged",
            }
        ],
        output_sha256,
    )

    return {
        "schema_version": 1,
        "contract_type": "P5_BOUNDED_EXECUTION_RECEIPT",
        "execution_status": "EXECUTED",
        "runtime_scope": "SYNTHETIC_BUILTIN_ADAPTER_ONLY",
        "public_base_sha": decision["public_base_sha"],
        "registry_sha256": decision["registry_sha256"],
        "request_sha256": decision["request_sha256"],
        "capability_id": decision["capability_id"],
        "capability_contract_version": decision["capability_contract_version"],
        "adapter_id": adapter_id,
        "adapter_input_sha256": input_sha256,
        "output_sha256": output_sha256,
        "output": output,
        "precondition_result": preconditions,
        "postcondition_result": postconditions,
        "authority_source": "PUBLIC_SAFE_FIXTURE_HARNESS",
        "registry_authority_granted": False,
        "external_authority_used": False,
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
    parser.add_argument("--expected-public-base-sha", required=True)
    parser.add_argument("--expected-registry-sha256", required=True)
    args = parser.parse_args()

    try:
        bundle = _load_object(args.bundle)
        result = execute_route(
            bundle["request"],
            bundle["registry"],
            args.expected_public_base_sha,
            args.expected_registry_sha256,
            bundle["precondition_checks"],
            bundle["adapter_id"],
            bundle["adapter_input"],
        )
    except (RouterError, KeyError, ValueError) as exc:
        raise SystemExit(f"P5_BOUNDED_EXECUTABLE_ROUTER_FAIL: {exc}") from None

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
