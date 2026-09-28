from __future__ import annotations

import json
import re
from pathlib import Path

from build_tooling_priority_queue import build_priority_queue

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


def validate_vendor_audits(catalog: dict) -> None:
    allowed_catalog_states = {
        "REFERENCE_ONLY",
        "SKILL_ALLOWED",
        "PLUGIN_ALLOWED",
        "PIN_REQUIRED",
        "REJECTED",
    }
    allowed_audit_dispositions = {
        "KEEP_REFERENCE_ONLY",
        "ADMIT_SKILL",
        "ADMIT_PLUGIN",
        "PIN_REQUIRED",
        "REJECT",
    }

    source_ids: set[str] = set()
    for source in catalog.get("sources", []):
        source_id = source.get("id")
        if not isinstance(source_id, str) or not source_id:
            fail("catalog source missing id")
        if source_id in source_ids:
            fail(f"duplicate catalog source id: {source_id}")
        source_ids.add(source_id)

        state = source.get("admission_state")
        if state not in allowed_catalog_states:
            fail(f"catalog source {source_id} invalid admission_state: {state!r}")

        audit_rel = source.get("audit_record")
        if not audit_rel:
            continue
        if not isinstance(audit_rel, str) or not audit_rel.startswith("catalog/vendor-audits/"):
            fail(f"catalog source {source_id} invalid audit_record path")
        audit = load_json(ROOT / audit_rel)
        if not isinstance(audit, dict):
            fail(f"{audit_rel} must contain a JSON object")
        if audit.get("schema_version") != 1:
            fail(f"{audit_rel} unsupported schema_version")
        if audit.get("source_id") != source_id:
            fail(f"{audit_rel} source_id mismatch")
        if audit.get("admission_state_after_audit") != state:
            fail(f"{audit_rel} admission state does not match catalog")
        if audit.get("audit_disposition") not in allowed_audit_dispositions:
            fail(f"{audit_rel} invalid audit_disposition")

        candidate = audit.get("reviewed_candidate")
        if not isinstance(candidate, dict):
            fail(f"{audit_rel} missing reviewed_candidate")
        commit = candidate.get("commit")
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
            fail(f"{audit_rel} invalid reviewed commit")
        if source.get("reviewed_commit") != commit:
            fail(f"catalog source {source_id} reviewed_commit mismatch")

        access = audit.get("access_and_side_effects")
        if not isinstance(access, dict):
            fail(f"{audit_rel} missing access_and_side_effects")
        for key in (
            "local_filesystem_reads",
            "local_filesystem_writes",
            "network_access",
            "credential_handling",
        ):
            if not isinstance(access.get(key), bool):
                fail(f"{audit_rel} access field {key} must be boolean")

        subcaps = audit.get("reviewed_subcapabilities")
        if not isinstance(subcaps, list) or not subcaps:
            fail(f"{audit_rel} reviewed_subcapabilities must be non-empty")
        seen_subcaps: set[str] = set()
        for subcap in subcaps:
            if not isinstance(subcap, dict):
                fail(f"{audit_rel} subcapability must be an object")
            subcap_id = subcap.get("id")
            disposition = subcap.get("disposition")
            if not isinstance(subcap_id, str) or not subcap_id or subcap_id in seen_subcaps:
                fail(f"{audit_rel} invalid/duplicate subcapability id")
            seen_subcaps.add(subcap_id)
            if disposition not in allowed_catalog_states:
                fail(f"{audit_rel} subcapability {subcap_id} invalid disposition")


def validate_tooling_inventory(catalog: dict) -> None:
    path = ROOT / "catalog" / "tooling-inventory.json"
    data = load_json(path)
    if not isinstance(data, dict):
        fail("catalog/tooling-inventory.json must contain a JSON object")
    if data.get("schema_version") != 1:
        fail("catalog/tooling-inventory.json unsupported schema_version")

    sources = {
        source.get("id"): source
        for source in catalog.get("sources", [])
        if isinstance(source, dict) and isinstance(source.get("id"), str)
    }
    evidence = data.get("source_evidence")
    if not isinstance(evidence, dict) or set(evidence) != set(sources):
        fail("tooling inventory source_evidence must match catalog sources")

    for source_id, entry in evidence.items():
        if not isinstance(entry, dict):
            fail(f"tooling inventory source evidence {source_id} invalid")
        source = sources[source_id]
        if entry.get("admission_state") != source.get("admission_state"):
            fail(f"tooling inventory source {source_id} admission_state mismatch")
        if entry.get("reviewed_commit") != source.get("reviewed_commit"):
            fail(f"tooling inventory source {source_id} reviewed_commit mismatch")
        if entry.get("audit_record") != source.get("audit_record"):
            fail(f"tooling inventory source {source_id} audit_record mismatch")

    allowed_states = {
        "REFERENCE_ONLY",
        "SKILL_ALLOWED",
        "PLUGIN_ALLOWED",
        "PIN_REQUIRED",
        "REJECTED",
    }

    marketplace = data.get("marketplace_plugins")
    if not isinstance(marketplace, list) or not marketplace:
        fail("tooling inventory marketplace_plugins must be non-empty")
    marketplace_ids: set[str] = set()
    external_count = 0
    mcp_count = 0
    script_count = 0
    for item in marketplace:
        if not isinstance(item, dict):
            fail("tooling inventory marketplace item must be object")
        cap_id = item.get("capability_id")
        if not isinstance(cap_id, str) or not cap_id or cap_id in marketplace_ids:
            fail("tooling inventory marketplace capability id invalid/duplicate")
        marketplace_ids.add(cap_id)
        if item.get("source_id") != "openai-plugins":
            fail(f"tooling inventory marketplace item {cap_id} wrong source")
        if item.get("admission_state") != "REFERENCE_ONLY":
            fail(f"tooling inventory marketplace item {cap_id} must fail closed")
        if item.get("inventory_state") != "DISCOVERED_NOT_NARROW_AUDITED":
            fail(f"tooling inventory marketplace item {cap_id} invalid inventory_state")
        source = item.get("marketplace_source")
        if not isinstance(source, dict) or not source.get("source"):
            fail(f"tooling inventory marketplace item {cap_id} missing source")
        signals = item.get("structural_signals")
        if not isinstance(signals, dict):
            fail(f"tooling inventory marketplace item {cap_id} missing structural_signals")
        authority = item.get("authority_surface")
        if not isinstance(authority, dict):
            fail(f"tooling inventory marketplace item {cap_id} missing authority_surface")
        for key in ("remote_write_scope", "destructive_scope", "publish_scope", "credential_scope"):
            if authority.get(key) != "UNKNOWN_UNTIL_NARROW_AUDIT":
                fail(f"tooling inventory marketplace item {cap_id} must fail closed on {key}")
        flags = item.get("risk_flags")
        if not isinstance(flags, list) or any(not isinstance(flag, str) for flag in flags):
            fail(f"tooling inventory marketplace item {cap_id} invalid risk_flags")
        if source.get("source") != "local":
            external_count += 1
            if "EXTERNAL_REPOSITORY_SOURCE" not in flags:
                fail(f"tooling inventory external marketplace item {cap_id} missing provenance flag")
        if signals.get("mcp_manifest_present") is True:
            mcp_count += 1
        if signals.get("scripts_present") is True:
            script_count += 1

    subcaps = data.get("audited_subcapabilities")
    if not isinstance(subcaps, list) or not subcaps:
        fail("tooling inventory audited_subcapabilities must be non-empty")
    subcap_ids: set[str] = set()
    for item in subcaps:
        if not isinstance(item, dict):
            fail("tooling inventory audited subcapability must be object")
        cap_id = item.get("capability_id")
        source_id = item.get("source_id")
        if not isinstance(cap_id, str) or not cap_id or cap_id in subcap_ids:
            fail("tooling inventory audited capability id invalid/duplicate")
        subcap_ids.add(cap_id)
        if source_id not in sources:
            fail(f"tooling inventory audited capability {cap_id} unknown source")
        if item.get("admission_state") not in allowed_states:
            fail(f"tooling inventory audited capability {cap_id} invalid admission_state")
        if item.get("inventory_state") != "SOURCE_AUDITED":
            fail(f"tooling inventory audited capability {cap_id} invalid inventory_state")

    summary = data.get("summary")
    if not isinstance(summary, dict):
        fail("tooling inventory summary missing")
    expected_summary = {
        "catalog_sources": len(sources),
        "openai_marketplace_plugins": len(marketplace),
        "openai_marketplace_external_sources": external_count,
        "openai_marketplace_mcp_surfaces": mcp_count,
        "openai_marketplace_plugins_with_scripts": script_count,
        "audited_source_subcapabilities": len(subcaps),
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            fail(f"tooling inventory summary {key} mismatch")



def validate_tooling_priority_queue() -> None:
    inventory = load_json(ROOT / "catalog" / "tooling-inventory.json")
    queue = load_json(ROOT / "catalog" / "tooling-priority-queue.json")
    if not isinstance(inventory, dict):
        fail("tooling inventory must contain an object")
    if not isinstance(queue, dict):
        fail("catalog/tooling-priority-queue.json must contain a JSON object")
    if queue.get("schema_version") != 1:
        fail("catalog/tooling-priority-queue.json unsupported schema_version")

    expected = build_priority_queue(inventory)
    if queue != expected:
        fail("tooling priority queue does not match deterministic builder")

    candidates = queue.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        fail("tooling priority queue candidates must be non-empty")
    ids: list[str] = []
    for position, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, dict):
            fail("tooling priority queue candidate must be object")
        cap_id = candidate.get("capability_id")
        if not isinstance(cap_id, str) or not cap_id:
            fail("tooling priority queue candidate missing capability_id")
        ids.append(cap_id)
        if candidate.get("position") != position:
            fail(f"tooling priority queue candidate {cap_id} position mismatch")
        if candidate.get("priority_group") not in {1, 2, 3}:
            fail(f"tooling priority queue candidate {cap_id} outside initial allowed groups")
        if candidate.get("admission_state") != "REFERENCE_ONLY":
            fail(f"tooling priority queue candidate {cap_id} must remain reference-only")
        if candidate.get("audit_action") != "P4_2_NARROW_AUDIT":
            fail(f"tooling priority queue candidate {cap_id} wrong audit action")
    if len(ids) != len(set(ids)):
        fail("tooling priority queue contains duplicate candidates")

def validate_p4_narrow_audits() -> None:
    audit_path = ROOT / "catalog" / "p4-narrow-audits.json"
    cases_path = ROOT / "catalog" / "p4-narrow-audit-cases.json"
    audits = load_json(audit_path)
    cases_doc = load_json(cases_path)
    queue = load_json(ROOT / "catalog" / "tooling-priority-queue.json")

    if not isinstance(audits, dict) or audits.get("schema_version") != 1:
        fail("catalog/p4-narrow-audits.json invalid")
    if audits.get("status") != "P4_2_NARROW_AUDITS_COMPLETE":
        fail("P4.2 narrow audit status invalid")
    rules = audits.get("rules")
    if not isinstance(rules, dict):
        fail("P4.2 narrow audit rules missing")
    for key in (
        "no_installation",
        "no_authentication",
        "no_external_mutation",
        "no_paid_infrastructure_change",
        "audit_does_not_grant_authority",
        "registry_promotion_requires_later_gate",
    ):
        if rules.get(key) is not True:
            fail(f"P4.2 narrow audit rule {key} must be true")

    audit_items = audits.get("audits")
    if not isinstance(audit_items, list) or not audit_items:
        fail("P4.2 narrow audits must be non-empty")
    queue_candidates = queue.get("candidates")
    if not isinstance(queue_candidates, list):
        fail("P4 tooling queue candidates invalid during narrow-audit validation")
    queue_ids = [item.get("capability_id") for item in queue_candidates if isinstance(item, dict)]
    audit_ids = [item.get("capability_id") for item in audit_items if isinstance(item, dict)]
    if audit_ids != queue_ids:
        fail("P4.2 narrow audit capability order must exactly match bounded queue")
    if len(audit_ids) != len(set(audit_ids)):
        fail("P4.2 narrow audit capability IDs must be unique")

    allowed_dispositions = {"REFERENCE_ONLY", "SKILL_ALLOWED", "PLUGIN_ALLOWED", "PIN_REQUIRED", "REJECTED"}
    referenced_case_ids: set[str] = set()
    for item in audit_items:
        if not isinstance(item, dict):
            fail("P4.2 narrow audit entry must be object")
        cap_id = item.get("capability_id")
        commit = item.get("reviewed_commit")
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
            fail(f"P4.2 audit {cap_id} reviewed_commit invalid")
        if item.get("disposition") not in allowed_dispositions:
            fail(f"P4.2 audit {cap_id} invalid disposition")
        paths = item.get("reviewed_paths")
        if not isinstance(paths, list) or not paths:
            fail(f"P4.2 audit {cap_id} reviewed_paths missing")
        for source_path in paths:
            if (
                not isinstance(source_path, dict)
                or not isinstance(source_path.get("path"), str)
                or not source_path.get("path")
                or not isinstance(source_path.get("blob_sha"), str)
                or not re.fullmatch(r"[0-9a-f]{40}", source_path["blob_sha"])
            ):
                fail(f"P4.2 audit {cap_id} reviewed path invalid")
        case_ids = item.get("public_safe_eval_case_ids")
        if (
            not isinstance(case_ids, list)
            or not case_ids
            or any(not isinstance(case_id, str) or not case_id for case_id in case_ids)
        ):
            fail(f"P4.2 audit {cap_id} public_safe_eval_case_ids invalid")
        for case_id in case_ids:
            if case_id in referenced_case_ids:
                fail(f"P4.2 eval case {case_id} referenced more than once")
            referenced_case_ids.add(case_id)

    if not isinstance(cases_doc, dict) or cases_doc.get("schema_version") != 1:
        fail("P4.2 eval cases invalid")
    if cases_doc.get("suite") != "p4-narrow-audit-public-safe-cases":
        fail("P4.2 eval suite invalid")
    classes = cases_doc.get("case_classes")
    if set(classes or []) != {"easy", "normal", "deceptive", "control", "adversarial"}:
        fail("P4.2 eval case_classes must contain the full public-safe class set")
    cases = cases_doc.get("cases")
    if not isinstance(cases, list) or not cases:
        fail("P4.2 eval cases must be non-empty")
    actual_case_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            fail("P4.2 eval case must be object")
        case_id = case.get("id")
        cap_id = case.get("capability_id")
        level = case.get("class")
        if not isinstance(case_id, str) or not case_id or case_id in actual_case_ids:
            fail("P4.2 eval case id invalid or duplicate")
        actual_case_ids.add(case_id)
        if cap_id not in audit_ids:
            fail(f"P4.2 eval case {case_id} references unknown capability")
        if level not in {"easy", "normal", "deceptive", "control", "adversarial"}:
            fail(f"P4.2 eval case {case_id} invalid class")
        if not isinstance(case.get("scenario"), str) or not case["scenario"].strip():
            fail(f"P4.2 eval case {case_id} missing scenario")
        if not isinstance(case.get("expected"), str) or not case["expected"].strip():
            fail(f"P4.2 eval case {case_id} missing expected result")
    if actual_case_ids != referenced_case_ids:
        fail("P4.2 eval cases must exactly match audit references")


def validate_json() -> None:
    catalog_path = ROOT / "catalog" / "trusted-sources.json"
    schema_path = ROOT / "schemas" / "private-overlay-profile.schema.json"
    catalog = load_json(catalog_path)
    load_json(schema_path)

    if not isinstance(catalog, dict):
        fail("catalog/trusted-sources.json must contain a JSON object")
    validate_vendor_audits(catalog)
    validate_tooling_inventory(catalog)
    validate_tooling_priority_queue()
    validate_p4_narrow_audits()
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
        "docs/VENDOR_CAPABILITY_ADMISSION.md",
        "docs/P1_CAPABILITY_BASELINE.md",
        "docs/SPECIALIST_REVIEWER_EVALUATION.md",
        "docs/P4_NARROW_AUDITS.md",
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
