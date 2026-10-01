"""Validate the recorded Agent OS v1.0.0-rc.1 publication evidence."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLICATION_PATH = ROOT / "catalog" / "release-publication.json"
CANDIDATE_PATH = ROOT / "catalog" / "release-candidate.json"
REGISTRY_PATH = ROOT / "catalog" / "capability-registry.json"
VERSION_PATH = ROOT / "VERSION"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class PublicationError(ValueError):
    pass


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PublicationError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PublicationError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PublicationError(f"{path} must contain a JSON object")
    return value


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def validate_publication(
    publication: object,
    candidate: object,
    registry: object,
    *,
    candidate_bytes: bytes | None = None,
    version_text: str | None = None,
) -> None:
    if not isinstance(publication, dict):
        raise PublicationError("release publication must be an object")

    required = {
        "schema_version",
        "status",
        "candidate_version",
        "target_stable_version",
        "tag",
        "release_name",
        "tagged_commit_sha",
        "candidate_manifest_blob_sha",
        "registry_version",
        "registry_sha256",
        "github_release_id",
        "published_at",
        "prerelease",
        "draft",
        "consumer_pin_advanced",
        "stable_release_published",
        "automatic_publication",
        "next_gate",
    }
    if set(publication) != required:
        raise PublicationError("release publication top-level keys mismatch")
    if publication["schema_version"] != 1:
        raise PublicationError("release publication schema_version must equal 1")
    if publication["status"] != "RC1_PUBLISHED":
        raise PublicationError("release publication status invalid")

    if not isinstance(candidate, dict):
        raise PublicationError("release candidate must be an object")
    if publication["candidate_version"] != candidate.get("candidate_version"):
        raise PublicationError("candidate version mismatch")
    if publication["target_stable_version"] != candidate.get("target_stable_version"):
        raise PublicationError("target stable version mismatch")
    if publication["tag"] != f'v{publication["candidate_version"]}':
        raise PublicationError("publication tag/version mismatch")
    if publication["release_name"] != f'Agent OS {publication["tag"]}':
        raise PublicationError("release name mismatch")

    sha = publication["tagged_commit_sha"]
    if not isinstance(sha, str) or SHA_RE.fullmatch(sha) is None:
        raise PublicationError("tagged commit SHA invalid")

    raw_candidate = candidate_bytes if candidate_bytes is not None else CANDIDATE_PATH.read_bytes()
    observed_blob = git_blob_sha1(raw_candidate)
    if publication["candidate_manifest_blob_sha"] != observed_blob:
        raise PublicationError("candidate manifest blob SHA mismatch")

    if not isinstance(registry, dict):
        raise PublicationError("registry must be an object")
    if publication["registry_version"] != registry.get("registry_version"):
        raise PublicationError("registry version mismatch")
    digest = publication["registry_sha256"]
    if not isinstance(digest, str) or DIGEST_RE.fullmatch(digest) is None:
        raise PublicationError("registry digest invalid")
    if digest != canonical_sha256(registry):
        raise PublicationError("registry digest mismatch")

    if not isinstance(publication["github_release_id"], int) or isinstance(publication["github_release_id"], bool) or publication["github_release_id"] < 1:
        raise PublicationError("GitHub release ID invalid")
    try:
        parsed = datetime.fromisoformat(publication["published_at"].replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise PublicationError("published_at invalid") from exc
    if parsed.tzinfo is None:
        raise PublicationError("published_at must be timezone-aware")

    if publication["prerelease"] is not True:
        raise PublicationError("RC publication must remain prerelease")
    if publication["draft"] is not False:
        raise PublicationError("published RC must not be a draft")
    if publication["consumer_pin_advanced"] is not False:
        raise PublicationError("publication must not imply consumer pin advancement")
    if publication["stable_release_published"] is not False:
        raise PublicationError("RC publication must not claim stable publication")
    if publication["automatic_publication"] is not False:
        raise PublicationError("publication was not automatic")
    if publication["next_gate"] != "RC_VALIDATION_THEN_EXPLICIT_STABLE_PUBLICATION_AUTHORITY":
        raise PublicationError("next gate mismatch")

    if version_text is not None:
        observed_version = version_text.strip()
        if observed_version != publication["candidate_version"]:
            raise PublicationError("VERSION does not match published candidate")


def main() -> None:
    try:
        publication = load_json(PUBLICATION_PATH)
        candidate = load_json(CANDIDATE_PATH)
        registry = load_json(REGISTRY_PATH)
        validate_publication(publication, candidate, registry)
    except (OSError, PublicationError) as exc:
        raise SystemExit(f"RELEASE_PUBLICATION_VALIDATION_FAIL: {exc}") from None
    print("RELEASE_PUBLICATION_VALIDATION_PASS")


if __name__ == "__main__":
    main()
