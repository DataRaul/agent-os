"""Verify a structurally valid P5 request against an already-pinned local registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from capability_selection_contract import load_schema, validate_request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "catalog" / "capability-registry.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class BindingError(ValueError):
    pass


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise BindingError(f"{label} must be a positive integer")
    return value


def verify_binding(
    request: object,
    registry: object,
    expected_public_base_sha: str,
    expected_registry_sha256: str | None = None,
) -> dict:
    schema = load_schema()
    if not validate_request(request, schema):
        raise BindingError("selection request fails structural contract")
    if (
        not isinstance(expected_public_base_sha, str)
        or SHA_RE.fullmatch(expected_public_base_sha) is None
    ):
        raise BindingError(
            "expected public base SHA must be an exact 40-character lowercase SHA"
        )
    if request["public_base_sha"] != expected_public_base_sha:
        raise BindingError(
            "request public_base_sha does not match the consumer-verified public base SHA"
        )

    if not isinstance(registry, dict):
        raise BindingError("registry must be a JSON object")
    if registry.get("schema_version") != 1 or isinstance(
        registry.get("schema_version"), bool
    ):
        raise BindingError("registry schema_version mismatch")
    _positive_int(registry.get("registry_version"), "registry_version")
    if registry.get("status") != "PUBLIC_CAPABILITY_REGISTRY_V1":
        raise BindingError("registry status mismatch")

    registry_sha256 = canonical_sha256(registry)
    if expected_registry_sha256 is not None:
        if (
            not isinstance(expected_registry_sha256, str)
            or DIGEST_RE.fullmatch(expected_registry_sha256) is None
        ):
            raise BindingError(
                "expected registry SHA-256 must be an exact 64-character lowercase digest"
            )
        if registry_sha256 != expected_registry_sha256:
            raise BindingError("registry SHA-256 does not match the consumer-verified digest")

    capabilities = registry.get("capabilities")
    if not isinstance(capabilities, list):
        raise BindingError("registry capabilities must be an array")

    matches = [
        item
        for item in capabilities
        if isinstance(item, dict) and item.get("capability_id") == request["capability_id"]
    ]
    if len(matches) != 1:
        raise BindingError("capability ID must resolve to exactly one registry entry")
    capability = matches[0]

    if capability.get("state") != "AVAILABLE":
        raise BindingError("capability is not AVAILABLE")
    if (
        capability.get("capability_contract_version")
        != request["capability_contract_version"]
    ):
        raise BindingError("capability contract version mismatch")
    if capability.get("grants_authority") is not False:
        raise BindingError("registry entry must explicitly grant no authority")

    return {
        "schema_version": 1,
        "binding": "CAPABILITY_BINDING_VERIFIED",
        "public_base_sha": expected_public_base_sha,
        "registry_sha256": registry_sha256,
        "capability_id": request["capability_id"],
        "capability_contract_version": request["capability_contract_version"],
        "registry_version": registry["registry_version"],
        "authority_granted": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--expected-public-base-sha", required=True)
    parser.add_argument("--expected-registry-sha256")
    args = parser.parse_args()

    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        registry = json.loads(args.registry.read_text(encoding="utf-8"))
        result = verify_binding(
            request,
            registry,
            args.expected_public_base_sha,
            args.expected_registry_sha256,
        )
    except (OSError, json.JSONDecodeError, BindingError, ValueError) as exc:
        raise SystemExit(f"CAPABILITY_BINDING_FAIL: {exc}") from None

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
