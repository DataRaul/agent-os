from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "catalog" / "capability-registry.json"

def fail(message: str) -> None:
    raise SystemExit(f"CAPABILITY_REGISTRY_VALIDATION_FAIL: {message}")

def main() -> None:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("registry_version") != 1:
        fail("unsupported registry version")
    caps = data.get("capabilities")
    if not isinstance(caps, list) or not caps:
        fail("capabilities must be non-empty")
    ids: set[str] = set()
    registered_skills: set[str] = set()
    for cap in caps:
        if not isinstance(cap, dict):
            fail("capability must be object")
        cid = cap.get("capability_id")
        if not isinstance(cid, str) or not cid or cid in ids:
            fail(f"invalid or duplicate capability_id: {cid!r}")
        ids.add(cid)
        if cap.get("grants_authority") is not False:
            fail(f"{cid} must not grant authority")
        path = ROOT / str(cap.get("path", ""))
        if not path.is_file():
            fail(f"{cid} path missing: {path.relative_to(ROOT)}")
        if cap.get("kind") == "skill":
            registered_skills.add(cid)
            eval_path = ROOT / str(cap.get("eval_path", ""))
            if not eval_path.is_file():
                fail(f"{cid} eval path missing")
        if cap.get("kind") == "reviewer":
            primary = cap.get("primary_skill")
            if primary not in ids and primary not in registered_skills:
                # final cross-check below allows registry order changes
                pass
    disk_skills = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
    if registered_skills != disk_skills:
        fail(f"registered skills differ from disk skills: registry={sorted(registered_skills)} disk={sorted(disk_skills)}")
    for cap in caps:
        if cap.get("kind") == "reviewer" and cap.get("primary_skill") not in registered_skills:
            fail(f"{cap['capability_id']} primary_skill not registered")
    print("PUBLIC_CAPABILITY_REGISTRY_VALIDATION_PASS")

if __name__ == "__main__":
    main()
