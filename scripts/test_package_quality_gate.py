"""Synthetic guardrails; no live services, paid calls or private data."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from package_quality_gate import GateError, check_publication, file_hash, make_packet, rotation, safe_path, validate, write_json


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = "a" * 40
        self.goal = {"schema_version": 1, "goal_id": "example", "revision": 1,
            "outcome": "Usable report", "purpose": "Inspect results", "constraints": [],
            "intent_provenance": ["synthetic owner request"], "changes": [],
            "success_criteria": [{"id": "g1", "description": "Complete report"}]}
        self.adapter = {"schema_version": 1, "project": "example", "mode": "PROCEDURAL_PILOT",
            "max_rounds": 2, "constraints": ["No paid API"], "required_checks": ["c1"]}
        self.contract = {"schema_version": 1, "project": "example", "lane_id": "report",
            "package_id": "p1", "base_commit": self.base, "author_session_id": "author",
            "goal_path": "goal.json", "adapter_path": "adapter.json", "outcome": "Report",
            "contribution": "Inspect results", "authority": "AUTO + VERIFY",
            "intent_provenance": ["synthetic request"], "scope": ["report"], "non_goals": [],
            "inputs": [], "criteria": [{"id": "c1", "description": "Complete", "goal_criteria": ["g1"]}],
            "required_evidence": ["checks.txt"], "mandatory_knowledge_domains": ["engineering"],
            "human_decisions": [], "assumptions": [], "dependencies": [], "next_action": "Review",
            "stop_boundary": "One package", "budget": {"round": 1, "max_rounds": 2, "usage": "unknown"}}
        for name, obj in [("goal.json", self.goal), ("adapter.json", self.adapter), ("contract.json", self.contract)]:
            write_json(self.root / name, obj)
        (self.root / "report.bin").write_bytes(b"report\x00bytes")
        (self.root / "checks.txt").write_text("synthetic meaningful check passed")
        self.packet = make_packet(self.root, "contract.json", ["report.bin"])
        self.supporter = self.review("supporter")
        self.critic = self.review("critic")

    def review(self, role):
        return {"schema_version": 1, "role": role, "session_id": role, "model": "synthetic",
            "candidate_digest": self.packet["candidate_digest"], "verdict": "PASS",
            "knowledge": [{"domain": "engineering", "commit": "b" * 40, "object": "generic.md",
                "applied_rule": "verify evidence", "criterion_id": "c1"}],
            "coverage": [{"criterion_id": "c1", "result": "PASS", "evidence": ["checks.txt"]}], "findings": []}

    def check(self):
        return validate(self.root, self.packet, self.supporter, self.critic, self.base)

    def test_valid_candidate_is_ready_for_ci_only(self):
        result = self.check()
        self.assertEqual(result["status"], "REVIEWED_READY_FOR_REQUIRED_CI")
        self.assertFalse(result["semantic_truth_proven"])
        self.assertFalse(result["required_ci_complete"])

    def test_changed_candidate_evidence_goal_adapter_or_contract_invalidates(self):
        for name in ["report.bin", "checks.txt", "goal.json", "adapter.json", "contract.json"]:
            with self.subTest(name=name):
                path = self.root / name
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                with self.assertRaises(GateError): self.check()
                path.write_bytes(original)

    def test_live_base_change_holds(self):
        with self.assertRaises(GateError): validate(self.root, self.packet, self.supporter, self.critic, "c" * 40)

    def test_same_author_or_reviewer_session_holds(self):
        for session in ["author", "supporter"]:
            self.critic["session_id"] = session
            with self.assertRaises(GateError): self.check()

    def test_missing_coverage_evidence_knowledge_or_review_holds(self):
        for field in ["coverage", "knowledge"]:
            original = self.critic[field]
            self.critic[field] = []
            with self.assertRaises(GateError): self.check()
            self.critic[field] = original
        self.critic["coverage"][0]["evidence"] = ["unknown.txt"]
        with self.assertRaises(GateError): self.check()

    def test_changed_digest_or_nonpass_review_holds(self):
        for key, value in [("candidate_digest", "0" * 64), ("verdict", "HOLD")]:
            original = self.critic[key]; self.critic[key] = value
            with self.assertRaises(GateError): self.check()
            self.critic[key] = original

    def test_material_deferred_finding_holds(self):
        finding = {"id": "f1", "kind": "robustness_defect", "material": True,
            "evidence": "missing integration", "remedy": "repair", "disposition": "DEFERRED",
            "resolution_evidence": []}
        self.critic["findings"] = [finding]
        with self.assertRaises(GateError): self.check()
        finding["disposition"] = "RESOLVED"
        with self.assertRaises(GateError): self.check()
        finding["resolution_evidence"] = ["checks.txt"]
        self.assertEqual(self.check()["status"], "REVIEWED_READY_FOR_REQUIRED_CI")

    def test_budget_exhaustion_and_human_gate_hold(self):
        self.contract["budget"]["round"] = 3
        write_json(self.root / "contract.json", self.contract)
        with self.assertRaises(GateError): make_packet(self.root, "contract.json", ["report.bin"])
        self.contract["budget"]["round"] = 1
        self.contract["human_decisions"] = ["owner must choose"]
        write_json(self.root / "contract.json", self.contract)
        with self.assertRaises(GateError): make_packet(self.root, "contract.json", ["report.bin"])

    def test_invalid_criteria_mapping(self):
        self.contract["criteria"][0]["goal_criteria"] = ["nonexistent"]
        write_json(self.root / "contract.json", self.contract)
        with self.assertRaises(GateError): make_packet(self.root, "contract.json", ["report.bin"])

    def test_path_and_symlink_escape(self):
        for name in ["../outside", "/absolute", "a/../b", "a\\b", "a//b", ".git/config"]:
            with self.assertRaises(GateError): safe_path(self.root, name)
        (self.root / "escape").symlink_to(self.root.parent)
        with self.assertRaises(GateError): safe_path(self.root, "escape/outside")

    def test_publication_cannot_add_unreviewed_files_or_omit_candidate(self):
        sidecars = ["packet.json", "supporter.json", "critic.json"]
        check_publication(self.packet, ["report.bin", *sidecars], sidecars)
        for outgoing in [["report.bin", "extra.py"], ["supporter.json"]]:
            with self.assertRaises(GateError): check_publication(self.packet, outgoing, sidecars)

    def test_symlink_candidates_refs_and_linked_parents_are_rejected(self):
        (self.root / "same.bin").write_bytes((self.root / "report.bin").read_bytes())
        (self.root / "published.bin").symlink_to(self.root / "report.bin")
        with self.assertRaises(GateError): make_packet(self.root, "contract.json", ["published.bin"])
        (self.root / "published.bin").unlink()
        (self.root / "published.bin").symlink_to(self.root / "same.bin")
        with self.assertRaises(GateError): make_packet(self.root, "contract.json", ["published.bin"])
        (self.root / "linked-parent").symlink_to(self.root)
        with self.assertRaises(GateError): make_packet(self.root, "linked-parent/contract.json", ["report.bin"])
        (self.root / "linked-goal.json").symlink_to(self.root / "goal.json")
        self.contract["goal_path"] = "linked-goal.json"
        write_json(self.root / "contract.json", self.contract)
        with self.assertRaises(GateError): make_packet(self.root, "contract.json", ["report.bin"])

    def test_git_executable_mode_changes_invalidate_packet(self):
        path = self.root / "report.bin"
        path.chmod(0o755)
        with self.assertRaises(GateError): self.check()

    def test_git_owner_execute_semantics_match_actual_git_tree_mode(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "config", "core.filemode", "true"], cwd=self.root, check=True)
        path = self.root / "report.bin"
        path.chmod(0o654)
        subprocess.run(["git", "add", "report.bin"], cwd=self.root, check=True)
        tree_mode = subprocess.check_output(["git", "ls-files", "--stage", "report.bin"], cwd=self.root, text=True).split()[0]
        self.packet = make_packet(self.root, "contract.json", ["report.bin"])
        self.assertEqual(tree_mode, self.packet["subject"]["git_modes"]["report.bin"])
        self.supporter = self.review("supporter"); self.critic = self.review("critic")
        self.check()
        path.chmod(0o744)
        subprocess.run(["git", "add", "report.bin"], cwd=self.root, check=True)
        new_mode = subprocess.check_output(["git", "ls-files", "--stage", "report.bin"], cwd=self.root, text=True).split()[0]
        self.assertNotEqual(tree_mode, new_mode)
        with self.assertRaises(GateError): self.check()

    def test_deletion_binds_absence(self):
        packet = make_packet(self.root, "contract.json", ["report.bin"], ["removed.py"])
        self.packet = packet
        self.supporter = self.review("supporter"); self.critic = self.review("critic")
        self.check()
        (self.root / "removed.py").write_text("restored")
        with self.assertRaises(GateError): self.check()

    def test_rotation_prepares_atomic_pair_and_preserves_existing_fields(self):
        write_json(self.root / "CURRENT.json", {"legacy": "preserved"})
        old_hash = file_hash(self.root / "CURRENT.json")
        next_doc = {"legacy": "retained", "package_quality": {"schema_version": 1,
            "goal_ref": {"path": "goal.json", "sha256": file_hash(self.root / "goal.json")},
            "package_ref": "p1", "status": "CHECKPOINT", "next_action": "Resume",
            "predecessor_sha256": old_hash, "last_evidence": [], "reviews": [],
            "unfinished_criteria": [], "failures": [], "decisions": [], "constraints": [],
            "budget": {"round": 1, "max_rounds": 2, "usage": "unknown"}}}
        result = rotation(self.root, "CURRENT.json", next_doc, old_hash)
        self.assertEqual(result["writes"]["PREVIOUS.json"], {"legacy": "preserved"})
        self.assertEqual(json.loads((self.root / "CURRENT.json").read_text()), {"legacy": "preserved"})
        with self.assertRaises(GateError): rotation(self.root, "CURRENT.json", next_doc, "0" * 64)

    def test_rotation_cannot_drop_history_or_reset_same_package_budget(self):
        old = {"schema_version": 1, "legacy_authority": "keep",
            "legacy_project_state": {"authority": "HUMAN GATE", "blocker": "owner needed"}, "package_quality": {
            "schema_version": 1, "goal_ref": {"path": "goal.json", "sha256": file_hash(self.root / "goal.json")},
            "package_ref": "p1", "status": "HOLD", "next_action": "Repair", "predecessor_sha256": "0" * 64,
            "last_evidence": [], "reviews": [], "unfinished_criteria": ["c1"],
            "failures": ["previous defect"], "decisions": ["human blocker"], "constraints": ["no trading"],
            "budget": {"round": 2, "max_rounds": 2, "usage": "unknown"}}}
        write_json(self.root / "CURRENT.json", old)
        old_hash = file_hash(self.root / "CURRENT.json")
        import copy
        candidate = copy.deepcopy(old)
        candidate["package_quality"]["predecessor_sha256"] = old_hash
        rotation(self.root, "CURRENT.json", candidate, old_hash)
        variants = []
        removed = copy.deepcopy(candidate); del removed["legacy_authority"]; variants.append(removed)
        nested = copy.deepcopy(candidate); nested["legacy_project_state"] = {}; variants.append(nested)
        for key in ["failures", "decisions", "constraints"]:
            changed = copy.deepcopy(candidate); changed["package_quality"][key] = []; variants.append(changed)
        for key, value in [("round", 1), ("max_rounds", 99)]:
            changed = copy.deepcopy(candidate); changed["package_quality"]["budget"][key] = value; variants.append(changed)
        for changed in variants:
            with self.assertRaises(GateError): rotation(self.root, "CURRENT.json", changed, old_hash)


if __name__ == "__main__":
    unittest.main()
