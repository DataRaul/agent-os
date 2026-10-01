"""Validate the prepared Agent OS first stable release candidate manifest."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_PATH = ROOT / "catalog" / "release-candidate.json"
REGISTRY_PATH = ROOT / "catalog" / "capability-registry.json"
VERSION_PATH = ROOT / "VERSION"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class CandidateError(ValueError):
    pass


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CandidateError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CandidateError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CandidateError(f"{path} must contain a JSON object")
    return value


def _repo_file(root: Path, raw: object) -> None:
    if not isinstance(raw, str) or not raw:
        raise CandidateError("stable interface path invalid")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or "." in pure.parts or ".." in pure.parts:
        raise CandidateError(f"stable interface path not normalized: {raw}")
    candidate = root.joinpath(*pure.parts)
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise CandidateError(f"stable interface path escapes root: {raw}") from exc
    if not candidate.is_file():
        raise CandidateError(f"stable interface path missing: {raw}")


def validate_candidate(
    candidate: object,
    registry: object,
    root: Path = ROOT,
    version_text: str | None = None,
) -> None:
    if not isinstance(candidate, dict):
        raise CandidateError("release candidate must be an object")
    required_top = {
        "schema_version",
        "status",
        "candidate_version",
        "target_stable_version",
        "baseline_main_sha",
        "prepared_at",
        "registry_version",
        "registry_sha256",
        "stable_capability_contracts",
        "stable_interfaces",
        "experimental_exclusions",
        "stability_guarantees",
        "nonblocking_deferred_work",
        "publication",
    }
    if set(candidate) != required_top:
        raise CandidateError("release candidate top-level keys mismatch")
    if candidate["schema_version"] != 1:
        raise CandidateError("release candidate schema_version must equal 1")
    if candidate["status"] != "FIRST_STABLE_RELEASE_CANDIDATE_PREPARED":
        raise CandidateError("release candidate status invalid")
    if candidate["candidate_version"] != "1.0.0-rc.1":
        raise CandidateError("candidate version must equal 1.0.0-rc.1")
    if candidate["target_stable_version"] != "1.0.0":
        raise CandidateError("target stable version must equal 1.0.0")
    if not isinstance(candidate["baseline_main_sha"], str) or SHA_RE.fullmatch(candidate["baseline_main_sha"]) is None:
        raise CandidateError("baseline main SHA invalid")
    if candidate["prepared_at"] != "2026-10-01":
        raise CandidateError("release candidate prepared_at mismatch")

    if version_text is not None:
        observed_version = version_text.strip()
        if observed_version != candidate["candidate_version"]:
            raise CandidateError("VERSION does not match candidate version")

    if not isinstance(registry, dict):
        raise CandidateError("registry must be an object")
    if registry.get("registry_version") != candidate["registry_version"]:
        raise CandidateError("release candidate registry_version mismatch")
    registry_digest = canonical_sha256(registry)
    expected_digest = candidate["registry_sha256"]
    if not isinstance(expected_digest, str) or DIGEST_RE.fullmatch(expected_digest) is None:
        raise CandidateError("release candidate registry digest invalid")
    if registry_digest != expected_digest:
        raise CandidateError("release candidate registry digest mismatch")

    contracts = candidate["stable_capability_contracts"]
    if not isinstance(contracts, list) or not contracts:
        raise CandidateError("stable capability contracts missing")
    normalized: dict[str, tuple[str, int]] = {}
    for item in contracts:
        if not isinstance(item, dict) or set(item) != {
            "capability_id",
            "kind",
            "capability_contract_version",
        }:
            raise CandidateError("stable capability contract shape invalid")
        cid = item["capability_id"]
        version = item["capability_contract_version"]
        if not isinstance(cid, str) or not cid or cid in normalized:
            raise CandidateError("stable capability ID invalid or duplicate")
        if not isinstance(item["kind"], str) or not item["kind"]:
            raise CandidateError(f"stable capability {cid} kind invalid")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise CandidateError(f"stable capability {cid} version invalid")
        normalized[cid] = (item["kind"], version)

    expected_contracts: dict[str, tuple[str, int]] = {}
    capabilities = registry.get("capabilities")
    if not isinstance(capabilities, list):
        raise CandidateError("registry capabilities invalid")
    for cap in capabilities:
        if not isinstance(cap, dict):
            raise CandidateError("registry capability invalid")
        if cap.get("state") == "AVAILABLE":
            expected_contracts[cap["capability_id"]] = (
                cap["kind"],
                cap["capability_contract_version"],
            )
    if normalized != expected_contracts:
        raise CandidateError("stable capability contracts do not match AVAILABLE registry capabilities")

    interfaces = candidate["stable_interfaces"]
    if (
        not isinstance(interfaces, list)
        or not interfaces
        or len(interfaces) != len(set(interfaces))
    ):
        raise CandidateError("stable interfaces invalid or duplicate")
    for path in interfaces:
        _repo_file(root, path)

    exclusions = candidate["experimental_exclusions"]
    expected_exclusions = {
        "P2_SPECIALIST_REVIEWER_CANDIDATES",
        "P5_BOUNDED_EXECUTABLE_FIXTURE_ROUTER",
        "NON_ADMITTED_VENDOR_TOOLING",
        "PLAYWRIGHT_BROWSER_OBSERVATION",
    }
    if not isinstance(exclusions, list) or set(exclusions) != expected_exclusions:
        raise CandidateError("experimental exclusions mismatch")

    guarantees = candidate["stability_guarantees"]
    required_guarantees = {
        "exact_repository_sha_pin_required",
        "registry_membership_grants_authority",
        "public_repository_must_not_depend_on_private_overlay",
        "capability_contract_change_requires_version_bump",
        "capability_registry_change_requires_registry_version_and_changelog",
        "breaking_stable_interface_change_requires_major_version_after_1_0",
        "release_readiness_required_at_publication_commit",
    }
    if not isinstance(guarantees, dict) or set(guarantees) != required_guarantees:
        raise CandidateError("stability guarantees shape mismatch")
    if guarantees["registry_membership_grants_authority"] is not False:
        raise CandidateError("registry membership must never grant authority")
    for key in required_guarantees - {"registry_membership_grants_authority"}:
        if guarantees[key] is not True:
            raise CandidateError(f"stability guarantee {key} must be true")

    deferred = candidate["nonblocking_deferred_work"]
    if (
        not isinstance(deferred, list)
        or not deferred
        or any(not isinstance(item, str) or not item.strip() for item in deferred)
    ):
        raise CandidateError("nonblocking deferred work invalid")

    publication = candidate["publication"]
    expected_publication = {
        "tag_created": False,
        "github_release_published": False,
        "consumer_pin_advanced": False,
        "automatic_publication": False,
        "explicit_publication_authority_required": True,
    }
    if publication != expected_publication:
        raise CandidateError("release candidate publication boundary mismatch")


def main() -> None:
    try:
        candidate = load_json(CANDIDATE_PATH)
        registry = load_json(REGISTRY_PATH)
        validate_candidate(candidate, registry, ROOT)
    except (OSError, CandidateError) as exc:
        raise SystemExit(f"RELEASE_CANDIDATE_VALIDATION_FAIL: {exc}") from None
    print("RELEASE_CANDIDATE_VALIDATION_PASS")


if __name__ == "__main__":
    main()
