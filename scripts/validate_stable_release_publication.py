"""Validate recorded Agent OS v1.0.0 stable publication evidence."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLICATION_PATH = ROOT / "catalog" / "stable-release-publication.json"
CANDIDATE_PATH = ROOT / "catalog" / "stable-release-candidate.json"
REGISTRY_PATH = ROOT / "catalog" / "releases" / "v1.0.0-capability-registry.json"
VERSION_PATH = ROOT / "VERSION"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class StablePublicationError(ValueError):
    pass


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StablePublicationError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise StablePublicationError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise StablePublicationError(f"{path} must contain a JSON object")
    return value


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def validate_stable_publication(
    publication: object,
    candidate: object,
    registry: object,
    *,
    candidate_bytes: bytes | None = None,
    version_text: str | None = None,
) -> None:
    if not isinstance(publication, dict):
        raise StablePublicationError("stable publication must be an object")
    required = {
        "schema_version", "status", "version", "tag", "release_name",
        "tagged_commit_sha", "stable_candidate_blob_sha", "registry_version",
        "registry_sha256", "github_release_id", "published_at", "draft",
        "prerelease", "latest_release", "publisher", "consumer_pin_advanced",
        "private_overlay_pin_advanced", "automatic_publication",
        "explicit_publication_authority_obtained", "next_gate",
    }
    if set(publication) != required:
        raise StablePublicationError("stable publication top-level keys mismatch")
    if publication["schema_version"] != 1:
        raise StablePublicationError("schema_version must equal 1")
    if publication["status"] != "STABLE_V1_0_0_PUBLISHED":
        raise StablePublicationError("status invalid")
    if publication["version"] != "1.0.0":
        raise StablePublicationError("stable version must equal 1.0.0")
    if publication["tag"] != "v1.0.0":
        raise StablePublicationError("stable tag must equal v1.0.0")
    if publication["release_name"] != "Agent OS v1.0.0":
        raise StablePublicationError("stable release name mismatch")

    sha = publication["tagged_commit_sha"]
    if not isinstance(sha, str) or SHA_RE.fullmatch(sha) is None:
        raise StablePublicationError("tagged commit SHA invalid")

    if not isinstance(candidate, dict):
        raise StablePublicationError("stable candidate must be an object")
    if candidate.get("candidate_version") != publication["version"]:
        raise StablePublicationError("stable candidate version mismatch")
    raw = candidate_bytes if candidate_bytes is not None else CANDIDATE_PATH.read_bytes()
    if publication["stable_candidate_blob_sha"] != git_blob_sha1(raw):
        raise StablePublicationError("stable candidate blob SHA mismatch")

    if not isinstance(registry, dict):
        raise StablePublicationError("registry must be an object")
    if publication["registry_version"] != registry.get("registry_version"):
        raise StablePublicationError("registry version mismatch")
    digest = publication["registry_sha256"]
    if not isinstance(digest, str) or DIGEST_RE.fullmatch(digest) is None:
        raise StablePublicationError("registry digest invalid")
    if digest != canonical_sha256(registry):
        raise StablePublicationError("registry digest mismatch")

    release_id = publication["github_release_id"]
    if not isinstance(release_id, int) or isinstance(release_id, bool) or release_id < 1:
        raise StablePublicationError("GitHub release ID invalid")
    try:
        parsed = datetime.fromisoformat(publication["published_at"].replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise StablePublicationError("published_at invalid") from exc
    if parsed.tzinfo is None:
        raise StablePublicationError("published_at must be timezone-aware")

    if publication["draft"] is not False:
        raise StablePublicationError("stable release must not be a draft")
    if publication["prerelease"] is not False:
        raise StablePublicationError("stable release must not be a prerelease")
    if publication["latest_release"] is not True:
        raise StablePublicationError("stable v1.0.0 must be recorded as latest release")
    if publication["publisher"] != "github-actions[bot]":
        raise StablePublicationError("publisher mismatch")
    if publication["consumer_pin_advanced"] is not False:
        raise StablePublicationError("stable publication must not imply consumer pin advancement")
    if publication["private_overlay_pin_advanced"] is not False:
        raise StablePublicationError("stable publication must not imply private-overlay pin advancement")
    if publication["automatic_publication"] is not False:
        raise StablePublicationError("stable publication was explicitly authorized, not automatic")
    if publication["explicit_publication_authority_obtained"] is not True:
        raise StablePublicationError("explicit publication authority must be recorded")
    if publication["next_gate"] != "CONSUMER_OR_PRIVATE_OVERLAY_PIN_ADVANCEMENT_REQUIRES_SEPARATE_AUTHORITY":
        raise StablePublicationError("next gate mismatch")

    observed_version = version_text.strip() if version_text is not None else VERSION_PATH.read_text(encoding="utf-8").strip()
    if observed_version != publication["version"]:
        raise StablePublicationError("VERSION does not match stable publication")


def main() -> None:
    try:
        validate_stable_publication(
            load_json(PUBLICATION_PATH),
            load_json(CANDIDATE_PATH),
            load_json(REGISTRY_PATH),
        )
    except (OSError, StablePublicationError) as exc:
        raise SystemExit(f"STABLE_RELEASE_PUBLICATION_VALIDATION_FAIL: {exc}") from None
    print("STABLE_RELEASE_PUBLICATION_VALIDATION_PASS")


if __name__ == "__main__":
    main()
