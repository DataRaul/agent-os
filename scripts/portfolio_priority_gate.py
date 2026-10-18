"""Portable, prospective portfolio/lane/value gate. No network, runtime writes or agent launch.

This is an evidence contract, not a semantic oracle or proof of owner approval.
Integrate prospectively through a consumer's pinned adapter; never rewrite frozen reviews.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


class PortfolioGateError(ValueError):
    pass


def require(value, message):
    if not value:
        raise PortfolioGateError(message)


def safe_file(root, value):
    require(isinstance(value, str) and bool(value.strip()), "relative file path required")
    name = PurePosixPath(value)
    require(not name.is_absolute() and ".." not in name.parts and
            str(name) == value and "\\" not in value and name.parts[0] != ".git",
            "unsafe file path")
    path = (root / value).resolve()
    require(path.is_relative_to(root) and path.is_file(), "file missing or escapes project")
    return path


def read_object(root, name):
    path = safe_file(root, name)
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PortfolioGateError("invalid JSON evidence") from exc
    require(isinstance(obj, dict) and obj.get("schema_version") == 1,
            "schema_version 1 object required")
    return obj, hashlib.sha256(path.read_bytes()).hexdigest()


def populated(obj, fields, scope):
    require(isinstance(obj, dict), scope + " object required")
    for field in fields:
        require(isinstance(obj.get(field), str) and bool(obj[field].strip()),
                scope + "." + field + " required")


def validate(root, policy_path, decision_path):
    """Check a consumer's frozen priority policy and one decision/continuation receipt."""
    root = Path(root).resolve()
    policy, policy_sha = read_object(root, policy_path)
    decision, decision_sha = read_object(root, decision_path)
    populated(policy, ("roadmap_path", "primary_lane", "owner_steering_source"), "policy")
    roadmap = safe_file(root, policy["roadmap_path"])
    require(policy.get("roadmap_sha256") ==
            hashlib.sha256(roadmap.read_bytes()).hexdigest(), "stale roadmap policy pin")
    lanes = policy.get("lanes")
    require(isinstance(lanes, dict) and len(lanes) >= 2, "two or more configured lanes required")
    main = policy["primary_lane"]
    require(main in lanes, "primary lane unregistered")
    for lane, spec in lanes.items():
        populated(spec, ("priority", "branch_policy"), "lane")
        require(spec["priority"] in ("P0", "P1", "P2"), "invalid lane priority")
        require(spec["branch_policy"] in ("MAIN_DELIVERY", "ISOLATED"), "invalid lane routing")
        if lane != main:
            require(spec["branch_policy"] == "ISOLATED", "nonprimary lane must be isolated")
    require(lanes[main]["priority"] == "P0" and
            lanes[main]["branch_policy"] == "MAIN_DELIVERY",
            "configured primary lane must remain P0")
    limit = policy.get("limits")
    require(isinstance(limit, dict), "limits required")
    for key in ("unchanged_blocker_checks", "cycles_without_value"):
        require(type(limit.get(key)) is int and limit[key] >= 0, "invalid " + key)
    populated(decision, ("lane_id", "milestone_line", "business_metric",
                         "next_primary_action", "route", "owner_steering_source"), "decision")
    require(decision.get("roadmap_sha256") == policy["roadmap_sha256"],
            "decision has stale roadmap")
    require(decision["milestone_line"] in roadmap.read_text(encoding="utf-8").splitlines(),
            "decision milestone missing from roadmap")
    require(decision["owner_steering_source"] == policy["owner_steering_source"],
            "owner steering mismatch")
    lane = decision["lane_id"]
    require(lane in lanes, "unregistered decision lane")
    require(decision.get("selected_priority") == lanes[lane]["priority"],
            "lane priority differs from policy")
    require(decision.get("blocks_primary") is False,
            "a package cannot claim exclusive blocking authority over P0")
    route = decision["route"]
    require(route in ("CONTINUE", "ISOLATE_SECONDARY", "PARK", "ESCALATE_OWNER"),
            "invalid continuation route")
    if lane != main:
        require(route != "ISOLATE_SECONDARY", "secondary already isolated")
    for key in ("unchanged_blocker_checks", "cycles_without_value"):
        require(type(decision.get(key)) is int and decision[key] >= 0,
                "invalid counter " + key)
    require(type(decision.get("material_progress")) is bool, "progress flag required")
    blocker = decision.get("blocker")
    require(isinstance(blocker, str), "blocker description required (may be empty)")
    stalled = (decision["unchanged_blocker_checks"] > limit["unchanged_blocker_checks"]
               or (not decision["material_progress"]
                   and decision["cycles_without_value"] >= limit["cycles_without_value"]))
    if stalled:
        require(route in ("PARK", "ISOLATE_SECONDARY", "ESCALATE_OWNER"),
                "repeat without value: park/isolate/escalate, not continue")
    if blocker and decision["unchanged_blocker_checks"] > 0:
        require(route != "CONTINUE" or decision["unchanged_blocker_checks"] <=
                limit["unchanged_blocker_checks"], "blocked repeated work cannot continue")
    critic = decision.get("strategic_critic")
    populated(critic, ("roadmap_challenge", "higher_priority_alternative",
                       "opportunity_cost", "lane_routing_challenge",
                       "value_checkpoint_challenge", "disposition"), "strategic_critic")
    require(critic["disposition"] in ("ALIGNED", "HOLD", "ESCALATE"),
            "invalid Critic disposition")
    require(not (critic["disposition"] != "ALIGNED" and route == "CONTINUE"),
            "Critic HOLD/ESCALATE cannot authorize continuation")
    owner = decision.get("owner_escalation")
    if stalled or route == "ESCALATE_OWNER":
        populated(owner, ("issue", "options", "recommendation", "owner_action"),
                  "owner_escalation")
    if route == "ISOLATE_SECONDARY":
        require(lane == main, "only P0 may route to isolated secondary")
        populated(decision, ("secondary_lane",), "decision")
        require(decision["secondary_lane"] in lanes and
                decision["secondary_lane"] != main and
                lanes[decision["secondary_lane"]]["branch_policy"] == "ISOLATED",
                "isolated route must identify a distinct registered lane")
    if route == "CONTINUE":
        require(critic["disposition"] == "ALIGNED", "Critic has not accepted continuation")
    return {"schema_version": 1, "status": "PORTFOLIO_LANE_VALUE_GATE_PASS",
            "policy_sha256": policy_sha, "decision_sha256": decision_sha,
            "lane_id": lane, "route": route,
            "assurance": "PROCEDURAL_SELF_REPORTED_NOT_INDEPENDENT"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--decision", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.root, args.policy, args.decision), sort_keys=True))
    except (PortfolioGateError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "HOLD", "reason": str(exc)}))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
