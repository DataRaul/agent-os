from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GROUP_NAMES = {
    1: "SPECIFICATION_OR_REFERENCE_HELPER",
    2: "LOCAL_DETERMINISTIC_ANALYSIS",
    3: "ISOLATED_READ_ONLY_OBSERVATION",
    4: "AUTHENTICATED_OR_SENSITIVE_READ",
    5: "WRITE_EXECUTION_OR_INSTALL",
    6: "DESTRUCTIVE_PUBLISH_SEND_FINANCIAL_OR_ADMIN",
}

GROUP_6_FLAGS = {
    "DELETE",
    "REMOTE_DELETE",
    "PUBLICATION",
    "MESSAGE_SEND",
    "EMAIL_SEND",
    "FINANCIAL_DATA",
    "COMMERCE",
    "CONSEQUENTIAL_DOMAIN",
    "SECURITY_POLICY",
    "NETWORK_CONFIGURATION",
    "MARKETPLACE_MUTATION",
    "INFRA_MUTATION",
}

GROUP_5_FLAGS = {
    "REMOTE_MUTATION",
    "REMOTE_WRITE",
    "WRITE",
    "READ_WRITE",
    "SOURCE_CONTROL_WRITE",
    "REMOTE_CREATE",
    "DEPLOYMENT",
    "CODE_WRITE",
    "TEST_MUTATION",
    "FORM_SUBMISSION",
    "FILE_UPLOAD",
    "COOKIE_WRITE",
    "COOKIE_DELETE",
    "BROWSER_STATE_MUTATION",
    "ARBITRARY_CODE",
    "LOCAL_EXECUTION",
    "SCRIPT_EXECUTION",
    "EXECUTABLE_SCRIPTS",
    "SOFTWARE_INSTALL",
    "SOFTWARE_UPDATE",
    "GLOBAL_INSTALL",
    "UPSTREAM_SKILL_INSTALL",
    "PLUGIN_INSTALL",
    "SKILL_INSTALL",
    "DEPENDENCY_FETCH",
    "HOME_DIRECTORY_WRITE",
    "POTENTIAL_DATABASE_CREATE",
    "EXTENSION_INSTALL",
    "EXTENSION_INSTALL_OPTIONAL",
    "COMMUNITY_EXTENSION",
    "COMMUNITY_EXTENSION_OPTIONAL",
    "MCP_INSTALL_OPTION",
    "TOOL_PREAPPROVAL",
    "SUPPLY_CHAIN",
    "EXTERNAL_REPOSITORY",
    "MIXED_PROVENANCE",
    "NPM",
    "NPX",
    "SHELL",
}

GROUP_4_FLAGS = {
    "OAUTH",
    "AUTHENTICATION",
    "REMOTE_ACCOUNT",
    "API_TOKEN",
    "API_KEYS",
    "SECRETS",
    "SECRET_HANDLING",
    "SECRET_CONFIGURATION",
    "CREDENTIALS",
    "CREDENTIAL_CHAIN",
    "CREDENTIAL_CHAIN_OPTIONAL",
    "EXPLICIT_SECRET_OPTION",
    "AUTH_STATE",
    "PRIVACY_BOUNDARY",
    "PERSONAL_DATA",
    "POTENTIAL_SECRET_REUSE",
    "LOCAL_SESSION_HISTORY_READ",
    "PERSISTENT_PROFILE",
    "EXISTING_BROWSER_ACCESS",
}

GROUP_3_FLAGS = {
    "NETWORK",
    "NETWORK_OPTIONAL",
    "REMOTE_STORAGE",
    "PAGE_CONTENT_READ",
    "SCREENSHOT",
    "SCREEN_CAPTURE",
    "BROWSER_TOOLING",
    "MCP",
    "CDP",
    "NETWORK_INTERCEPTION",
    "UNTRUSTED_PAGE_TOOLING",
}

GROUP_1_FLAGS = {"FORMAT_REFERENCE", "REFERENCE_IMPLEMENTATION"}

INITIAL_QUEUE_GROUPS = (1, 2, 3)
MAX_INITIAL_QUEUE_SIZE = 5


def classify_priority_group(risk_flags: list[str]) -> int:
    flags = set(risk_flags)
    if flags & GROUP_6_FLAGS:
        return 6
    if flags & GROUP_5_FLAGS:
        return 5
    if flags & GROUP_4_FLAGS:
        return 4
    if flags & GROUP_3_FLAGS:
        return 3
    if flags & GROUP_1_FLAGS:
        return 1
    if flags & {"LOCAL_READ", "BASH", "CLI"}:
        return 2
    return 5


def build_priority_queue(inventory: dict) -> dict:
    audited = inventory.get("audited_subcapabilities", [])
    marketplace = inventory.get("marketplace_plugins", [])
    if not isinstance(audited, list) or not isinstance(marketplace, list):
        raise ValueError("tooling inventory candidate arrays are invalid")

    buckets: dict[str, list[dict]] = {str(group): [] for group in range(1, 7)}
    for item in audited:
        if not isinstance(item, dict):
            raise ValueError("audited subcapability must be an object")
        risk_flags = item.get("risk_flags", [])
        if not isinstance(risk_flags, list) or any(not isinstance(flag, str) for flag in risk_flags):
            raise ValueError("audited subcapability risk_flags must be strings")
        group = classify_priority_group(risk_flags)
        buckets[str(group)].append(item)

    for items in buckets.values():
        items.sort(key=lambda item: item["capability_id"])

    candidates: list[dict] = []
    for group in INITIAL_QUEUE_GROUPS:
        for item in buckets[str(group)]:
            if len(candidates) >= MAX_INITIAL_QUEUE_SIZE:
                break
            candidates.append(
                {
                    "position": len(candidates) + 1,
                    "capability_id": item["capability_id"],
                    "source_id": item["source_id"],
                    "priority_group": group,
                    "priority_class": GROUP_NAMES[group],
                    "risk_flags": item["risk_flags"],
                    "admission_state": item["admission_state"],
                    "inventory_state": item["inventory_state"],
                    "audit_action": "P4_2_NARROW_AUDIT",
                }
            )

    return {
        "schema_version": 1,
        "inventory_snapshot_date": inventory.get("snapshot_date"),
        "purpose": "Deterministic P4.1 queue for selecting the lowest-authority source-audited capabilities for narrow P4.2 evaluation.",
        "rules": {
            "marketplace_unknown_authority_deferred": True,
            "source_audited_only_for_initial_queue": True,
            "priority_order": [1, 2, 3, 4, 5, 6],
            "initial_queue_allowed_groups": [1, 2, 3],
            "maximum_initial_queue_size": MAX_INITIAL_QUEUE_SIZE,
            "deterministic_sort": ["priority_group", "capability_id"],
            "no_admission_granted_by_prioritization": True,
        },
        "summary": {
            "audited_candidates_classified": len(audited),
            "marketplace_candidates_deferred_unknown_authority": len(marketplace),
            "priority_group_counts": {
                group: len(items) for group, items in buckets.items()
            },
            "initial_queue_count": len(candidates),
        },
        "candidates": candidates,
        "classified_priority_groups": {
            group: [item["capability_id"] for item in items]
            for group, items in buckets.items()
        },
    }


def main() -> None:
    inventory = json.loads((ROOT / "catalog" / "tooling-inventory.json").read_text(encoding="utf-8"))
    print(json.dumps(build_priority_queue(inventory), indent=2) + "\n")


if __name__ == "__main__":
    main()
