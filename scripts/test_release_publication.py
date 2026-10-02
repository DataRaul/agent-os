"""Deterministic mutation tests for recorded release-publication evidence."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_release_publication.py"
PUBLICATION_PATH = ROOT / "catalog" / "release-publication.json"
CANDIDATE_PATH = ROOT / "catalog" / "release-candidate.json"
REGISTRY_PATH = ROOT / "catalog" / "releases" / "v1.0.0-capability-registry.json"


def fail(message: str) -> None:
    raise SystemExit(f"RELEASE_PUBLICATION_TEST_FAIL: {message}")


def load_module():
    spec = importlib.util.spec_from_file_location("validate_release_publication", MODULE_PATH)
    if spec is None or spec.loader is None:
        fail("could not load release-publication validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_error(module, publication, candidate, registry, contains: str, *, candidate_bytes: bytes | None = None, version: str = "1.0.0-rc.1") -> None:
    try:
        module.validate_publication(
            publication,
            candidate,
            registry,
            candidate_bytes=candidate_bytes,
            version_text=version,
        )
    except module.PublicationError as exc:
        if contains not in str(exc):
            fail(f"wrong failure for {contains!r}: {exc}")
    else:
        fail(f"expected PublicationError containing {contains!r}")


def main() -> None:
    module = load_module()
    publication = json.loads(PUBLICATION_PATH.read_text(encoding="utf-8"))
    candidate = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    candidate_bytes = CANDIDATE_PATH.read_bytes()

    module.validate_publication(
        publication,
        candidate,
        registry,
        candidate_bytes=candidate_bytes,
    )
    module.validate_publication(
        publication,
        candidate,
        registry,
        candidate_bytes=candidate_bytes,
        version_text="1.0.0-rc.1",
    )

    wrong_tag = copy.deepcopy(publication)
    wrong_tag["tag"] = "v1.0.0"
    expect_error(module, wrong_tag, candidate, registry, "tag/version", candidate_bytes=candidate_bytes)

    wrong_sha = copy.deepcopy(publication)
    wrong_sha["tagged_commit_sha"] = "main"
    expect_error(module, wrong_sha, candidate, registry, "tagged commit SHA", candidate_bytes=candidate_bytes)

    wrong_blob = copy.deepcopy(publication)
    wrong_blob["candidate_manifest_blob_sha"] = "0" * 40
    expect_error(module, wrong_blob, candidate, registry, "blob SHA mismatch", candidate_bytes=candidate_bytes)

    wrong_digest = copy.deepcopy(publication)
    wrong_digest["registry_sha256"] = "0" * 64
    expect_error(module, wrong_digest, candidate, registry, "registry digest mismatch", candidate_bytes=candidate_bytes)

    stable = copy.deepcopy(publication)
    stable["stable_release_published"] = True
    expect_error(module, stable, candidate, registry, "must not claim stable publication", candidate_bytes=candidate_bytes)

    advanced = copy.deepcopy(publication)
    advanced["consumer_pin_advanced"] = True
    expect_error(module, advanced, candidate, registry, "consumer pin", candidate_bytes=candidate_bytes)

    expect_error(module, publication, candidate, registry, "VERSION does not match", candidate_bytes=candidate_bytes, version="1.0.0")

    print("RELEASE_PUBLICATION_TEST_PASS")


if __name__ == "__main__":
    main()
