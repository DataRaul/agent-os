"""Deterministic public release-readiness and registry-compatibility checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "catalog" / "capability-registry.json"
CHANGELOG_PATH = ROOT / "catalog" / "capability-changelog.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
CAPABILITY_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ALLOWED_CAPABILITY_KINDS = {"skill", "reviewer", "tool", "adapter"}
ALLOWED_CAPABILITY_STATES = {"AVAILABLE", "DEPRECATED"}
SNAPSHOT_TOP_LEVEL_KEYS = {
    "schema_version",
    "snapshot_type",
    "repository_sha",
    "registry_version",
    "registry_sha256",
    "capabilities",
    "authority_granted",
}
SNAPSHOT_CAPABILITY_REQUIRED_KEYS = {
    "capability_id",
    "kind",
    "state",
    "capability_contract_version",
    "path",
    "path_sha256",
    "grants_authority",
}
SNAPSHOT_CAPABILITY_OPTIONAL_KEYS = {"eval_path", "eval_sha256", "primary_skill"}
BACKTICK_PATH_RE = re.compile(
    r"`((?:docs|scripts|catalog|schemas|benchmarks|\.github)"
    r"/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*)`"
)
REQUIRED_LOCAL_CHECKS = (
    ("agent_os_validation", "scripts/validate_agent_os.py", "AGENT_OS_VALIDATION_FAILED"),
    ("publication_gate", "scripts/validate_publication_gate.py", "PUBLICATION_GATE_FAILED"),
    (
        "capability_registry",
        "scripts/validate_capability_registry.py",
        "CAPABILITY_REGISTRY_FAILED",
    ),
    (
        "release_candidate_history",
        "scripts/validate_release_candidate.py",
        "RELEASE_CANDIDATE_HISTORY_FAILED",
    ),
    (
        "release_publication_history",
        "scripts/validate_release_publication.py",
        "RELEASE_PUBLICATION_HISTORY_FAILED",
    ),
    (
        "stable_release_candidate",
        "scripts/validate_stable_release_candidate.py",
        "STABLE_RELEASE_CANDIDATE_FAILED",
    ),
    (
        "stable_release_publication",
        "scripts/validate_stable_release_publication.py",
        "STABLE_RELEASE_PUBLICATION_FAILED",
    ),
)


class ReadinessError(ValueError):
    pass


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReadinessError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ReadinessError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReadinessError(f"{path} must contain a JSON object")
    return value


def _valid_sha(value: object, label: str) -> str:
    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
        raise ReadinessError(f"{label} must be an exact 40-character lowercase SHA")
    return value


def _valid_digest(value: object, label: str) -> str:
    if not isinstance(value, str) or DIGEST_RE.fullmatch(value) is None:
        raise ReadinessError(f"{label} must be an exact 64-character lowercase SHA-256")
    return value


def _nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReadinessError(f"{label} must be a non-empty string")
    return value


def _validate_snapshot_capability(cap: object, index: int) -> str:
    if not isinstance(cap, dict):
        raise ReadinessError(f"snapshot capability {index} must be an object")

    keys = set(cap)
    missing = SNAPSHOT_CAPABILITY_REQUIRED_KEYS - keys
    extra = keys - (SNAPSHOT_CAPABILITY_REQUIRED_KEYS | SNAPSHOT_CAPABILITY_OPTIONAL_KEYS)
    if missing or extra:
        raise ReadinessError(
            f"snapshot capability {index} keys mismatch: "
            f"missing={sorted(missing)} extra={sorted(extra)}"
        )

    cid = _nonempty_string(cap.get("capability_id"), f"snapshot capability {index} capability_id")
    if CAPABILITY_ID_RE.fullmatch(cid) is None:
        raise ReadinessError(f"snapshot capability_id invalid: {cid!r}")

    kind = cap.get("kind")
    if kind not in ALLOWED_CAPABILITY_KINDS:
        raise ReadinessError(f"{cid} snapshot kind invalid: {kind!r}")
    state = cap.get("state")
    if state not in ALLOWED_CAPABILITY_STATES:
        raise ReadinessError(f"{cid} snapshot state invalid: {state!r}")

    version = cap.get("capability_contract_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ReadinessError(f"{cid} snapshot capability_contract_version invalid")

    path = _nonempty_string(cap.get("path"), f"{cid} snapshot path")
    _valid_digest(cap.get("path_sha256"), f"{cid} snapshot path_sha256")
    if cap.get("grants_authority") is not False:
        raise ReadinessError(f"{cid} snapshot must not grant authority")

    has_eval_path = "eval_path" in cap
    has_eval_digest = "eval_sha256" in cap
    if has_eval_path != has_eval_digest:
        raise ReadinessError(f"{cid} snapshot eval_path/eval_sha256 must be paired")
    if has_eval_path:
        _nonempty_string(cap.get("eval_path"), f"{cid} snapshot eval_path")
        _valid_digest(cap.get("eval_sha256"), f"{cid} snapshot eval_sha256")

    if kind == "skill":
        expected_path = f"skills/{cid}/SKILL.md"
        expected_eval = f"evals/{cid}/cases.json"
        if path != expected_path:
            raise ReadinessError(f"{cid} snapshot skill path must equal {expected_path}")
        if cap.get("eval_path") != expected_eval:
            raise ReadinessError(f"{cid} snapshot eval_path must equal {expected_eval}")
        if "primary_skill" in cap:
            raise ReadinessError(f"{cid} snapshot skill must not declare primary_skill")
    elif kind == "reviewer":
        expected_path = f"agents/{cid}.md"
        if path != expected_path:
            raise ReadinessError(f"{cid} snapshot reviewer path must equal {expected_path}")
        primary = cap.get("primary_skill")
        if not isinstance(primary, str) or CAPABILITY_ID_RE.fullmatch(primary) is None:
            raise ReadinessError(f"{cid} snapshot reviewer primary_skill invalid")
    elif "primary_skill" in cap:
        raise ReadinessError(f"{cid} snapshot {kind} must not declare primary_skill")

    return cid


def resolve_repository_sha(root: Path = ROOT) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise ReadinessError("could not resolve repository HEAD SHA")
    return _valid_sha(proc.stdout.strip(), "repository SHA")


def _run_local_check(root: Path, relative_script: str) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, str(root / relative_script)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    detail = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0, detail


def find_broken_doc_paths(root: Path = ROOT) -> list[str]:
    broken: list[str] = []
    for path in sorted(root.rglob("*.md")):
        if any(part in {".git", ".venv", "venv", "node_modules"} for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in BACKTICK_PATH_RE.finditer(text):
            raw = match.group(1)
            if not (root / raw).exists():
                broken.append(f"{path.relative_to(root)} -> {raw}")
    return sorted(set(broken))


def build_snapshot(root: Path, repository_sha: str) -> dict:
    repository_sha = _valid_sha(repository_sha, "repository SHA")
    registry_path = root / "catalog" / "capability-registry.json"
    registry = load_json(registry_path)
    caps = registry.get("capabilities")
    if not isinstance(caps, list):
        raise ReadinessError("registry capabilities must be an array")

    capability_rows: list[dict] = []
    for cap in caps:
        if not isinstance(cap, dict):
            raise ReadinessError("registry capability must be an object")
        path = cap.get("path")
        if not isinstance(path, str) or not (root / path).is_file():
            raise ReadinessError(f"capability path missing: {path!r}")
        row = {
            "capability_id": cap.get("capability_id"),
            "kind": cap.get("kind"),
            "state": cap.get("state"),
            "capability_contract_version": cap.get("capability_contract_version"),
            "path": path,
            "path_sha256": file_sha256(root / path),
            "grants_authority": cap.get("grants_authority"),
        }
        for optional in ("eval_path", "primary_skill"):
            if optional in cap:
                row[optional] = cap[optional]
        if "eval_path" in cap:
            eval_path = cap["eval_path"]
            if not isinstance(eval_path, str) or not (root / eval_path).is_file():
                raise ReadinessError(
                    f"capability eval path missing: {cap.get('capability_id')}: {eval_path!r}"
                )
            row["eval_sha256"] = file_sha256(root / eval_path)
        capability_rows.append(row)

    capability_rows.sort(key=lambda item: str(item["capability_id"]))
    return {
        "schema_version": 1,
        "snapshot_type": "PUBLIC_CAPABILITY_SNAPSHOT_V1",
        "repository_sha": repository_sha,
        "registry_version": registry.get("registry_version"),
        "registry_sha256": canonical_sha256(registry),
        "capabilities": capability_rows,
        "authority_granted": False,
    }


def run_readiness(root: Path = ROOT, repository_sha: str | None = None) -> dict:
    checks: dict[str, dict] = {}
    reason_codes: list[str] = []

    for name, script, reason in REQUIRED_LOCAL_CHECKS:
        ok, detail = _run_local_check(root, script)
        checks[name] = {"pass": ok, "detail": detail}
        if not ok:
            reason_codes.append(reason)

    broken = find_broken_doc_paths(root)
    checks["documentation_paths"] = {"pass": not broken, "broken": broken}
    if broken:
        reason_codes.append("DOCUMENT_PATH_INCONSISTENT")

    resolved_sha: str | None = None
    try:
        resolved_sha = (
            _valid_sha(repository_sha, "repository SHA")
            if repository_sha is not None
            else resolve_repository_sha(root)
        )
    except ReadinessError as exc:
        checks["repository_sha"] = {"pass": False, "detail": str(exc)}
        reason_codes.append("REPOSITORY_SHA_UNRESOLVED")
    else:
        checks["repository_sha"] = {"pass": True, "value": resolved_sha}

    snapshot = None
    if not reason_codes and resolved_sha is not None:
        try:
            snapshot = build_snapshot(root, resolved_sha)
        except ReadinessError as exc:
            checks["capability_snapshot"] = {"pass": False, "detail": str(exc)}
            reason_codes.append("CAPABILITY_SNAPSHOT_FAILED")
        else:
            checks["capability_snapshot"] = {
                "pass": True,
                "registry_sha256": snapshot["registry_sha256"],
                "capability_count": len(snapshot["capabilities"]),
            }

    return {
        "schema_version": 1,
        "status": "READY" if not reason_codes else "FAIL",
        "reason_codes": sorted(set(reason_codes)),
        "checks": checks,
        "snapshot": snapshot,
        "auto_publish": False,
        "authority_granted": False,
    }


def _snapshot_map(snapshot: dict) -> dict[str, dict]:
    if set(snapshot) != SNAPSHOT_TOP_LEVEL_KEYS:
        missing = sorted(SNAPSHOT_TOP_LEVEL_KEYS - set(snapshot))
        extra = sorted(set(snapshot) - SNAPSHOT_TOP_LEVEL_KEYS)
        raise ReadinessError(
            f"snapshot top-level keys mismatch: missing={missing} extra={extra}"
        )
    if snapshot.get("schema_version") != 1:
        raise ReadinessError("snapshot schema_version must equal 1")
    if snapshot.get("snapshot_type") != "PUBLIC_CAPABILITY_SNAPSHOT_V1":
        raise ReadinessError("snapshot type mismatch")
    _valid_sha(snapshot.get("repository_sha"), "snapshot repository SHA")
    version = snapshot.get("registry_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ReadinessError("snapshot registry_version must be a positive integer")
    _valid_digest(snapshot.get("registry_sha256"), "snapshot registry_sha256")
    if snapshot.get("authority_granted") is not False:
        raise ReadinessError("snapshot authority_granted must be false")

    caps = snapshot.get("capabilities")
    if not isinstance(caps, list) or not caps:
        raise ReadinessError("snapshot capabilities must be a non-empty array")

    result: dict[str, dict] = {}
    for index, cap in enumerate(caps):
        cid = _validate_snapshot_capability(cap, index)
        if cid in result:
            raise ReadinessError(f"duplicate snapshot capability: {cid}")
        result[cid] = cap

    for cid, cap in result.items():
        if cap.get("kind") != "reviewer":
            continue
        primary = cap["primary_skill"]
        if primary not in result or result[primary].get("kind") != "skill":
            raise ReadinessError(f"{cid} snapshot primary_skill not present as a skill")

    return result


def _expected_change_entry(
    capability_id: str,
    change_type: str,
    old_version: int | None,
    new_version: int | None,
    registry_version: int,
) -> tuple:
    return (capability_id, change_type, old_version, new_version, registry_version)


def _changelog_entries(changelog: dict) -> set[tuple]:
    if changelog.get("schema_version") != 1:
        raise ReadinessError("capability changelog schema_version must equal 1")
    entries = changelog.get("entries")
    if not isinstance(entries, list):
        raise ReadinessError("capability changelog entries must be an array")
    normalized: set[tuple] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ReadinessError(f"changelog entry {index} must be an object")
        required = {
            "capability_id",
            "change_type",
            "from_contract_version",
            "to_contract_version",
            "registry_version",
            "compatibility",
            "notes",
        }
        if set(entry) != required:
            raise ReadinessError(f"changelog entry {index} keys mismatch")
        if entry["compatibility"] not in {"COMPATIBLE", "BREAKING_WITH_MIGRATION"}:
            raise ReadinessError(f"changelog entry {index} compatibility invalid")
        if not isinstance(entry["notes"], str) or not entry["notes"].strip():
            raise ReadinessError(f"changelog entry {index} notes missing")
        normalized.add(
            (
                entry["capability_id"],
                entry["change_type"],
                entry["from_contract_version"],
                entry["to_contract_version"],
                entry["registry_version"],
            )
        )
    return normalized


def compare_snapshots(old: dict, new: dict, changelog: dict) -> dict:
    old_map = _snapshot_map(old)
    new_map = _snapshot_map(new)
    old_registry_version = old["registry_version"]
    new_registry_version = new["registry_version"]
    if new_registry_version < old_registry_version:
        raise ReadinessError("registry_version must not decrease")

    changes: list[dict] = []
    required_log_entries: list[tuple] = []

    for cid in sorted(old_map.keys() - new_map.keys()):
        old_cap = old_map[cid]
        if old_cap.get("state") != "DEPRECATED":
            raise ReadinessError(f"{cid} removed without prior DEPRECATED state")
        old_version = old_cap.get("capability_contract_version")
        changes.append({"capability_id": cid, "change_type": "REMOVED"})
        required_log_entries.append(
            _expected_change_entry(
                cid, "REMOVED", old_version, None, new_registry_version
            )
        )

    for cid in sorted(new_map.keys() - old_map.keys()):
        new_cap = new_map[cid]
        new_version = new_cap.get("capability_contract_version")
        changes.append({"capability_id": cid, "change_type": "ADDED"})
        required_log_entries.append(
            _expected_change_entry(
                cid, "ADDED", None, new_version, new_registry_version
            )
        )

    structural_fields = ("kind", "path", "eval_path", "primary_skill")
    for cid in sorted(old_map.keys() & new_map.keys()):
        old_cap = old_map[cid]
        new_cap = new_map[cid]
        old_version = old_cap.get("capability_contract_version")
        new_version = new_cap.get("capability_contract_version")
        if (
            not isinstance(old_version, int)
            or isinstance(old_version, bool)
            or old_version < 1
            or not isinstance(new_version, int)
            or isinstance(new_version, bool)
            or new_version < 1
        ):
            raise ReadinessError(f"{cid} contract version invalid")
        if new_version < old_version:
            raise ReadinessError(f"{cid} capability_contract_version must not decrease")

        structural_changed = any(old_cap.get(f) != new_cap.get(f) for f in structural_fields)
        state_changed = old_cap.get("state") != new_cap.get("state")

        if structural_changed and new_version == old_version:
            raise ReadinessError(
                f"{cid} structural contract changed without capability_contract_version increment"
            )

        if old_cap.get("state") == "DEPRECATED" and new_cap.get("state") == "AVAILABLE":
            if new_version == old_version:
                raise ReadinessError(f"{cid} reactivated without contract-version increment")
            changes.append({"capability_id": cid, "change_type": "REACTIVATED"})
            required_log_entries.append(
                _expected_change_entry(
                    cid, "REACTIVATED", old_version, new_version, new_registry_version
                )
            )
        elif state_changed:
            if old_cap.get("state") == "AVAILABLE" and new_cap.get("state") == "DEPRECATED":
                changes.append({"capability_id": cid, "change_type": "DEPRECATED"})
                required_log_entries.append(
                    _expected_change_entry(
                        cid, "DEPRECATED", old_version, new_version, new_registry_version
                    )
                )
            else:
                raise ReadinessError(f"{cid} unsupported state transition")

        if new_version > old_version and not (
            old_cap.get("state") == "DEPRECATED" and new_cap.get("state") == "AVAILABLE"
        ):
            changes.append(
                {"capability_id": cid, "change_type": "CONTRACT_VERSION_CHANGED"}
            )
            required_log_entries.append(
                _expected_change_entry(
                    cid,
                    "CONTRACT_VERSION_CHANGED",
                    old_version,
                    new_version,
                    new_registry_version,
                )
            )

    if changes and new_registry_version <= old_registry_version:
        raise ReadinessError("capability changes require registry_version increment")

    available_log_entries = _changelog_entries(changelog)
    missing = [entry for entry in required_log_entries if entry not in available_log_entries]
    if missing:
        raise ReadinessError(
            "capability changes missing changelog treatment: "
            + ", ".join(f"{cid}/{kind}" for cid, kind, *_ in missing)
        )

    return {
        "schema_version": 1,
        "status": "COMPATIBLE",
        "base_repository_sha": old["repository_sha"],
        "head_repository_sha": new["repository_sha"],
        "base_registry_version": old_registry_version,
        "head_registry_version": new_registry_version,
        "changes": changes,
        "changelog_treatment_complete": True,
        "automatic_upgrade_authorized": False,
        "authority_granted": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check")
    check.add_argument("--repository-sha")
    check.add_argument("--snapshot-out", type=Path)

    compare = sub.add_parser("compare")
    compare.add_argument("base_snapshot", type=Path)
    compare.add_argument("head_snapshot", type=Path)
    compare.add_argument("--changelog", type=Path, default=CHANGELOG_PATH)

    args = parser.parse_args()

    if args.command == "check":
        result = run_readiness(ROOT, args.repository_sha)
        if args.snapshot_out is not None and result["snapshot"] is not None:
            args.snapshot_out.write_text(
                json.dumps(result["snapshot"], indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(0 if result["status"] == "READY" else 1)

    try:
        result = compare_snapshots(
            load_json(args.base_snapshot),
            load_json(args.head_snapshot),
            load_json(args.changelog),
        )
    except ReadinessError as exc:
        result = {
            "schema_version": 1,
            "status": "FAIL",
            "reason_codes": ["REGISTRY_COMPATIBILITY_FAILED"],
            "detail": str(exc),
            "automatic_upgrade_authorized": False,
            "authority_granted": False,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(1) from None

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
