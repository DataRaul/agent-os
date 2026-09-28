from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def fail(message: str) -> None:
    raise SystemExit(f"VALIDATION_FAIL: {message}")


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail(f"{path.relative_to(ROOT)} missing YAML frontmatter")
    try:
        _, block, _ = text.split("---", 2)
    except ValueError:
        fail(f"{path.relative_to(ROOT)} malformed YAML frontmatter")
    fields: dict[str, str] = {}
    for raw in block.strip().splitlines():
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def validate_skills() -> None:
    skills_dir = ROOT / "skills"
    if not skills_dir.is_dir():
        fail("skills/ directory missing")
    skill_files = sorted(skills_dir.glob("*/SKILL.md"))
    if not skill_files:
        fail("no skills found")
    for path in skill_files:
        fields = parse_frontmatter(path)
        name = fields.get("name", "")
        description = fields.get("description", "")
        if not NAME_RE.fullmatch(name):
            fail(f"{path.relative_to(ROOT)} invalid name: {name!r}")
        if path.parent.name != name:
            fail(f"{path.relative_to(ROOT)} directory/name mismatch")
        if not description or len(description) > 1024:
            fail(f"{path.relative_to(ROOT)} invalid description")


def validate_json() -> None:
    required = [
        ROOT / "catalog" / "trusted-sources.json",
        ROOT / "evals" / "silent-failure-hunter" / "cases.json",
        ROOT / "schemas" / "private-overlay-profile.schema.json",
    ]
    for path in required:
        if not path.is_file():
            fail(f"{path.relative_to(ROOT)} missing")
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(f"{path.relative_to(ROOT)} invalid JSON: {exc}")

    catalog = json.loads(required[0].read_text(encoding="utf-8"))
    for source in catalog.get("sources", []):
        for key in ("id", "owner", "canonical_url", "trust_tier", "admission_state", "purpose"):
            if not source.get(key):
                fail(f"catalog source missing {key}")
        if not source["canonical_url"].startswith("https://"):
            fail(f"catalog source URL must be https: {source['id']}")


def validate_required_docs() -> None:
    paths = [
        "README.md",
        "AGENTS.md",
        "docs/ARCHITECTURE.md",
        "docs/PRIVATE_OVERLAY_CONTRACT.md",
        "docs/COMPLEXITY_ROUTING.md",
        "docs/TRUST_MODEL.md",
        "agents/silent-failure-reviewer.md",
    ]
    for rel in paths:
        if not (ROOT / rel).is_file():
            fail(f"{rel} missing")


def main() -> None:
    validate_required_docs()
    validate_skills()
    validate_json()
    print("AGENT_OS_VALIDATION_PASS")


if __name__ == "__main__":
    main()
