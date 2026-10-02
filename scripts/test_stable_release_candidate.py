"""Deterministic mutation tests for the 1.0.0 stable-release candidate."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_stable_release_candidate.py"
STABLE_PATH = ROOT / "catalog" / "stable-release-candidate.json"
RC_PATH = ROOT / "catalog" / "release-candidate.json"
PUBLICATION_PATH = ROOT / "catalog" / "release-publication.json"
REGISTRY_PATH = ROOT / "catalog" / "releases" / "v1.0.0-capability-registry.json"


def fail(message: str) -> None:
    raise SystemExit(f"STABLE_RELEASE_CANDIDATE_TEST_FAIL: {message}")


def load_module():
    spec = importlib.util.spec_from_file_location("validate_stable_release_candidate", MODULE_PATH)
    if spec is None or spec.loader is None:
        fail("could not load stable-release validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_error(module, stable, rc, publication, registry, contains: str, *, root: Path = ROOT, version: str = "1.0.0") -> None:
    try:
        module.validate_stable_candidate(
            stable,
            rc,
            publication,
            registry,
            root=root,
            version_text=version,
            registry_bytes=REGISTRY_PATH.read_bytes(),
        )
    except module.StableCandidateError as exc:
        if contains not in str(exc):
            fail(f"wrong failure for {contains!r}: {exc}")
    else:
        fail(f"expected StableCandidateError containing {contains!r}")


def main() -> None:
    module = load_module()
    stable = json.loads(STABLE_PATH.read_text(encoding="utf-8"))
    rc = json.loads(RC_PATH.read_text(encoding="utf-8"))
    publication = json.loads(PUBLICATION_PATH.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    module.validate_stable_candidate(
        stable,
        rc,
        publication,
        registry,
        version_text="1.0.0",
        registry_bytes=REGISTRY_PATH.read_bytes(),
    )

    wrong_version = copy.deepcopy(stable)
    wrong_version["candidate_version"] = "1.0.1"
    expect_error(module, wrong_version, rc, publication, registry, "version must equal")

    wrong_rc = copy.deepcopy(stable)
    wrong_rc["prerelease_commit_sha"] = "0" * 40
    expect_error(module, wrong_rc, rc, publication, registry, "prerelease commit mismatch")

    wrong_digest = copy.deepcopy(stable)
    wrong_digest["registry_sha256"] = "0" * 64
    expect_error(module, wrong_digest, rc, publication, registry, "registry digest mismatch")

    changed_contract = copy.deepcopy(stable)
    changed_contract["stable_capability_contracts"][0]["capability_contract_version"] += 1
    expect_error(module, changed_contract, rc, publication, registry, "drifted from RC")

    changed_blob = copy.deepcopy(stable)
    changed_blob["stable_surface_blob_snapshot"][0]["git_blob_sha"] = "0" * 40
    expect_error(module, changed_blob, rc, publication, registry, "stable surface drift")

    published = copy.deepcopy(stable)
    published["publication"]["stable_tag_created"] = True
    expect_error(module, published, rc, publication, registry, "publication boundary")

    with tempfile.TemporaryDirectory() as tmp:
        expect_error(module, stable, rc, publication, registry, "stable surface path missing", root=Path(tmp))

    expect_error(module, stable, rc, publication, registry, "VERSION does not match", version="1.0.0-rc.1")

    print("STABLE_RELEASE_CANDIDATE_TEST_PASS")


if __name__ == "__main__":
    main()
