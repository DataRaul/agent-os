"""Deterministic P5 declarative decision/evidence contracts.

This module only validates and summarizes declarations about a capability already named
by a request. It never chooses another capability, loads adapters, executes tools,
satisfies preconditions, composes runtimes, or grants authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from capability_selection_contract import load_schema as load_request_schema
from capability_selection_contract import validate_request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "catalog" / "capability-registry.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
CAPABILITY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
AUTHORITY_RANK = {
    "read-only": 0,
    "local-write": 1,
    "external-write": 2,
    "destructive": 3,
    "publish-deploy": 4,
    "spend": 5,
}
CHECK_STATUSES = {"PASS", "FAIL", "UNKNOWN"}
REASON_CODES = {
    "NO_MATCH",
    "AMBIGUOUS_MATCH",
    "STALE_PIN",
    "REGISTRY_DIGEST_MISMATCH",
    "CAPABILITY_NOT_AVAILABLE",
    "CONTRACT_VERSION_MISMATCH",
    "MALFORMED_REQUEST",
    "REGISTRY_AUTHORITY_VIOLATION",
    "PRECONDITION_FAILED",
    "PRECONDITION_UNKNOWN",
    "POSTCONDITION_FAILED",
    "POSTCONDITION_UNKNOWN",
    "AUTHORITY_CEILING_EXCEEDED",
    "PRECONDITION_CONFLICT",
}


class DecisionContractError(ValueError):
    pass


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DecisionContractError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DecisionContractError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise DecisionContractError(f"{path} must contain a JSON object")
    return value


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _sha(value: object, label: str) -> str:
    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
        raise DecisionContractError(f"{label} must be an exact lowercase 40-character SHA")
    return value


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or DIGEST_RE.fullmatch(value) is None:
        raise DecisionContractError(f"{label} must be an exact lowercase 64-character digest")
    return value


def _capability_id(value: object, label: str) -> str:
    if not isinstance(value, str) or CAPABILITY_RE.fullmatch(value) is None:
        raise DecisionContractError(f"{label} invalid")
    return value


def _positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise DecisionContractError(f"{label} must be a positive integer")
    return value


def _registry_identity(registry: object) -> tuple[str, list]:
    if not isinstance(registry, dict):
        raise DecisionContractError("registry must be a JSON object")
    if registry.get("schema_version") != 1 or isinstance(registry.get("schema_version"), bool):
        raise DecisionContractError("registry schema_version mismatch")
    _positive_int(registry.get("registry_version"), "registry_version")
    if registry.get("status") != "PUBLIC_CAPABILITY_REGISTRY_V1":
        raise DecisionContractError("registry status mismatch")
    caps = registry.get("capabilities")
    if not isinstance(caps, list):
        raise DecisionContractError("registry capabilities must be an array")
    return canonical_sha256(registry), caps


def declared_binding_decision(
    request: object,
    registry: object,
    expected_public_base_sha: str,
    expected_registry_sha256: str,
) -> dict:
    """Classify binding for the single capability already declared by request."""
    _sha(expected_public_base_sha, "expected public base SHA")
    _digest(expected_registry_sha256, "expected registry SHA-256")
    registry_digest, caps = _registry_identity(registry)

    request_is_valid = validate_request(request, load_request_schema())
    if request_is_valid:
        capability_id = request["capability_id"]
        contract_version = request["capability_contract_version"]
        request_digest = canonical_sha256(request)
        public_base_sha = request["public_base_sha"]
    else:
        capability_id = "malformed-request"
        contract_version = 1
        request_digest = canonical_sha256(request)
        public_base_sha = expected_public_base_sha

    reason_codes: list[str] = []
    disposition = "REJECTED"

    if not request_is_valid:
        reason_codes.append("MALFORMED_REQUEST")
    elif public_base_sha != expected_public_base_sha:
        reason_codes.append("STALE_PIN")
    elif registry_digest != expected_registry_sha256:
        reason_codes.append("REGISTRY_DIGEST_MISMATCH")
    else:
        matches = [
            cap for cap in caps
            if isinstance(cap, dict) and cap.get("capability_id") == capability_id
        ]
        if not matches:
            disposition = "NO_MATCH"
            reason_codes.append("NO_MATCH")
        elif len(matches) > 1:
            disposition = "AMBIGUOUS_MATCH"
            reason_codes.append("AMBIGUOUS_MATCH")
        else:
            cap = matches[0]
            if cap.get("state") != "AVAILABLE":
                reason_codes.append("CAPABILITY_NOT_AVAILABLE")
            if cap.get("capability_contract_version") != contract_version:
                reason_codes.append("CONTRACT_VERSION_MISMATCH")
            if cap.get("grants_authority") is not False:
                reason_codes.append("REGISTRY_AUTHORITY_VIOLATION")
            if not reason_codes:
                disposition = "BOUND"

    return {
        "schema_version": 1,
        "contract_type": "DECLARED_CAPABILITY_BINDING_DECISION",
        "disposition": disposition,
        "public_base_sha": public_base_sha,
        "registry_sha256": registry_digest,
        "request_sha256": request_digest,
        "capability_id": capability_id,
        "capability_contract_version": contract_version,
        "reason_codes": sorted(set(reason_codes)),
        "authority_granted": False,
        "executable": False,
    }


def _validated_checks(checks: object) -> list[dict]:
    if not isinstance(checks, list):
        raise DecisionContractError("checks must be an array")
    seen: set[str] = set()
    output: list[dict] = []
    for index, check in enumerate(checks):
        if not isinstance(check, dict) or set(check) != {"check_id", "status", "evidence"}:
            raise DecisionContractError(f"check {index} shape invalid")
        check_id = check.get("check_id")
        if not isinstance(check_id, str) or not check_id.strip() or check_id in seen:
            raise DecisionContractError(f"check {index} check_id invalid or duplicate")
        seen.add(check_id)
        status = check.get("status")
        if status not in CHECK_STATUSES:
            raise DecisionContractError(f"check {check_id} status invalid")
        evidence = check.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            raise DecisionContractError(f"check {check_id} evidence missing")
        output.append(
            {"check_id": check_id, "status": status, "evidence": evidence}
        )
    return output


def check_result(
    contract_type: str,
    public_base_sha: str,
    registry_sha256: str,
    capability_id: str,
    capability_contract_version: int,
    checks: object,
    output_sha256: str | None = None,
) -> dict:
    if contract_type not in {
        "PRECONDITION_VALIDATION_RESULT",
        "POSTCONDITION_VERIFICATION_RESULT",
    }:
        raise DecisionContractError("unsupported check contract_type")
    public_base_sha = _sha(public_base_sha, "public_base_sha")
    registry_sha256 = _digest(registry_sha256, "registry_sha256")
    capability_id = _capability_id(capability_id, "capability_id")
    capability_contract_version = _positive_int(
        capability_contract_version, "capability_contract_version"
    )
    validated = _validated_checks(checks)

    statuses = {item["status"] for item in validated}
    if "FAIL" in statuses:
        status = "FAIL"
    elif "UNKNOWN" in statuses:
        status = "UNKNOWN"
    else:
        status = "PASS"

    prefix = "PRECONDITION" if contract_type.startswith("PRECONDITION") else "POSTCONDITION"
    reason_codes: list[str] = []
    if status == "FAIL":
        reason_codes.append(f"{prefix}_FAILED")
    elif status == "UNKNOWN":
        reason_codes.append(f"{prefix}_UNKNOWN")

    result = {
        "schema_version": 1,
        "contract_type": contract_type,
        "status": status,
        "public_base_sha": public_base_sha,
        "registry_sha256": registry_sha256,
        "capability_id": capability_id,
        "capability_contract_version": capability_contract_version,
        "checks": validated,
        "reason_codes": reason_codes,
        "authority_granted": False,
        "executable": False,
    }
    if contract_type == "POSTCONDITION_VERIFICATION_RESULT":
        if output_sha256 is None:
            raise DecisionContractError("postcondition result requires output_sha256")
        result["output_sha256"] = _digest(output_sha256, "output_sha256")
    elif output_sha256 is not None:
        raise DecisionContractError("precondition result must not include output_sha256")
    return result


def composition_declaration(
    public_base_sha: str,
    registry_sha256: str,
    authority_ceiling: str,
    members: object,
) -> dict:
    public_base_sha = _sha(public_base_sha, "public_base_sha")
    registry_sha256 = _digest(registry_sha256, "registry_sha256")
    if authority_ceiling not in AUTHORITY_RANK:
        raise DecisionContractError("authority_ceiling invalid")
    if not isinstance(members, list) or len(members) < 2:
        raise DecisionContractError("composition requires at least two explicit members")

    normalized: list[dict] = []
    ids: set[str] = set()
    preconditions: dict[str, str] = {}
    reason_codes: set[str] = set()

    for index, member in enumerate(members):
        required = {
            "capability_id",
            "capability_contract_version",
            "request_sha256",
            "declared_authority_class",
            "required_preconditions",
        }
        if not isinstance(member, dict) or set(member) != required:
            raise DecisionContractError(f"composition member {index} shape invalid")

        cid = _capability_id(member["capability_id"], f"member {index} capability_id")
        if cid in ids:
            raise DecisionContractError(f"duplicate composition capability_id: {cid}")
        ids.add(cid)
        version = _positive_int(
            member["capability_contract_version"],
            f"member {cid} capability_contract_version",
        )
        request_digest = _digest(member["request_sha256"], f"member {cid} request_sha256")
        authority = member["declared_authority_class"]
        if authority not in AUTHORITY_RANK:
            raise DecisionContractError(f"member {cid} authority invalid")
        if AUTHORITY_RANK[authority] > AUTHORITY_RANK[authority_ceiling]:
            reason_codes.add("AUTHORITY_CEILING_EXCEEDED")

        raw_preconditions = member["required_preconditions"]
        if not isinstance(raw_preconditions, dict):
            raise DecisionContractError(f"member {cid} required_preconditions must be object")
        clean_preconditions: dict[str, str] = {}
        for key, value in sorted(raw_preconditions.items()):
            if (
                not isinstance(key, str)
                or not key.strip()
                or not isinstance(value, str)
                or not value.strip()
            ):
                raise DecisionContractError(f"member {cid} precondition key/value invalid")
            if key in preconditions and preconditions[key] != value:
                reason_codes.add("PRECONDITION_CONFLICT")
            else:
                preconditions[key] = value
            clean_preconditions[key] = value

        normalized.append(
            {
                "capability_id": cid,
                "capability_contract_version": version,
                "request_sha256": request_digest,
                "declared_authority_class": authority,
                "required_preconditions": clean_preconditions,
            }
        )

    return {
        "schema_version": 1,
        "contract_type": "MULTI_CAPABILITY_COMPOSITION_DECLARATION",
        "public_base_sha": public_base_sha,
        "registry_sha256": registry_sha256,
        "authority_ceiling": authority_ceiling,
        "members": normalized,
        "contract_consistent": not reason_codes,
        "reason_codes": sorted(reason_codes),
        "authority_granted": False,
        "executable": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    binding = sub.add_parser("binding")
    binding.add_argument("request", type=Path)
    binding.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    binding.add_argument("--expected-public-base-sha", required=True)
    binding.add_argument("--expected-registry-sha256", required=True)

    check = sub.add_parser("check-result")
    check.add_argument("input", type=Path)

    composition = sub.add_parser("composition")
    composition.add_argument("input", type=Path)

    args = parser.parse_args()
    try:
        if args.command == "binding":
            result = declared_binding_decision(
                load_json(args.request),
                load_json(args.registry),
                args.expected_public_base_sha,
                args.expected_registry_sha256,
            )
        elif args.command == "check-result":
            value = load_json(args.input)
            result = check_result(
                value["contract_type"],
                value["public_base_sha"],
                value["registry_sha256"],
                value["capability_id"],
                value["capability_contract_version"],
                value["checks"],
                value.get("output_sha256"),
            )
        else:
            value = load_json(args.input)
            result = composition_declaration(
                value["public_base_sha"],
                value["registry_sha256"],
                value["authority_ceiling"],
                value["members"],
            )
    except (DecisionContractError, KeyError) as exc:
        raise SystemExit(f"P5_DECLARATIVE_DECISION_CONTRACT_FAIL: {exc}") from None

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
