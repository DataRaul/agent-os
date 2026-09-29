"""Verify a structurally valid P5 request against an already-pinned local registry."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from capability_selection_contract import load_schema, validate_request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "catalog" / "capability-registry.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class BindingError(ValueError):
    pass


def verify_binding(request: object, registry: object, expected_public_base_sha: str) -> dict:
    schema = load_schema()
    if not validate_request(request, schema):
        raise BindingError("selection request fails structural contract")
    if not isinstance(expected_public_base_sha, str) or SHA_RE.fullmatch(expected_public_base_sha) is None:
        raise BindingError("expected public base SHA must be an exact 40-character lowercase SHA")
    if request["public_base_sha"] != expected_public_base_sha:
        raise BindingError("request public_base_sha does not match the consumer-verified public base SHA")

    if not isinstance(registry, dict):
        raise BindingError("registry must be a JSON object")
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
    if capability.get("capability_contract_version") != request["capability_contract_version"]:
        raise BindingError("capability contract version mismatch")
    if capability.get("grants_authority") is not False:
        raise BindingError("registry entry must explicitly grant no authority")

    return {
        "schema_version": 1,
        "binding": "CAPABILITY_BINDING_VERIFIED",
        "public_base_sha": expected_public_base_sha,
        "capability_id": request["capability_id"],
        "capability_contract_version": request["capability_contract_version"],
        "registry_version": registry.get("registry_version"),
        "authority_granted": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--expected-public-base-sha", required=True)
    args = parser.parse_args()

    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        registry = json.loads(args.registry.read_text(encoding="utf-8"))
        result = verify_binding(request, registry, args.expected_public_base_sha)
    except (OSError, json.JSONDecodeError, BindingError, ValueError) as exc:
        raise SystemExit(f"CAPABILITY_BINDING_FAIL: {exc}") from None

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
