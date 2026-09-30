from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "catalog" / "capability-registry.json"

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ALLOWED_KINDS = {"skill", "reviewer", "tool", "adapter"}
ALLOWED_STATES = {"AVAILABLE", "DEPRECATED"}
TOP_LEVEL_KEYS = {
    "schema_version",
    "registry_version",
    "status",
    "versioning_policy",
    "authority_policy",
    "privacy_policy",
    "capabilities",
}
CAPABILITY_KEYS = {
    "capability_id",
    "kind",
    "state",
    "capability_contract_version",
    "path",
    "eval_path",
    "primary_skill",
    "grants_authority",
}


class RegistryError(ValueError):
    pass


def reject(message: str) -> None:
    raise RegistryError(message)


def _positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        reject(f"{label} must be a positive integer")
    return value


def _nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        reject(f"{label} must be a non-empty string")
    return value


def _repo_file(root: Path, raw: object, label: str) -> Path:
    value = _nonempty_string(raw, label)
    pure = PurePosixPath(value)
    if pure.is_absolute() or "." in pure.parts or ".." in pure.parts:
        reject(f"{label} must be a normalized repository-relative path")

    root_resolved = root.resolve()
    candidate = root.joinpath(*pure.parts)
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError:
        reject(f"{label} escapes repository root")

    if not candidate.is_file():
        reject(f"{label} missing: {value}")
    return candidate


def validate_registry(data: object, root: Path = ROOT) -> None:
    if not isinstance(data, dict):
        reject("registry must contain a JSON object")
    if set(data) != TOP_LEVEL_KEYS:
        missing = sorted(TOP_LEVEL_KEYS - set(data))
        extra = sorted(set(data) - TOP_LEVEL_KEYS)
        reject(f"registry top-level keys mismatch: missing={missing} extra={extra}")

    if data.get("schema_version") != 1 or isinstance(data.get("schema_version"), bool):
        reject("unsupported schema_version")
    _positive_int(data.get("registry_version"), "registry_version")
    if data.get("status") != "PUBLIC_CAPABILITY_REGISTRY_V1":
        reject("registry status mismatch")
    for key in ("versioning_policy", "authority_policy", "privacy_policy"):
        _nonempty_string(data.get(key), key)

    caps = data.get("capabilities")
    if not isinstance(caps, list) or not caps:
        reject("capabilities must be non-empty")

    ids: set[str] = set()
    paths: set[str] = set()
    eval_paths: set[str] = set()
    registered_skills: set[str] = set()
    registered_reviewers: set[str] = set()

    for index, cap in enumerate(caps):
        if not isinstance(cap, dict):
            reject(f"capability {index} must be object")
        unknown = set(cap) - CAPABILITY_KEYS
        required = {
            "capability_id",
            "kind",
            "state",
            "capability_contract_version",
            "path",
            "grants_authority",
        }
        missing = required - set(cap)
        if missing or unknown:
            reject(
                f"capability {index} keys mismatch: missing={sorted(missing)} extra={sorted(unknown)}"
            )

        cid = _nonempty_string(cap.get("capability_id"), f"capability {index} capability_id")
        if ID_RE.fullmatch(cid) is None:
            reject(f"invalid capability_id: {cid!r}")
        if cid in ids:
            reject(f"duplicate capability_id: {cid}")
        ids.add(cid)

        kind = cap.get("kind")
        if kind not in ALLOWED_KINDS:
            reject(f"{cid} unsupported kind: {kind!r}")
        state = cap.get("state")
        if state not in ALLOWED_STATES:
            reject(f"{cid} unsupported state: {state!r}")
        _positive_int(cap.get("capability_contract_version"), f"{cid} capability_contract_version")

        if cap.get("grants_authority") is not False:
            reject(f"{cid} must not grant authority")

        raw_path = _nonempty_string(cap.get("path"), f"{cid} path")
        _repo_file(root, raw_path, f"{cid} path")
        if raw_path in paths:
            reject(f"duplicate capability path: {raw_path}")
        paths.add(raw_path)

        if kind == "skill":
            registered_skills.add(cid)
            expected_path = f"skills/{cid}/SKILL.md"
            expected_eval = f"evals/{cid}/cases.json"
            if raw_path != expected_path:
                reject(f"{cid} skill path must equal {expected_path}")
            if cap.get("eval_path") != expected_eval:
                reject(f"{cid} eval_path must equal {expected_eval}")
            _repo_file(root, cap.get("eval_path"), f"{cid} eval_path")
            if expected_eval in eval_paths:
                reject(f"duplicate eval path: {expected_eval}")
            eval_paths.add(expected_eval)
            if "primary_skill" in cap:
                reject(f"{cid} skill must not declare primary_skill")

        elif kind == "reviewer":
            registered_reviewers.add(cid)
            expected_path = f"agents/{cid}.md"
            if raw_path != expected_path:
                reject(f"{cid} reviewer path must equal {expected_path}")
            primary = cap.get("primary_skill")
            if not isinstance(primary, str) or ID_RE.fullmatch(primary) is None:
                reject(f"{cid} reviewer primary_skill invalid")
            if "eval_path" in cap:
                raw_eval = _nonempty_string(cap.get("eval_path"), f"{cid} eval_path")
                _repo_file(root, raw_eval, f"{cid} eval_path")
                if raw_eval in eval_paths:
                    reject(f"duplicate eval path: {raw_eval}")
                eval_paths.add(raw_eval)

        else:
            if "primary_skill" in cap:
                reject(f"{cid} {kind} must not declare primary_skill")
            if "eval_path" in cap:
                raw_eval = _nonempty_string(cap.get("eval_path"), f"{cid} eval_path")
                _repo_file(root, raw_eval, f"{cid} eval_path")
                if raw_eval in eval_paths:
                    reject(f"duplicate eval path: {raw_eval}")
                eval_paths.add(raw_eval)

    disk_skills = {p.parent.name for p in (root / "skills").glob("*/SKILL.md")}
    if registered_skills != disk_skills:
        reject(
            "registered skills differ from disk skills: "
            f"registry={sorted(registered_skills)} disk={sorted(disk_skills)}"
        )

    disk_reviewers = {p.stem for p in (root / "agents").glob("*.md")}
    if registered_reviewers != disk_reviewers:
        reject(
            "registered reviewers differ from disk reviewers: "
            f"registry={sorted(registered_reviewers)} disk={sorted(disk_reviewers)}"
        )

    for cap in caps:
        if cap.get("kind") == "reviewer" and cap.get("primary_skill") not in registered_skills:
            reject(f"{cap['capability_id']} primary_skill not registered")


def main() -> None:
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        validate_registry(data)
    except (OSError, json.JSONDecodeError, RegistryError) as exc:
        raise SystemExit(f"CAPABILITY_REGISTRY_VALIDATION_FAIL: {exc}") from None
    print("PUBLIC_CAPABILITY_REGISTRY_VALIDATION_PASS")


if __name__ == "__main__":
    main()
