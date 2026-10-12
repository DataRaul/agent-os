"""Offline lane-isolated checkpoint plans. The caller publishes with a Git head lease."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from package_quality_gate import GateError, file_hash, require, rotation, safe_path


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def registry(root: Path, name: str) -> dict:
    value = json.loads(safe_path(root, name).read_text())
    require(value.get("schema_version") == 1, "unsupported lane registry")
    require(isinstance(value.get("project"), str) and bool(value["project"]), "project missing")
    require(isinstance(value.get("branch"), str) and bool(value["branch"]), "state branch missing")
    lanes = value.get("lanes")
    require(isinstance(lanes, dict) and bool(lanes), "lanes missing")
    identifiers = set()
    for lane_id, lane in lanes.items():
        require(bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", lane_id)), "invalid lane ID")
        require(isinstance(lane, dict), "lane record missing")
        require(lane.get("current") == f"docs/handovers/{lane_id}/CURRENT.json", "lane CURRENT path mismatch")
        require(lane.get("previous") == f"docs/handovers/{lane_id}/PREVIOUS.json", "lane PREVIOUS path mismatch")
        for path in [lane["current"], lane["previous"]]:
            safe_path(root, path)
        aliases = lane.get("aliases", [])
        require(isinstance(aliases, list), "alias array required")
        for identifier in [lane_id, *aliases]:
            require(isinstance(identifier, str) and bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier)), "invalid lane alias")
            require(identifier not in identifiers, "ambiguous lane alias")
            identifiers.add(identifier)
        goal = lane.get("goal_ref")
        require(isinstance(goal, dict), "lane goal reference missing")
        require(file_hash(safe_path(root, goal.get("path"))) == goal.get("sha256"), "lane goal changed")
    return value


def select(value: dict, identifier: str) -> tuple[str, dict]:
    matches = [(key, row) for key, row in value["lanes"].items()
               if identifier == key or identifier in row.get("aliases", [])]
    require(len(matches) == 1, "unknown or ambiguous lane; register it before writing")
    return matches[0]


def identity(doc: dict, value: dict, lane_id: str, lane: dict) -> None:
    require(isinstance(doc, dict), "checkpoint object required")
    require(doc.get("project") == value["project"], "checkpoint project mismatch")
    require(doc.get("lane_id") == lane_id, "checkpoint lane mismatch")
    require(doc.get("lane_goal_ref") == lane["goal_ref"], "checkpoint lane goal mismatch")


def prepare(root: Path, registry_path: str, identifier: str, next_doc: dict,
            snapshot_head: str, expected_head: str, expected_current: str) -> dict:
    require(bool(re.fullmatch(r"[0-9a-f]{40}", snapshot_head)), "invalid snapshot branch head")
    require(snapshot_head == expected_head, "branch advanced; fetch latest tree and reread this lane")
    value = registry(root, registry_path)
    lane_id, lane = select(value, identifier)
    current = safe_path(root, lane["current"])
    old_bytes = current.read_bytes()
    require(sha_bytes(old_bytes) == expected_current, "lane checkpoint advanced; reconcile same-lane work")
    identity(json.loads(old_bytes), value, lane_id, lane)
    identity(next_doc, value, lane_id, lane)
    adapter_name = value.get("quality_adapter")
    if adapter_name:
        adapter = json.loads(safe_path(root, adapter_name).read_text())
        require(adapter.get("project") == value["project"], "quality adapter project mismatch")
        ceiling = adapter.get("max_rounds")
        maximum = next_doc.get("package_quality", {}).get("budget", {}).get("max_rounds")
        require(type(ceiling) is int and type(maximum) is int and maximum <= ceiling, "adapter review budget exceeded")
    result = rotation(root, lane["current"], next_doc, expected_current)
    new_bytes = (json.dumps(result["writes"][lane["current"]], indent=2, ensure_ascii=False) + "\n").encode()
    return {
        "schema_version": 1, "project": value["project"], "lane_id": lane_id,
        "branch": value["branch"], "registry_path": registry_path,
        "registry_sha256": file_hash(safe_path(root, registry_path)),
        "expected_head": expected_head, "expected_current_sha256": expected_current,
        "writes": [
            {"path": lane["current"], "mode": "100644", "content": new_bytes.decode(), "sha256": sha_bytes(new_bytes)},
            {"path": lane["previous"], "mode": "100644", "content": old_bytes.decode(), "sha256": sha_bytes(old_bytes)},
        ],
        "publication": "Latest tree at expected_head; exactly these two writes; one commit; expected-head update; no force; skip CI",
        "on_conflict": "Reread branch and lane CURRENT. Unrelated-lane change: rebuild on latest tree. Same-lane change: reconcile work; never overwrite blindly.",
    }


def verify(root: Path, plan: dict, live_head: str) -> dict:
    require(plan.get("schema_version") == 1, "unsupported plan")
    require(live_head == plan.get("expected_head"), "branch advanced; rebuild plan from latest tree")
    value = registry(root, plan.get("registry_path"))
    require(file_hash(safe_path(root, plan["registry_path"])) == plan.get("registry_sha256"), "registry changed")
    lane_id, lane = select(value, plan.get("lane_id"))
    writes = plan.get("writes")
    require(isinstance(writes, list) and len(writes) == 2, "exact lane pair required")
    require({row.get("path") for row in writes} == {lane["current"], lane["previous"]}, "cross-lane or shared write rejected")
    row = next(row for row in writes if row["path"] == lane["current"])
    rebuilt = prepare(root, plan["registry_path"], lane_id, json.loads(row["content"]),
                      live_head, live_head, plan["expected_current_sha256"])
    require(plan == rebuilt, "plan bytes, modes or identity changed")
    return {"schema_version": 1, "status": "LANE_PAIR_READY_FOR_LEASED_PUBLICATION",
            "lane_id": lane_id, "expected_head": live_head,
            "assurance": "OFFLINE_PLAN_CHECK; caller must fetch live head and use server-side lease"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("prepare")
    build.add_argument("--root", required=True, type=Path)
    for name in ["registry", "lane", "next", "snapshot-head", "expected-head", "expected-current", "output"]:
        build.add_argument("--" + name, required=True)
    check = sub.add_parser("verify")
    check.add_argument("--root", required=True, type=Path)
    check.add_argument("--plan", required=True)
    check.add_argument("--live-head", required=True)
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        if args.command == "prepare":
            result = prepare(root, args.registry, args.lane, json.loads(safe_path(root, args.next).read_text()),
                             args.snapshot_head, args.expected_head, args.expected_current)
            target = safe_path(root, args.output)
            protected = {row["path"] for row in result["writes"]} | {args.registry, args.next}
            protected |= {p for row in registry(root, args.registry)["lanes"].values() for p in [row["current"], row["previous"], row["goal_ref"]["path"]]}
            require(args.output not in protected, "plan output would overwrite source/checkpoint")
            require(args.output.startswith("docs/package_quality/evidence/") or
                    args.output.startswith(f"docs/handovers/{result['lane_id']}/plans/"), "plan output must use an evidence/own-lane plans folder")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
            print(json.dumps({"status": "PREPARED_NOT_PUBLISHED", "lane_id": result["lane_id"]}))
        else:
            print(json.dumps(verify(root, json.loads(safe_path(root, args.plan).read_text()), args.live_head)))
    except (GateError, OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        print(json.dumps({"status": "HOLD", "reason": str(exc)}))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
