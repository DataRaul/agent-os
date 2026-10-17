"""Opt-in pre-build solution review, traceability and value checks.

Offline, repository-neutral and procedural: receipts cannot authenticate review
chronology, model identity or human approval. No authority is granted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


class PlanGateError(ValueError):
    pass


DIMENSIONS = (
    "problem_solution_fit", "alternatives", "architecture_tradeoffs",
    "complexity", "security_compliance", "cost", "failure_scenarios",
    "acceptance_criteria", "roadmap_alignment",
)
VERDICTS = {
    "VALUE_DEMONSTRATED", "VALUE_PARTIALLY_DEMONSTRATED",
    "VALUE_NOT_YET_MEASURED", "VALUE_NOT_DEMONSTRATED",
}
AUTHORITY = {"AUTO", "AUTO + VERIFY"}


def require(condition, message):
    if not condition:
        raise PlanGateError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def nonempty(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"missing {label}")


def string_list(value, label, minimum=0):
    require(isinstance(value, list) and len(value) >= minimum, f"invalid {label}")
    require(all(isinstance(x, str) and x.strip() for x in value), f"invalid {label}")
    require(len(value) == len(set(value)), f"duplicate {label}")


def safe_file(root, name):
    nonempty(name, "path")
    posix = PurePosixPath(name)
    require(not posix.is_absolute() and ".." not in posix.parts
            and "\\" not in name and str(posix) == name
            and posix.parts[0] != ".git", f"unsafe path: {name}")
    candidate = root
    for part in posix.parts:
        candidate = candidate / part
        require(not candidate.is_symlink(), f"symlink path: {name}")
    require(candidate.resolve().is_relative_to(root.resolve()), "path escapes root")
    return candidate


def load(root, name):
    p = safe_file(root, name)
    try:
        value = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PlanGateError(f"cannot load {name}: {exc}") from exc
    require(isinstance(value, dict) and value.get("schema_version") == 1,
            f"unsupported document: {name}")
    return value


def validate_roadmap(root, plan, contract=None):
    """Bind local roadmap and goal bytes; semantic priority judgment stays with reviewers."""
    entry = plan.get("roadmap_alignment")
    require(isinstance(entry, dict), "roadmap alignment required")
    for key in ("roadmap_path", "roadmap_sha256", "milestone_line",
                "goal_path", "goal_sha256", "steering_source",
                "priority_rationale", "goal_contribution", "value_signal"):
        nonempty(entry.get(key), "roadmap_alignment." + key)
    require(entry.get("status") == "ALIGNED", "roadmap alignment not accepted")
    require(entry.get("conflicts") == [], "unresolved roadmap priority conflict")
    for key in ("roadmap_sha256", "goal_sha256"):
        require(len(entry[key]) == 64 and all(c in "0123456789abcdef" for c in entry[key]),
                "invalid roadmap/goal digest")
    roadmap_path = safe_file(root, entry["roadmap_path"])
    goal_path = safe_file(root, entry["goal_path"])
    require(roadmap_path.is_file() and goal_path.is_file(), "roadmap or goal missing")
    roadmap_bytes, goal_bytes = roadmap_path.read_bytes(), goal_path.read_bytes()
    require(hashlib.sha256(roadmap_bytes).hexdigest() == entry["roadmap_sha256"],
            "roadmap changed; renew alignment and solution review")
    require(hashlib.sha256(goal_bytes).hexdigest() == entry["goal_sha256"],
            "goal changed; renew alignment and solution review")
    try:
        lines = roadmap_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise PlanGateError("roadmap must be UTF-8") from exc
    require(entry["milestone_line"] in lines, "milestone not present verbatim in roadmap")
    goal = load(root, entry["goal_path"])
    ids = {row["id"] for row in goal.get("success_criteria", [])}
    string_list(entry.get("goal_criteria"), "roadmap goal criteria", 1)
    require(set(entry["goal_criteria"]) <= ids, "roadmap goal criteria not in versioned goal")
    if contract is not None:
        require(entry["goal_path"] == contract["goal_path"], "roadmap goal path differs from contract")
        require(entry["roadmap_path"] in contract["required_evidence"],
                "roadmap must be frozen required evidence")
    return {"roadmap_digest": entry["roadmap_sha256"], "goal_digest": entry["goal_sha256"]}


def accepted_receipt(plan, review):
    """Validate the proposed decision and its same-chat review before building."""
    require(plan.get("schema_version") == 1, "invalid plan version")
    require(type(plan.get("revision")) is int and plan["revision"] >= 1,
            "versioned plan revision required")
    for key in ("plan_id", "problem", "affected_users", "root_cause",
                "desired_outcome", "expected_value", "selected_option_id",
                "architecture", "tradeoffs", "estimated_cost", "authority"):
        nonempty(plan.get(key), "plan." + key)
    require(plan["authority"] in AUTHORITY, "plan requires human authority resolution")
    options = plan.get("options")
    require(isinstance(options, list) and len(options) >= 2, "at least two options required")
    ids = []
    for option in options:
        require(isinstance(option, dict), "invalid option")
        for key in ("id", "description", "pros", "cons"):
            nonempty(option.get(key), "option." + key)
        ids.append(option["id"])
    require(len(set(ids)) == len(ids) and plan["selected_option_id"] in ids,
            "duplicate or missing selected option")
    decisions = plan.get("decisions")
    require(isinstance(decisions, list) and bool(decisions), "plan decisions required")
    decision_ids = []
    for row in decisions:
        require(isinstance(row, dict), "invalid decision")
        for key in ("id", "decision", "rationale", "expected_consequences", "authority"):
            nonempty(row.get(key), "decision." + key)
        require(row["authority"] in AUTHORITY, "decision lacks delegated authority")
        require(type(row.get("material")) is bool, "decision materiality must be explicit")
        if row["material"]:
            nonempty(row.get("delegation_reference"), "material decision delegation")
        decision_ids.append(row["id"])
    require(len(set(decision_ids)) == len(decision_ids), "duplicate plan decisions")
    string_list(plan.get("acceptance_criteria"), "acceptance criteria", 1)
    string_list(plan.get("risks"), "risks")

    require(isinstance(review, dict) and review.get("schema_version") == 1,
            "invalid solution review")
    require(review.get("review_mode") == "SAME_CHAT_SEQUENTIAL"
            and review.get("independent") is False,
            "same-chat review cannot claim independent peer status")
    for key in ("session_id", "model", "rationale", "authority"):
        nonempty(review.get(key), "review." + key)
    require(review["authority"] == plan["authority"], "review authority mismatch")
    require(review.get("plan_digest") == digest(plan), "stale solution review")
    entry = plan.get("roadmap_alignment")
    require(isinstance(entry, dict), "plan missing roadmap alignment")
    require(review.get("roadmap_digest") == entry.get("roadmap_sha256"),
            "solution review missing roadmap identity")
    require(review.get("verdict") == "PLAN_ACCEPTED", "plan not accepted")
    dimensions = review.get("dimensions")
    require(isinstance(dimensions, dict) and set(DIMENSIONS) <= set(dimensions),
            "solution review dimensions incomplete")
    for key in DIMENSIONS:
        nonempty(dimensions[key], "review." + key)
    findings = review.get("findings")
    require(isinstance(findings, list), "plan findings must be a list")
    finding_ids = []
    for row in findings:
        require(isinstance(row, dict), "invalid plan finding")
        for key in ("id", "finding", "disposition"):
            nonempty(row.get(key), "finding." + key)
        require(row["disposition"] in ("RESOLVED", "DEFERRED"),
                "unresolved plan finding")
        if row.get("material", True):
            require(row["disposition"] == "RESOLVED", "material plan finding unresolved")
            nonempty(row.get("resolution"), "material finding resolution")
        finding_ids.append(row["id"])
    require(len(finding_ids) == len(set(finding_ids)), "duplicate plan findings")
    return {
        "schema_version": 1,
        "status": "PLAN_ACCEPTED",
        "plan_digest": digest(plan),
        "review_digest": digest(review),
        "roadmap_digest": entry["roadmap_sha256"],
        "goal_digest": entry["goal_sha256"],
        "authority": plan["authority"],
        "session_id": review["session_id"],
        "assurance": "PROCEDURAL_SELF_REPORTED_PREBUILD",
    }


def validate_binding(root, contract, adapter):
    """Opt-in from existing package contract; never silently activate."""
    mode = adapter.get("plan_first", "DISABLED")
    require(mode in ("DISABLED", "AVAILABLE", "REQUIRED"), "invalid plan-first adapter mode")
    if mode == "DISABLED":
        require("plan_first" not in contract, "plan-first contract not selected by adapter")
        return None
    if mode == "AVAILABLE" and "plan_first" not in contract:
        return None
    require(contract.get("review_mode") == "SAME_CHAT_SEQUENTIAL",
            "plan-first V1 requires selected same-chat mode")
    config = contract.get("plan_first")
    require(isinstance(config, dict), "plan-first paths required")
    paths = [config.get(key) for key in
             ("plan_path", "review_path", "receipt_path", "trace_path")]
    for name in paths:
        nonempty(name, "plan-first evidence path")
        safe_file(root, name)
    require(len(set(paths)) == 4, "duplicate plan-first evidence path")
    require(set(paths) <= set(contract["required_evidence"]),
            "plan-first files must be frozen required evidence")
    plan, review, receipt, trace = [load(root, name) for name in paths]
    roadmap = validate_roadmap(root, plan, contract)
    expected = accepted_receipt(plan, review)
    require(receipt.get("roadmap_digest") == roadmap["roadmap_digest"]
            and receipt.get("goal_digest") == roadmap["goal_digest"],
            "receipt roadmap/goal identity mismatch")
    require(receipt == expected, "missing or stale pre-build receipt")
    require(review["session_id"] == contract["author_session_id"],
            "solution review must identify actual same-chat author session")
    require(receipt["authority"] == contract["authority"],
            "plan authority differs from authorized package")
    for decision in plan["decisions"]:
        if decision["material"]:
            ref = decision["delegation_reference"]
            require(ref in contract["required_evidence"],
                    "material decision delegation must be frozen evidence")
            require(safe_file(root, ref).is_file(),
                    "material decision delegation evidence missing")
    require(trace.get("plan_digest") == receipt["plan_digest"],
            "implementation trace refers to a different plan")
    require(trace.get("material_deviations") == [],
            "material plan deviation requires re-planning and acceptance")
    rows = trace.get("decisions")
    require(isinstance(rows, list), "decision trace required")
    observed = []
    for row in rows:
        require(isinstance(row, dict), "invalid trace decision")
        nonempty(row.get("id"), "trace decision id")
        require(row.get("status") in ("IMPLEMENTED", "JUSTIFIED_NONMATERIAL_DEVIATION"),
                "unapproved or incomplete plan decision")
        string_list(row.get("evidence"), "decision evidence", 1)
        require(set(row["evidence"]) <= set(contract["required_evidence"]),
                "trace evidence not frozen in package")
        if row["status"] != "IMPLEMENTED":
            nonempty(row.get("rationale"), "non-material deviation rationale")
        observed.append(row["id"])
    expected_ids = {row["id"] for row in plan["decisions"]}
    require(len(observed) == len(set(observed)) and set(observed) == expected_ids,
            "plan decision coverage incomplete or duplicate")
    return expected


def validate_value(synthesis, contract):
    """Require evidence-aware business reporting only in selected packages."""
    value = synthesis.get("business_value")
    require(isinstance(value, dict), "business value assessment missing")
    for key in ("problem", "solution", "observed_improvement", "executive_summary"):
        nonempty(value.get(key), "business_value." + key)
    require(value.get("verdict") in VERDICTS, "invalid business value verdict")
    for key in ("expected_but_unverified", "remaining_risks", "owner_actions"):
        string_list(value.get(key), "business_value." + key)
    string_list(value.get("acceptance_evidence"), "business acceptance evidence", 1)
    require(set(value["acceptance_evidence"]) <= set(contract["required_evidence"]),
            "business value cites unfrozen evidence")
    observations = value.get("observations")
    require(isinstance(observations, list), "observations must be a list")
    for row in observations:
        require(isinstance(row, dict), "invalid value observation")
        nonempty(row.get("metric"), "value metric")
        require(type(row.get("baseline")) in (float, int)
                and type(row.get("observed")) in (float, int),
                "numeric baseline and observed values required")
        string_list(row.get("evidence"), "observation evidence", 1)
        require(set(row["evidence"]) <= set(contract["required_evidence"]),
                "value observation has unbound evidence")
    if value["verdict"] in ("VALUE_DEMONSTRATED", "VALUE_PARTIALLY_DEMONSTRATED"):
        require(bool(observations), "demonstrated value needs measured observations")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--review", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        require(len({args.plan, args.review, args.output}) == 3,
                "plan, review and receipt must be separate files")
        plan = load(root, args.plan)
        validate_roadmap(root, plan)
        receipt = accepted_receipt(plan, load(root, args.review))
        output = safe_file(root, args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "PLAN_ACCEPTED_PREBUILD_ONLY",
                          "plan_digest": receipt["plan_digest"],
                          "assurance": receipt["assurance"]}))
    except (PlanGateError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "HOLD", "reason": str(exc)}))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
