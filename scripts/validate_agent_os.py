from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ALLOWED_EVAL_LEVELS = {"easy", "normal", "deceptive", "control", "adversarial"}
REQUIRED_EVAL_LEVELS = {"easy", "normal", "deceptive", "control", "adversarial"}
SPECIALIST_REVIEWER_CANDIDATES = {
    "research-validity-reviewer",
    "evidence-provenance-reviewer",
    "runtime-postcondition-verifier",
}


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


def validate_python_scripts() -> None:
    for path in sorted((ROOT / "scripts").glob("*.py")):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            fail(f"{path.relative_to(ROOT)} syntax error: {exc}")


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


def validate_specialist_reviewer_benchmark(skill_names: set[str]) -> None:
    base = ROOT / "benchmarks" / "specialist-reviewer-evaluation"
    cases_path = base / "cases.json"
    oracle_path = base / "oracle.json"
    cases_doc = load_json(cases_path)
    oracle = load_json(oracle_path)

    for path, data in ((cases_path, cases_doc), (oracle_path, oracle)):
        if not isinstance(data, dict):
            fail(f"{path.relative_to(ROOT)} must contain a JSON object")
        if data.get("schema_version") != 1:
            fail(f"{path.relative_to(ROOT)} unsupported schema_version")
        if data.get("suite") != "specialist-reviewer-evaluation":
            fail(f"{path.relative_to(ROOT)} wrong suite")

    taxonomy = cases_doc.get("finding_code_taxonomy")
    if (
        not isinstance(taxonomy, list)
        or not taxonomy
        or len(taxonomy) != len(set(taxonomy))
        or any(not isinstance(code, str) or not code for code in taxonomy)
    ):
        fail(f"{cases_path.relative_to(ROOT)} invalid finding_code_taxonomy")
    taxonomy_set = set(taxonomy)

    candidates = cases_doc.get("candidates")
    if not isinstance(candidates, dict) or set(candidates) != SPECIALIST_REVIEWER_CANDIDATES:
        fail(f"{cases_path.relative_to(ROOT)} candidate set mismatch")
    for candidate, config in candidates.items():
        if not isinstance(config, dict):
            fail(f"{cases_path.relative_to(ROOT)} candidate {candidate} config invalid")
        skills = config.get("baseline_skills")
        if (
            not isinstance(skills, list)
            or not skills
            or any(skill not in skill_names for skill in skills)
        ):
            fail(f"{cases_path.relative_to(ROOT)} candidate {candidate} baseline skills invalid")

    cases = cases_doc.get("cases")
    if not isinstance(cases, list) or not cases:
        fail(f"{cases_path.relative_to(ROOT)} cases must be non-empty")
    ids: set[str] = set()
    levels_by_candidate: dict[str, set[str]] = {
        candidate: set() for candidate in SPECIALIST_REVIEWER_CANDIDATES
    }
    cases_by_candidate: dict[str, int] = {
        candidate: 0 for candidate in SPECIALIST_REVIEWER_CANDIDATES
    }
    for case in cases:
        if not isinstance(case, dict):
            fail(f"{cases_path.relative_to(ROOT)} case must be object")
        case_id = case.get("id")
        candidate = case.get("reviewer_candidate")
        level = case.get("level")
        scenario = case.get("scenario")
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            fail(f"{cases_path.relative_to(ROOT)} invalid/duplicate case id: {case_id!r}")
        ids.add(case_id)
        if candidate not in SPECIALIST_REVIEWER_CANDIDATES:
            fail(f"{cases_path.relative_to(ROOT)} case {case_id} invalid candidate")
        if level not in ALLOWED_EVAL_LEVELS:
            fail(f"{cases_path.relative_to(ROOT)} case {case_id} invalid level")
        if not isinstance(scenario, str) or not scenario.strip():
            fail(f"{cases_path.relative_to(ROOT)} case {case_id} missing scenario")
        levels_by_candidate[candidate].add(level)
        cases_by_candidate[candidate] += 1

    for candidate in SPECIALIST_REVIEWER_CANDIDATES:
        if levels_by_candidate[candidate] != REQUIRED_EVAL_LEVELS:
            fail(f"reviewer benchmark {candidate} must cover all eval levels")
        if cases_by_candidate[candidate] != 5:
            fail(f"reviewer benchmark {candidate} must contain exactly five cases")

    expected = oracle.get("expected")
    if not isinstance(expected, dict) or set(expected) != ids:
        fail(f"{oracle_path.relative_to(ROOT)} expected IDs must match benchmark cases")
    for case_id, codes in expected.items():
        if (
            not isinstance(codes, list)
            or len(codes) != len(set(codes))
            or any(code not in taxonomy_set for code in codes)
        ):
            fail(f"{oracle_path.relative_to(ROOT)} invalid expected codes for {case_id}")

    reps = oracle.get("replicates_per_case")
    if not isinstance(reps, int) or isinstance(reps, bool) or reps != 3:
        fail(f"{oracle_path.relative_to(ROOT)} replicates_per_case must equal 3")

    policy = oracle.get("admission_policy")
    required_policy = (
        "minimum_incremental_distinct_cases",
        "minimum_incremental_expected_observations",
        "minimum_combined_expected_recall",
        "maximum_reviewer_false_positive_observations",
        "require_control_false_positive_free",
        "eligible_disposition",
        "noneligible_disposition",
    )
    if not isinstance(policy, dict) or any(key not in policy for key in required_policy):
        fail(f"{oracle_path.relative_to(ROOT)} admission_policy incomplete")
    min_recall = policy.get("minimum_combined_expected_recall")
    if (
        not isinstance(min_recall, (int, float))
        or isinstance(min_recall, bool)
        or not 0 <= min_recall <= 1
    ):
        fail(f"{oracle_path.relative_to(ROOT)} minimum_combined_expected_recall invalid")


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
        "docs/SPECIALIST_REVIEWER_EVALUATION.md",
        "agents/silent-failure-reviewer.md",
        "scripts/score_specialist_reviewer_eval.py",
    ]
    for rel in paths:
        if not (ROOT / rel).is_file():
            fail(f"{rel} missing")


def main() -> None:
    validate_required_docs()
    validate_python_scripts()
    skill_names = validate_skills()
    validate_evals(skill_names)
    validate_specialist_reviewer_benchmark(skill_names)
    validate_json()
    print("AGENT_OS_VALIDATION_PASS")


if __name__ == "__main__":
    main()
