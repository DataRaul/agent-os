from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ALLOWED_EVAL_LEVELS = {"easy", "normal", "deceptive", "control", "adversarial"}
REQUIRED_EVAL_LEVELS = {"easy", "normal", "deceptive", "control", "adversarial"}


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


def load_json(path: Path) -> object:
    if not path.is_file():
        fail(f"{path.relative_to(ROOT)} missing")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path.relative_to(ROOT)} invalid JSON: {exc}")


def validate_skills() -> set[str]:
    skills_dir = ROOT / "skills"
    if not skills_dir.is_dir():
        fail("skills/ directory missing")
    skill_files = sorted(skills_dir.glob("*/SKILL.md"))
    if not skill_files:
        fail("no skills found")

    names: set[str] = set()
    for path in skill_files:
        fields = parse_frontmatter(path)
        name = fields.get("name", "")
        description = fields.get("description", "")
        if not NAME_RE.fullmatch(name):
            fail(f"{path.relative_to(ROOT)} invalid name: {name!r}")
        if path.parent.name != name:
            fail(f"{path.relative_to(ROOT)} directory/name mismatch")
        if name in names:
            fail(f"duplicate skill name: {name}")
        if not description or len(description) > 1024:
            fail(f"{path.relative_to(ROOT)} invalid description")
        names.add(name)
    return names


def validate_evals(skill_names: set[str]) -> None:
    evals_dir = ROOT / "evals"
    if not evals_dir.is_dir():
        fail("evals/ directory missing")

    eval_dirs = {path.name for path in evals_dir.iterdir() if path.is_dir()}
    missing = skill_names - eval_dirs
    orphaned = eval_dirs - skill_names
    if missing:
        fail(f"skills missing eval corpus: {', '.join(sorted(missing))}")
    if orphaned:
        fail(f"eval corpus without matching skill: {', '.join(sorted(orphaned))}")

    for skill in sorted(skill_names):
        path = evals_dir / skill / "cases.json"
        data = load_json(path)
        if not isinstance(data, dict):
            fail(f"{path.relative_to(ROOT)} must contain a JSON object")
        if data.get("schema_version") != 1:
            fail(f"{path.relative_to(ROOT)} unsupported schema_version")
        if data.get("skill") != skill:
            fail(f"{path.relative_to(ROOT)} skill field must equal directory name")

        cases = data.get("cases")
        if not isinstance(cases, list) or not cases:
            fail(f"{path.relative_to(ROOT)} cases must be a non-empty array")

        ids: set[str] = set()
        levels: set[str] = set()
        for index, case in enumerate(cases):
            if not isinstance(case, dict):
                fail(f"{path.relative_to(ROOT)} case {index} must be an object")
            case_id = case.get("id")
            level = case.get("level")
            scenario = case.get("scenario")
            focus = case.get("expected_focus")
            if not isinstance(case_id, str) or not case_id:
                fail(f"{path.relative_to(ROOT)} case {index} missing id")
            if case_id in ids:
                fail(f"{path.relative_to(ROOT)} duplicate case id: {case_id}")
            ids.add(case_id)
            if level not in ALLOWED_EVAL_LEVELS:
                fail(f"{path.relative_to(ROOT)} case {case_id} invalid level: {level!r}")
            levels.add(level)
            if not isinstance(scenario, str) or not scenario.strip():
                fail(f"{path.relative_to(ROOT)} case {case_id} missing scenario")
            if (
                not isinstance(focus, list)
                or not focus
                or any(not isinstance(item, str) or not item.strip() for item in focus)
            ):
                fail(f"{path.relative_to(ROOT)} case {case_id} invalid expected_focus")

        missing_levels = REQUIRED_EVAL_LEVELS - levels
        if missing_levels:
            fail(
                f"{path.relative_to(ROOT)} missing eval levels: "
                + ", ".join(sorted(missing_levels))
            )


def validate_json() -> None:
    catalog_path = ROOT / "catalog" / "trusted-sources.json"
    schema_path = ROOT / "schemas" / "private-overlay-profile.schema.json"
    catalog = load_json(catalog_path)
    load_json(schema_path)

    if not isinstance(catalog, dict):
        fail("catalog/trusted-sources.json must contain a JSON object")
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
        "docs/P1_CAPABILITY_BASELINE.md",
        "agents/silent-failure-reviewer.md",
    ]
    for rel in paths:
        if not (ROOT / rel).is_file():
            fail(f"{rel} missing")


def main() -> None:
    validate_required_docs()
    skill_names = validate_skills()
    validate_evals(skill_names)
    validate_json()
    print("AGENT_OS_VALIDATION_PASS")


if __name__ == "__main__":
    main()
