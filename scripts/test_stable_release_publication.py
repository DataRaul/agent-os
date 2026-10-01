"""Deterministic mutation tests for stable v1.0.0 publication evidence."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_stable_release_publication.py"
PUBLICATION_PATH = ROOT / "catalog" / "stable-release-publication.json"
CANDIDATE_PATH = ROOT / "catalog" / "stable-release-candidate.json"
REGISTRY_PATH = ROOT / "catalog" / "capability-registry.json"


def fail(message: str) -> None:
    raise SystemExit(f"STABLE_RELEASE_PUBLICATION_TEST_FAIL: {message}")


def load_module():
    spec = importlib.util.spec_from_file_location("validate_stable_release_publication", MODULE_PATH)
    if spec is None or spec.loader is None:
        fail("could not load stable publication validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_error(module, publication, candidate, registry, contains: str, *, candidate_bytes: bytes, version: str = "1.0.0") -> None:
    try:
        module.validate_stable_publication(
            publication,
            candidate,
            registry,
            candidate_bytes=candidate_bytes,
            version_text=version,
        )
    except module.StablePublicationError as exc:
        if contains not in str(exc):
            fail(f"wrong failure for {contains!r}: {exc}")
    else:
        fail(f"expected StablePublicationError containing {contains!r}")


def main() -> None:
    module = load_module()
    publication = json.loads(PUBLICATION_PATH.read_text(encoding="utf-8"))
    candidate = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    candidate_bytes = CANDIDATE_PATH.read_bytes()

    module.validate_stable_publication(
        publication,
        candidate,
        registry,
        candidate_bytes=candidate_bytes,
        version_text="1.0.0",
    )

    bad_tag = copy.deepcopy(publication)
    bad_tag["tag"] = "v1.0.1"
    expect_error(module, bad_tag, candidate, registry, "stable tag", candidate_bytes=candidate_bytes)

    bad_sha = copy.deepcopy(publication)
    bad_sha["tagged_commit_sha"] = "main"
    expect_error(module, bad_sha, candidate, registry, "tagged commit SHA", candidate_bytes=candidate_bytes)

    bad_blob = copy.deepcopy(publication)
    bad_blob["stable_candidate_blob_sha"] = "0" * 40
    expect_error(module, bad_blob, candidate, registry, "blob SHA mismatch", candidate_bytes=candidate_bytes)

    prerelease = copy.deepcopy(publication)
    prerelease["prerelease"] = True
    expect_error(module, prerelease, candidate, registry, "must not be a prerelease", candidate_bytes=candidate_bytes)

    advanced = copy.deepcopy(publication)
    advanced["consumer_pin_advanced"] = True
    expect_error(module, advanced, candidate, registry, "consumer pin", candidate_bytes=candidate_bytes)

    automatic = copy.deepcopy(publication)
    automatic["automatic_publication"] = True
    expect_error(module, automatic, candidate, registry, "not automatic", candidate_bytes=candidate_bytes)

    expect_error(module, publication, candidate, registry, "VERSION does not match", candidate_bytes=candidate_bytes, version="1.0.0-rc.1")

    print("STABLE_RELEASE_PUBLICATION_TEST_PASS")


if __name__ == "__main__":
    main()
