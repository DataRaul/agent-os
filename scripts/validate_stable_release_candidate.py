"""Validate the prepared Agent OS 1.0.0 stable-release candidate."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
STABLE_PATH = ROOT / "catalog" / "stable-release-candidate.json"
RC_PATH = ROOT / "catalog" / "release-candidate.json"
PUBLICATION_PATH = ROOT / "catalog" / "release-publication.json"
REGISTRY_PATH = ROOT / "catalog" / "capability-registry.json"
VERSION_PATH = ROOT / "VERSION"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class StableCandidateError(ValueError):
    pass


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StableCandidateError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise StableCandidateError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise StableCandidateError(f"{path} must contain a JSON object")
    return value


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _safe_file(root: Path, raw: object) -> Path:
    if not isinstance(raw, str) or not raw:
        raise StableCandidateError("stable surface path invalid")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or "." in pure.parts or ".." in pure.parts:
        raise StableCandidateError(f"stable surface path not normalized: {raw}")
    path = root.joinpath(*pure.parts)
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise StableCandidateError(f"stable surface path escapes root: {raw}") from exc
    if not path.is_file():
        raise StableCandidateError(f"stable surface path missing: {raw}")
    return path


def validate_stable_candidate(
    stable: object,
    rc: object,
    publication: object,
    registry: object,
    *,
    root: Path = ROOT,
    version_text: str | None = None,
) -> None:
    if not isinstance(stable, dict):
        raise StableCandidateError("stable release candidate must be an object")
    required = {
        "schema_version",
        "status",
        "candidate_version",
        "prepared_from_main_sha",
        "prepared_at",
        "based_on_prerelease_tag",
        "prerelease_commit_sha",
        "prerelease_release_id",
        "registry_version",
        "registry_sha256",
        "stable_capability_contracts",
        "stable_interfaces",
        "stable_surface_blob_snapshot",
        "rc_validation",
        "experimental_exclusions",
        "publication",
    }
    if set(stable) != required:
        raise StableCandidateError("stable release candidate top-level keys mismatch")
    if stable["schema_version"] != 1:
        raise StableCandidateError("stable candidate schema_version must equal 1")
    if stable["status"] != "FIRST_STABLE_RELEASE_CANDIDATE_PREPARED":
        raise StableCandidateError("stable candidate status invalid")
    if stable["candidate_version"] != "1.0.0":
        raise StableCandidateError("stable candidate version must equal 1.0.0")
    if stable["prepared_at"] != "2026-10-01":
        raise StableCandidateError("stable candidate prepared_at mismatch")

    for key in ("prepared_from_main_sha", "prerelease_commit_sha"):
        value = stable[key]
        if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
            raise StableCandidateError(f"{key} invalid")

    observed_version = version_text.strip() if version_text is not None else VERSION_PATH.read_text(encoding="utf-8").strip()
    if observed_version != stable["candidate_version"]:
        raise StableCandidateError("VERSION does not match stable candidate version")

    if not isinstance(rc, dict) or not isinstance(publication, dict) or not isinstance(registry, dict):
        raise StableCandidateError("supporting release records must be objects")
    if stable["based_on_prerelease_tag"] != publication.get("tag"):
        raise StableCandidateError("prerelease tag mismatch")
    if stable["prerelease_commit_sha"] != publication.get("tagged_commit_sha"):
        raise StableCandidateError("prerelease commit mismatch")
    if stable["prerelease_release_id"] != publication.get("github_release_id"):
        raise StableCandidateError("prerelease release ID mismatch")
    if publication.get("prerelease") is not True or publication.get("draft") is not False:
        raise StableCandidateError("prerelease publication state invalid")

    if stable["registry_version"] != registry.get("registry_version"):
        raise StableCandidateError("registry version mismatch")
    digest = stable["registry_sha256"]
    if not isinstance(digest, str) or DIGEST_RE.fullmatch(digest) is None:
        raise StableCandidateError("registry digest invalid")
    if digest != canonical_sha256(registry):
        raise StableCandidateError("registry digest mismatch")

    if stable["stable_capability_contracts"] != rc.get("stable_capability_contracts"):
        raise StableCandidateError("stable capability contracts drifted from RC")
    if stable["stable_interfaces"] != rc.get("stable_interfaces"):
        raise StableCandidateError("stable interfaces drifted from RC")
    if stable["experimental_exclusions"] != rc.get("experimental_exclusions"):
        raise StableCandidateError("experimental exclusions drifted from RC")

    available = {}
    for cap in registry.get("capabilities", []):
        if isinstance(cap, dict) and cap.get("state") == "AVAILABLE":
            available[cap.get("capability_id")] = (
                cap.get("kind"),
                cap.get("capability_contract_version"),
                cap.get("path"),
                cap.get("eval_path"),
            )
    expected_contracts = {
        item["capability_id"]: (item["kind"], item["capability_contract_version"])
        for item in stable["stable_capability_contracts"]
    }
    observed_contracts = {cid: (row[0], row[1]) for cid, row in available.items()}
    if expected_contracts != observed_contracts:
        raise StableCandidateError("stable capability contracts do not match AVAILABLE registry capabilities")

    expected_paths = set(stable["stable_interfaces"])
    for cid in expected_contracts:
        row = available.get(cid)
        if row is None:
            raise StableCandidateError(f"stable capability missing from registry: {cid}")
        expected_paths.add(row[2])
        if row[3]:
            expected_paths.add(row[3])

    snapshot = stable["stable_surface_blob_snapshot"]
    if not isinstance(snapshot, list) or not snapshot:
        raise StableCandidateError("stable surface blob snapshot missing")
    observed_paths = set()
    for item in snapshot:
        if not isinstance(item, dict) or set(item) != {"path", "git_blob_sha"}:
            raise StableCandidateError("stable surface snapshot entry shape invalid")
        path = item["path"]
        blob = item["git_blob_sha"]
        if path in observed_paths:
            raise StableCandidateError("stable surface snapshot path duplicate")
        observed_paths.add(path)
        if not isinstance(blob, str) or SHA_RE.fullmatch(blob) is None:
            raise StableCandidateError(f"stable surface blob SHA invalid: {path}")
        file_path = _safe_file(root, path)
        if git_blob_sha1(file_path.read_bytes()) != blob:
            raise StableCandidateError(f"stable surface drift detected: {path}")
    if observed_paths != expected_paths:
        raise StableCandidateError("stable surface snapshot path set mismatch")

    rc_validation = stable["rc_validation"]
    expected_validation_keys = {
        "prerelease_verified",
        "prerelease_is_draft",
        "prerelease_is_prerelease",
        "tagged_commit_verified",
        "stable_surface_unchanged_since_rc",
        "post_publication_main_sha",
        "validate_run_number",
        "publication_gate_run_number",
    }
    if not isinstance(rc_validation, dict) or set(rc_validation) != expected_validation_keys:
        raise StableCandidateError("RC validation evidence shape mismatch")
    for key in ("prerelease_verified", "tagged_commit_verified", "stable_surface_unchanged_since_rc"):
        if rc_validation[key] is not True:
            raise StableCandidateError(f"RC validation {key} must be true")
    if rc_validation["prerelease_is_draft"] is not False or rc_validation["prerelease_is_prerelease"] is not True:
        raise StableCandidateError("RC release classification invalid")
    if rc_validation["post_publication_main_sha"] != stable["prepared_from_main_sha"]:
        raise StableCandidateError("RC validation main SHA mismatch")
    for key in ("validate_run_number", "publication_gate_run_number"):
        if not isinstance(rc_validation[key], int) or isinstance(rc_validation[key], bool) or rc_validation[key] < 1:
            raise StableCandidateError(f"RC validation {key} invalid")

    expected_publication = {
        "stable_tag_created": False,
        "github_release_published": False,
        "consumer_pin_advanced": False,
        "automatic_publication": False,
        "explicit_publication_authority_required": True,
    }
    if stable["publication"] != expected_publication:
        raise StableCandidateError("stable publication boundary mismatch")


def main() -> None:
    try:
        validate_stable_candidate(
            load_json(STABLE_PATH),
            load_json(RC_PATH),
            load_json(PUBLICATION_PATH),
            load_json(REGISTRY_PATH),
        )
    except (OSError, StableCandidateError) as exc:
        raise SystemExit(f"STABLE_RELEASE_CANDIDATE_VALIDATION_FAIL: {exc}") from None
    print("STABLE_RELEASE_CANDIDATE_VALIDATION_PASS")


if __name__ == "__main__":
    main()
