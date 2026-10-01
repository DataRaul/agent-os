"""Deterministic tests for public release-readiness and compatibility rules."""

from __future__ import annotations

import copy
import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "release_readiness.py"


def fail(message: str) -> None:
    raise SystemExit(f"RELEASE_READINESS_TEST_FAIL: {message}")


def load_module():
    spec = importlib.util.spec_from_file_location("release_readiness", MODULE_PATH)
    if spec is None or spec.loader is None:
        fail("could not load release readiness module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def empty_changelog() -> dict:
    return {
        "schema_version": 1,
        "policy": "test",
        "entries": [],
    }


def log_entry(cid, change_type, old_version, new_version, registry_version) -> dict:
    return {
        "capability_id": cid,
        "change_type": change_type,
        "from_contract_version": old_version,
        "to_contract_version": new_version,
        "registry_version": registry_version,
        "compatibility": "COMPATIBLE",
        "notes": "deterministic test treatment",
    }


def expect_error(module, fn, contains: str) -> None:
    try:
        fn()
    except module.ReadinessError as exc:
        if contains not in str(exc):
            fail(f"wrong failure for {contains!r}: {exc}")
    else:
        fail(f"expected failure containing: {contains}")


def main() -> None:
    module = load_module()
    pin = "a" * 40

    readiness = module.run_readiness(ROOT, pin)
    if readiness["status"] != "READY":
        fail(f"repository should be release-ready in fixture: {readiness['reason_codes']}")
    snapshot = readiness["snapshot"]
    if snapshot is None:
        fail("ready result must include a snapshot")
    if snapshot["repository_sha"] != pin:
        fail("snapshot did not preserve exact repository SHA")
    if len(snapshot["registry_sha256"]) != 64:
        fail("snapshot registry digest invalid")
    if snapshot["authority_granted"] is not False:
        fail("snapshot must not grant authority")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "docs").mkdir()
        (root / "README.md").write_text("See `docs/missing.md`.\n", encoding="utf-8")
        broken = module.find_broken_doc_paths(root)
        if broken != ["README.md -> docs/missing.md"]:
            fail(f"broken documentation path was not detected: {broken}")
        (root / "docs" / "missing.md").write_text("ok\n", encoding="utf-8")
        if module.find_broken_doc_paths(root):
            fail("existing documentation path was rejected")

    identical = copy.deepcopy(snapshot)
    identical["repository_sha"] = "b" * 40
    same = module.compare_snapshots(snapshot, identical, empty_changelog())
    if same["status"] != "COMPATIBLE" or same["changes"]:
        fail("identical capability surface should be compatible")

    top_level_authority = copy.deepcopy(identical)
    top_level_authority["authority_granted"] = True
    expect_error(
        module,
        lambda: module.compare_snapshots(snapshot, top_level_authority, empty_changelog()),
        "snapshot authority_granted must be false",
    )

    capability_authority = copy.deepcopy(identical)
    capability_authority["capabilities"][0]["grants_authority"] = True
    expect_error(
        module,
        lambda: module.compare_snapshots(snapshot, capability_authority, empty_changelog()),
        "snapshot must not grant authority",
    )

    malformed_digest = copy.deepcopy(identical)
    malformed_digest["capabilities"][0]["path_sha256"] = "NOT_A_DIGEST"
    expect_error(
        module,
        lambda: module.compare_snapshots(snapshot, malformed_digest, empty_changelog()),
        "snapshot path_sha256",
    )

    missing_eval_digest = copy.deepcopy(identical)
    skill_with_eval = next(
        item for item in missing_eval_digest["capabilities"] if item["kind"] == "skill"
    )
    skill_with_eval.pop("eval_sha256")
    expect_error(
        module,
        lambda: module.compare_snapshots(snapshot, missing_eval_digest, empty_changelog()),
        "eval_path/eval_sha256 must be paired",
    )

    added = copy.deepcopy(identical)
    added["repository_sha"] = "c" * 40
    added["registry_version"] += 1
    added["capabilities"].append(
        {
            "capability_id": "test-capability",
            "kind": "skill",
            "state": "AVAILABLE",
            "capability_contract_version": 1,
            "path": "skills/test-capability/SKILL.md",
            "path_sha256": "0" * 64,
            "eval_path": "evals/test-capability/cases.json",
            "eval_sha256": "1" * 64,
            "grants_authority": False,
        }
    )
    expect_error(
        module,
        lambda: module.compare_snapshots(identical, added, empty_changelog()),
        "missing changelog treatment",
    )
    add_log = empty_changelog()
    add_log["entries"].append(
        log_entry(
            "test-capability",
            "ADDED",
            None,
            1,
            added["registry_version"],
        )
    )
    if module.compare_snapshots(identical, added, add_log)["status"] != "COMPATIBLE":
        fail("documented additive capability change should be compatible")

    current_id = snapshot["capabilities"][0]["capability_id"]
    structural = copy.deepcopy(identical)
    structural["repository_sha"] = "d" * 40
    structural["registry_version"] += 1
    target = next(
        item for item in structural["capabilities"] if item["capability_id"] == current_id
    )
    target["path"] = target["path"] + ".moved"
    expect_error(
        module,
        lambda: module.compare_snapshots(identical, structural, empty_changelog()),
        "without capability_contract_version increment",
    )

    versioned = copy.deepcopy(identical)
    versioned["repository_sha"] = "e" * 40
    versioned["registry_version"] += 1
    target = next(
        item for item in versioned["capabilities"] if item["capability_id"] == current_id
    )
    old_version = target["capability_contract_version"]
    target["capability_contract_version"] = old_version + 1
    version_log = empty_changelog()
    version_log["entries"].append(
        log_entry(
            current_id,
            "CONTRACT_VERSION_CHANGED",
            old_version,
            old_version + 1,
            versioned["registry_version"],
        )
    )
    if module.compare_snapshots(identical, versioned, version_log)["status"] != "COMPATIBLE":
        fail("documented contract-version increment should be compatible")

    removed = copy.deepcopy(identical)
    removed["repository_sha"] = "f" * 40
    removed["registry_version"] += 1
    removed["capabilities"].pop(0)
    expect_error(
        module,
        lambda: module.compare_snapshots(identical, removed, empty_changelog()),
        "removed without prior DEPRECATED state",
    )

    deprecated_base = copy.deepcopy(identical)
    dep_target = deprecated_base["capabilities"][0]
    dep_target["state"] = "DEPRECATED"
    removed_after_deprecation = copy.deepcopy(deprecated_base)
    removed_after_deprecation["repository_sha"] = "1" * 40
    removed_after_deprecation["registry_version"] += 1
    removed_after_deprecation["capabilities"].pop(0)
    removal_log = empty_changelog()
    removal_log["entries"].append(
        log_entry(
            current_id,
            "REMOVED",
            dep_target["capability_contract_version"],
            None,
            removed_after_deprecation["registry_version"],
        )
    )
    if (
        module.compare_snapshots(
            deprecated_base, removed_after_deprecation, removal_log
        )["status"]
        != "COMPATIBLE"
    ):
        fail("documented removal after deprecation should be compatible")

    stale_version = copy.deepcopy(versioned)
    stale_version["registry_version"] = identical["registry_version"]
    expect_error(
        module,
        lambda: module.compare_snapshots(identical, stale_version, version_log),
        "registry_version increment",
    )

    print("RELEASE_READINESS_TEST_PASS")


if __name__ == "__main__":
    main()
