"""Offline procedural package gate. No network, agent launching or publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

from plan_first_gate import validate_binding, validate_value


class GateError(ValueError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise GateError(message)


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_path(root: Path, name: str) -> Path:
    require(isinstance(name, str) and bool(name), "missing relative path")
    p = PurePosixPath(name)
    require(
        not p.is_absolute() and ".." not in p.parts and str(p) == name
        and "\\" not in name and p.parts and p.parts[0] != ".git",
        f"unsafe path: {name}",
    )
    resolved = (root / name).resolve()
    require(resolved.is_relative_to(root.resolve()), f"path escapes root: {name}")
    cursor = root
    for part in p.parts:
        cursor = cursor / part
        require(not cursor.is_symlink(), f"symlinks unsupported: {name}")
    return resolved


def load(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise GateError(f"cannot read JSON {path}: {exc}") from exc
    require(isinstance(obj, dict), f"JSON object required: {path}")
    require(type(obj.get("schema_version")) is int and obj["schema_version"] == 1, f"unsupported schema: {path}")
    return obj


def text_fields(obj: dict, names: list[str]) -> None:
    for name in names:
        require(isinstance(obj.get(name), str) and bool(obj[name].strip()), f"missing {name}")


def list_fields(obj: dict, names: list[str]) -> None:
    for name in names:
        require(isinstance(obj.get(name), list), f"array required: {name}")


def unique_strings(values: list, label: str, nonempty: bool = False) -> set[str]:
    require(isinstance(values, list), f"array required: {label}")
    require(not nonempty or bool(values), f"empty {label}")
    require(all(isinstance(v, str) and v.strip() for v in values), f"invalid {label}")
    require(len(values) == len(set(values)), f"duplicate {label}")
    return set(values)


def criteria_ids(rows: list) -> set[str]:
    require(isinstance(rows, list) and bool(rows), "criteria required")
    ids = []
    for row in rows:
        require(isinstance(row, dict), "criterion object required")
        text_fields(row, ["id", "description"])
        ids.append(row["id"])
    return unique_strings(ids, "criterion IDs", True)


def contract_bundle(root: Path, contract_path: str) -> tuple[dict, dict, dict]:
    contract = load(safe_path(root, contract_path))
    text_fields(contract, [
        "project", "lane_id", "package_id", "base_commit", "author_session_id",
        "goal_path", "adapter_path", "outcome", "contribution", "authority",
        "next_action", "stop_boundary",
    ])
    require(bool(re.fullmatch(r"[0-9a-f]{40}", contract["base_commit"])), "invalid base commit")
    list_fields(contract, ["intent_provenance", "scope", "non_goals", "inputs",
        "criteria", "required_evidence", "mandatory_knowledge_domains",
        "human_decisions", "assumptions", "dependencies"])
    require(bool(contract["intent_provenance"]) and bool(contract["scope"]), "intent/scope missing")
    require(contract["authority"] in {"AUTO", "AUTO + VERIFY"}, "authority holds publication")
    require(not contract["human_decisions"], "unresolved human decisions")
    ids = criteria_ids(contract["criteria"])
    unique_strings(contract["required_evidence"], "required evidence", True)
    unique_strings(contract["mandatory_knowledge_domains"], "mandatory domains", True)
    goal = load(safe_path(root, contract["goal_path"]))
    text_fields(goal, ["goal_id", "outcome", "purpose"])
    list_fields(goal, ["constraints", "intent_provenance", "changes"])
    require(bool(goal["intent_provenance"]), "goal provenance missing")
    require(type(goal.get("revision")) is int and goal["revision"] >= 1, "invalid goal revision")
    goal_ids = criteria_ids(goal.get("success_criteria"))
    for row in contract["criteria"]:
        mapped = unique_strings(row.get("goal_criteria"), "goal criteria", True)
        require(mapped <= goal_ids, "unknown goal criterion")
    adapter = load(safe_path(root, contract["adapter_path"]))
    require(adapter.get("project") == contract["project"], "adapter/project mismatch")
    require(adapter.get("mode") == "PROCEDURAL_PILOT", "adapter not selected")
    selected = adapter.get("review_mode", "INDEPENDENT_SESSIONS")
    require(selected in {"INDEPENDENT_SESSIONS", "SAME_CHAT_SEQUENTIAL"}, "unknown review mode")
    require(contract.get("review_mode", "INDEPENDENT_SESSIONS") == selected,
        "contract review mode differs from selected adapter; migrate and refreeze")
    if selected == "SAME_CHAT_SEQUENTIAL":
        stage_evidence = contract.get("stage_evidence")
        require(isinstance(stage_evidence, dict), "alignment/build QA evidence mapping required")
        for stage in ["align", "build_qa"]:
            refs = unique_strings(stage_evidence.get(stage), stage + " evidence", True)
            require(refs <= set(contract["required_evidence"]), "stage evidence must be frozen required evidence")
    list_fields(adapter, ["constraints"])
    require(type(adapter.get("max_rounds")) is int and adapter["max_rounds"] >= 1, "adapter round limit missing")
    checks = unique_strings(adapter.get("required_checks", []), "required checks")
    require(checks <= ids, "required check criterion absent")
    budget = contract.get("budget")
    require(isinstance(budget, dict), "budget missing")
    require(type(budget.get("round")) is int and type(budget.get("max_rounds")) is int, "invalid round budget")
    require(1 <= budget["round"] <= budget["max_rounds"] <= adapter["max_rounds"], "review budget exhausted/widened")
    text_fields(budget, ["usage"])
    validate_binding(root, contract, adapter)
    return contract, goal, adapter


def changed_paths(root: Path, git_base: str) -> set[str]:
    try:
        tracked = subprocess.check_output(
            ["git", "diff", "--name-only", "-z", git_base, "--"], cwd=root
        ).decode().split("\0")
        untracked = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=root
        ).decode().split("\0")
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GateError("git inventory unavailable") from exc
    return set(tracked + untracked) - {""}


def make_packet(root: Path, contract_path: str, paths: list[str], deletions: list[str] | None = None) -> dict:
    contract, _, _ = contract_bundle(root, contract_path)
    unique_strings(paths, "candidate paths", True)
    deletions = deletions or []
    unique_strings(deletions, "deletions")
    require(not (set(paths) & set(deletions)), "path also deleted")
    refs = sorted(set([contract_path, contract["goal_path"], contract["adapter_path"], *contract["required_evidence"]]))
    hashes = {}
    modes = {}
    for name in sorted(set(paths + refs)):
        p = safe_path(root, name)
        require(p.is_file(), f"required file missing: {name}")
        hashes[name] = file_hash(p)
        modes[name] = "100755" if p.stat().st_mode & 0o100 else "100644"
    for name in deletions:
        require(not safe_path(root, name).exists(), f"deleted file exists: {name}")
        hashes[name] = None
        modes[name] = None
    subject = {
        "schema_version": 1, "contract_path": contract_path,
        "project": contract["project"], "lane_id": contract["lane_id"],
        "package_id": contract["package_id"], "base_commit": contract["base_commit"],
        "author_session_id": contract["author_session_id"],
        "candidate_paths": sorted(paths + deletions), "deletions": sorted(deletions),
        "hashes": hashes, "git_modes": modes,
    }
    return {"schema_version": 1, "subject": subject, "candidate_digest": digest(subject)}


def check_review(root: Path, report: dict, packet: dict, contract: dict, role: str) -> None:
    require(report.get("schema_version") == 1, "unsupported review schema")
    require(report.get("role") == role, "wrong review role")
    text_fields(report, ["session_id", "model", "candidate_digest", "verdict"])
    if contract.get("review_mode", "INDEPENDENT_SESSIONS") == "SAME_CHAT_SEQUENTIAL":
        require(report.get("review_mode") == "SAME_CHAT_SEQUENTIAL", "sequential review mode missing")
        require(report["session_id"] == contract["author_session_id"], "same-chat pass must use actual author session")
        require(report.get("independent") is False, "same-chat pass cannot claim independence")
    else:
        require(report["session_id"] != contract["author_session_id"], "author cannot independently review")
    require(report["candidate_digest"] == packet["candidate_digest"], "stale review")
    require(report["verdict"] == "PASS", f"{role} holds publication")
    list_fields(report, ["knowledge", "coverage", "findings"])
    ids = criteria_ids(contract["criteria"])
    domains = set()
    for item in report["knowledge"]:
        require(isinstance(item, dict), "knowledge object required")
        text_fields(item, ["domain", "commit", "object", "applied_rule", "criterion_id"])
        require(bool(re.fullmatch(r"[0-9a-f]{40}", item["commit"])), "knowledge commit not pinned")
        require(item["criterion_id"] in ids, "knowledge criterion unknown")
        domains.add(item["domain"])
    require(set(contract["mandatory_knowledge_domains"]) <= domains, f"{role} missing mandatory knowledge")
    covered = []
    evidence = set(contract["required_evidence"])
    for row in report["coverage"]:
        require(isinstance(row, dict), "coverage object required")
        text_fields(row, ["criterion_id", "result"])
        require(row["result"] == "PASS", "criterion did not pass")
        refs = unique_strings(row.get("evidence"), "coverage evidence", True)
        require(refs <= evidence, "unhashed coverage evidence")
        covered.append(row["criterion_id"])
    require(unique_strings(covered, "covered criteria", True) == ids, "incomplete criterion coverage")
    finding_ids = []
    for finding in report["findings"]:
        require(isinstance(finding, dict), "finding object required")
        text_fields(finding, ["id", "kind", "evidence", "remedy", "disposition"])
        require(finding["kind"] in {"requirement_defect", "robustness_defect", "optional_enhancement"}, "unknown finding kind")
        require(type(finding.get("material")) is bool, "finding material must be boolean")
        require(finding["disposition"] in {"RESOLVED", "DEFERRED"}, "unresolved finding")
        if finding["material"]:
            require(finding["disposition"] == "RESOLVED", "material defect deferred")
            refs = unique_strings(finding.get("resolution_evidence"), "resolution evidence", True)
            require(refs <= evidence, "unhashed resolution evidence")
        finding_ids.append(finding["id"])
    unique_strings(finding_ids, "finding IDs")


def validate_candidate(root: Path, packet: dict, current_base: str) -> dict:
    require(isinstance(packet.get("subject"), dict), "packet subject missing")
    subject = packet["subject"]
    require(packet.get("candidate_digest") == digest(subject), "packet digest mismatch")
    require(subject.get("base_commit") == current_base, "live base changed; reconcile and rereview")
    contract, _, _ = contract_bundle(root, subject.get("contract_path"))
    actual = make_packet(root, subject["contract_path"],
        [p for p in subject["candidate_paths"] if p not in subject["deletions"]], subject["deletions"])
    require(actual == packet, "candidate/contract/goal/adapter/evidence changed")
    return contract


def sequential_stage(report: dict, phase: int, predecessor: str) -> None:
    require(type(report.get("stage")) is int and report["stage"] == phase, "review stage out of order")
    require(report.get("predecessor_digest") == predecessor, "review predecessor changed or missing")


def validate(root: Path, packet: dict, supporter: dict, critic: dict, current_base: str,
        synthesis: dict | None = None) -> dict:
    contract = validate_candidate(root, packet, current_base)
    check_review(root, supporter, packet, contract, "supporter")
    check_review(root, critic, packet, contract, "critic")
    reports = {"supporter": digest(supporter), "critic": digest(critic)}
    sequential = contract.get("review_mode", "INDEPENDENT_SESSIONS") == "SAME_CHAT_SEQUENTIAL"
    if sequential:
        sequential_stage(supporter, 3, packet["candidate_digest"])
        sequential_stage(critic, 4, reports["supporter"])
        require(isinstance(synthesis, dict), "final synthesis required")
        check_review(root, synthesis, packet, contract, "synthesis")
        sequential_stage(synthesis, 5, reports["critic"])
        require(synthesis.get("report_digests") == reports, "synthesis does not collate exact final reports")
        dispositions = [{"role": role, "id": finding["id"], "disposition": finding["disposition"],
            "resolution_evidence": finding.get("resolution_evidence", [])}
            for role, report in [("supporter", supporter), ("critic", critic)] for finding in report["findings"]]
        require(synthesis.get("finding_dispositions") == dispositions, "synthesis dropped or changed reviewer finding dispositions")
        require(synthesis.get("stages") == ["align", "build_qa", "supporter", "critic", "synthesis"],
            "synthesis stage coverage missing or out of order")
        text_fields(synthesis, ["rationale", "goal_contribution", "next_gate"])
        require(synthesis["next_gate"] == "REQUIRED_CI", "synthesis cannot skip required CI")
        if contract.get("plan_first") is not None:
            validate_value(synthesis, contract)
        reports["synthesis"] = digest(synthesis)
    else:
        require(synthesis is None, "synthesis only supported in selected sequential mode")
        require(supporter["session_id"] != critic["session_id"], "review sessions must differ")
    return {"schema_version": 1,
        "status": "SEQUENTIALLY_REVIEWED_READY_FOR_REQUIRED_CI" if sequential else "REVIEWED_READY_FOR_REQUIRED_CI",
        "candidate_digest": packet["candidate_digest"],
        "review_mode": "SAME_CHAT_SEQUENTIAL" if sequential else "INDEPENDENT_SESSIONS",
        "assurance": "PROCEDURAL_SAME_CHAT_PASSES" if sequential else "PROCEDURAL_SELF_REPORTED_SESSIONS",
        "independent_review_proven": False,
        "semantic_truth_proven": False, "required_ci_complete": False,
        "report_digests": reports}


def next_stage(root: Path, packet: dict, current_base: str, supporter_path: str,
        critic_path: str, synthesis_path: str) -> dict:
    """Select the next same-chat pass; never generate verdicts or launch a model."""
    contract = validate_candidate(root, packet, current_base)
    require(contract.get("review_mode") == "SAME_CHAT_SEQUENTIAL", "next requires selected sequential mode")
    loaded = {}
    predecessor = packet["candidate_digest"]
    for phase, role, path in [(3, "supporter", supporter_path), (4, "critic", critic_path),
            (5, "synthesis", synthesis_path)]:
        p = safe_path(root, path)
        require(path not in packet["subject"]["hashes"], "review sidecar is part of its own subject")
        if not p.exists():
            return {"schema_version": 1, "status": "PASS_REQUIRED", "stage": phase,
                "next_action": role, "output": path, "candidate_digest": packet["candidate_digest"],
                "predecessor_digest": predecessor, "session_id": contract["author_session_id"],
                "review_mode": "SAME_CHAT_SEQUENTIAL", "independent": False}
        report = load(p)
        check_review(root, report, packet, contract, role)
        sequential_stage(report, phase, predecessor)
        loaded[role] = report
        predecessor = digest(report)
    return validate(root, packet, loaded["supporter"], loaded["critic"], current_base, loaded["synthesis"])


def check_publication(packet: dict, outgoing: list[str], sidecars: list[str]) -> None:
    names = unique_strings(outgoing, "publication paths", True)
    candidates = set(packet["subject"]["candidate_paths"])
    require(not (candidates & set(sidecars)), "review sidecar is part of its own subject")
    require(candidates <= names, "candidate omitted from publication")
    require(names <= candidates | set(sidecars), "unreviewed outgoing file")


def retained_fields(old: Any, new: Any, prefix: str = "checkpoint") -> None:
    """Keep existing nested field names; values still need semantic review."""
    if isinstance(old, dict):
        require(isinstance(new, dict), f"{prefix} replaced an object")
        require(set(old) <= set(new), f"{prefix} dropped existing local fields")
        for key, value in old.items():
            retained_fields(value, new[key], prefix + "." + key)


def rotation(root: Path, current_path: str, next_doc: dict, expected_current: str) -> dict:
    current_file = safe_path(root, current_path)
    old_hash = file_hash(current_file)
    require(old_hash == expected_current, "checkpoint advanced; reread before rotation")
    old = json.loads(current_file.read_text())
    require(isinstance(old, dict) and isinstance(next_doc, dict), "checkpoint objects required")
    retained_fields(old, next_doc)
    quality = next_doc.get("package_quality")
    require(isinstance(quality, dict) and quality.get("schema_version") == 1, "quality namespace missing")
    text_fields(quality, ["package_ref", "status", "next_action", "predecessor_sha256"])
    list_fields(quality, ["last_evidence", "reviews", "unfinished_criteria", "failures", "decisions", "constraints"])
    require(isinstance(quality.get("budget"), dict), "checkpoint budget missing")
    text_fields(quality["budget"], ["usage"])
    budget = quality["budget"]
    require(type(budget.get("round")) is int and type(budget.get("max_rounds")) is int,
        "checkpoint round budget missing")
    require(1 <= budget["round"] <= budget["max_rounds"], "checkpoint budget invalid")
    prior = old.get("package_quality")
    if isinstance(prior, dict):
        require(set(prior) <= set(quality), "checkpoint dropped quality fields")
        for name in ["failures", "decisions", "constraints"]:
            require(all(item in quality[name] for item in prior.get(name, [])),
                f"checkpoint erased {name}; preserve history and append new dispositions")
        if prior.get("package_ref") == quality["package_ref"]:
            old_budget = prior.get("budget", {})
            require(type(old_budget.get("round")) is int and type(old_budget.get("max_rounds")) is int,
                "prior package budget needs explicit reconciliation")
            require(budget["round"] >= old_budget["round"] and budget["max_rounds"] <= old_budget["max_rounds"],
                "same-package retry budget reset/widened")
    ref = quality.get("goal_ref")
    require(isinstance(ref, dict), "checkpoint goal reference missing")
    require(file_hash(safe_path(root, ref.get("path"))) == ref.get("sha256"), "checkpoint goal changed")
    require(quality["predecessor_sha256"] == old_hash, "checkpoint predecessor mismatch")
    require(current_file.name == "CURRENT.json", "canonical CURRENT filename required")
    previous_name = str(PurePosixPath(current_path).with_name("PREVIOUS.json"))
    return {"schema_version": 1, "expected_current_sha256": old_hash,
        "writes": {previous_name: old, current_path: next_doc},
        "publication": "ONE_COMMIT_ATOMIC_REF_WITH_EXPECTED_HEAD_LEASE"}


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--contract", required=True)
    freeze.add_argument("--paths", nargs="+", required=True)
    freeze.add_argument("--deletions", nargs="*", default=[])
    freeze.add_argument("--output", required=True)
    freeze.add_argument("--git-base")
    check = sub.add_parser("validate")
    for name in ["packet", "supporter", "critic", "current-base", "publication-list"]:
        check.add_argument("--" + name, required=True)
    check.add_argument("--git-base")
    check.add_argument("--synthesis")
    advance = sub.add_parser("next")
    for name in ["packet", "supporter", "critic", "synthesis", "current-base"]:
        advance.add_argument("--" + name, required=True)
    rotate = sub.add_parser("rotate")
    for name in ["current", "next", "expected-current", "output"]:
        rotate.add_argument("--" + name, required=True)
    for cmd in [freeze, check, rotate, advance]:
        cmd.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command == "freeze":
            packet = make_packet(root, args.contract, args.paths, args.deletions)
            output = safe_path(root, args.output)
            require(args.output not in packet["subject"]["hashes"], "packet cannot hash itself")
            if args.git_base:
                require(changed_paths(root, args.git_base) <= set(packet["subject"]["candidate_paths"]) | {args.output}, "changed/untracked path omitted")
            write_json(output, packet)
            print(json.dumps({"status": "FROZEN_NOT_REVIEWED", "candidate_digest": packet["candidate_digest"]}))
        elif args.command == "next":
            print(json.dumps(next_stage(root, load(safe_path(root, args.packet)), args.current_base,
                args.supporter, args.critic, args.synthesis)))
        elif args.command == "validate":
            packet = load(safe_path(root, args.packet))
            supporter = load(safe_path(root, args.supporter))
            critic = load(safe_path(root, args.critic))
            synthesis = load(safe_path(root, args.synthesis)) if args.synthesis else None
            result = validate(root, packet, supporter, critic, args.current_base, synthesis)
            outgoing = json.loads(Path(args.publication_list).read_text())
            sidecars = [args.packet, args.supporter, args.critic]
            if args.synthesis:
                sidecars.append(args.synthesis)
            for name in outgoing:
                safe_path(root, name)
            check_publication(packet, outgoing, sidecars)
            if args.git_base:
                require(changed_paths(root, args.git_base) <= set(outgoing), "changed/untracked path omitted")
            result["report_file_hashes"] = {name: file_hash(safe_path(root, name)) for name in sidecars[1:]}
            print(json.dumps(result))
        else:
            next_doc = json.loads(Path(args.next).read_text())
            result = rotation(root, args.current, next_doc, args.expected_current)
            write_json(Path(args.output), result)
            print(json.dumps({"status": "ROTATION_PREPARED_NOT_PUBLISHED", "paths": list(result["writes"])}))
    except (GateError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "HOLD", "reason": str(exc)}))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
