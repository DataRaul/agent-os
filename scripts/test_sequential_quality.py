"""Same-chat workflow controls; synthetic reports never establish independent review."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from package_quality_gate import GateError, digest, make_packet, next_stage, validate, write_json
import test_package_quality_gate as fixtures


class SequentialTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.GateTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.temp.cleanup)
        t = self.fixture
        t.adapter["review_mode"] = "SAME_CHAT_SEQUENTIAL"
        t.contract["review_mode"] = "SAME_CHAT_SEQUENTIAL"
        t.contract["stage_evidence"] = {"align": ["checks.txt"], "build_qa": ["checks.txt"]}
        write_json(t.root / "adapter.json", t.adapter)
        write_json(t.root / "contract.json", t.contract)
        t.packet = make_packet(t.root, "contract.json", ["report.bin"])
        self.supporter = self.report("supporter", 3, t.packet["candidate_digest"])
        self.critic = self.report("critic", 4, digest(self.supporter))
        self.synthesis = self.report("synthesis", 5, digest(self.critic))
        self.synthesis.update({"report_digests": {"supporter": digest(self.supporter), "critic": digest(self.critic)},
            "finding_dispositions": [],
            "stages": ["align", "build_qa", "supporter", "critic", "synthesis"],
            "rationale": "Both passes cover the fixed criterion and have no unresolved findings.",
            "goal_contribution": "The report is inspectable.", "next_gate": "REQUIRED_CI"})

    def report(self, role, stage, predecessor):
        row = self.fixture.review(role)
        row.update({"session_id": "author", "review_mode": "SAME_CHAT_SEQUENTIAL", "independent": False,
            "stage": stage, "predecessor_digest": predecessor})
        return row

    def check(self):
        t = self.fixture
        return validate(t.root, t.packet, self.supporter, self.critic, t.base, self.synthesis)

    def advance(self):
        t = self.fixture
        return next_stage(t.root, t.packet, t.base, "supporter.json", "critic.json", "synthesis.json")

    def test_real_next_sequence_and_ready_assurance(self):
        t = self.fixture
        for stage, role in [(3, "supporter"), (4, "critic"), (5, "synthesis")]:
            step = self.advance()
            self.assertEqual((step["stage"], step["next_action"]), (stage, role))
            write_json(t.root / (role + ".json"), getattr(self, role))
        result = self.advance()
        self.assertEqual(result["status"], "SEQUENTIALLY_REVIEWED_READY_FOR_REQUIRED_CI")
        self.assertFalse(result["independent_review_proven"])
        self.assertFalse(result["required_ci_complete"])
        self.assertFalse(result["semantic_truth_proven"])

    def test_cannot_skip_missing_supporter(self):
        write_json(self.fixture.root / "critic.json", self.critic)
        self.assertEqual(self.advance()["next_action"], "supporter")

    def test_cannot_rename_phases_as_separate_sessions(self):
        self.critic["session_id"] = "author:critic"
        with self.assertRaises(GateError): self.check()

    def test_cannot_claim_independence(self):
        self.supporter["independent"] = True
        with self.assertRaises(GateError): self.check()

    def test_synthesis_required(self):
        t = self.fixture
        with self.assertRaises(GateError): validate(t.root, t.packet, self.supporter, self.critic, t.base)

    def test_synthesis_cannot_waive_critic_hold(self):
        self.critic["verdict"] = "HOLD"
        with self.assertRaises(GateError): self.check()

    def test_synthesis_cannot_waive_material_findings(self):
        self.critic["findings"] = [{"id": "f1", "kind": "requirement_defect", "material": True,
            "evidence": "missing integration", "remedy": "repair", "disposition": "DEFERRED", "resolution_evidence": []}]
        with self.assertRaises(GateError): self.check()

    def test_synthesis_must_collate_optional_findings(self):
        self.critic["findings"] = [{"id": "f1", "kind": "optional_enhancement", "material": False,
            "evidence": "presentation enhancement", "remedy": "future work", "disposition": "DEFERRED", "resolution_evidence": []}]
        self.synthesis["predecessor_digest"] = digest(self.critic)
        self.synthesis["report_digests"]["critic"] = digest(self.critic)
        with self.assertRaises(GateError): self.check()
        self.synthesis["finding_dispositions"] = [{"role": "critic", "id": "f1", "disposition": "DEFERRED", "resolution_evidence": []}]
        self.check()

    def test_alignment_and_build_qa_evidence_required(self):
        t = self.fixture
        t.contract["stage_evidence"] = {"align": [], "build_qa": ["unknown.txt"]}
        write_json(t.root / "contract.json", t.contract)
        with self.assertRaises(GateError): make_packet(t.root, "contract.json", ["report.bin"])

    def test_changed_report_invalidates_successor(self):
        self.supporter["model"] = "changed model"
        with self.assertRaises(GateError): self.check()

    def test_wrong_stage_order_or_synthesis_hash_holds(self):
        for key, value in [("stage", 4), ("predecessor_digest", "0" * 64),
                ("report_digests", {}), ("stages", ["critic", "supporter"]), ("next_gate", "MERGE")]:
            original = copy.deepcopy(self.synthesis)
            self.synthesis[key] = value
            with self.subTest(key=key), self.assertRaises(GateError): self.check()
            self.synthesis = original

    def test_adapter_cannot_silently_change_existing_contract(self):
        t = self.fixture
        del t.contract["review_mode"]
        write_json(t.root / "contract.json", t.contract)
        with self.assertRaises(GateError): make_packet(t.root, "contract.json", ["report.bin"])

    def test_stale_candidate_stops_next_and_validation(self):
        t = self.fixture
        (t.root / "report.bin").write_bytes(b"repaired candidate")
        with self.assertRaises(GateError): self.advance()
        with self.assertRaises(GateError): self.check()

    def test_cli_next_validate_and_fourth_sidecar(self):
        t = self.fixture
        write_json(t.root / "packet.json", t.packet)
        script = str(Path(__file__).with_name("package_quality_gate.py"))
        common = ["--root", str(t.root), "--packet", "packet.json", "--supporter", "supporter.json",
            "--critic", "critic.json", "--synthesis", "synthesis.json", "--current-base", t.base]
        step = subprocess.run([sys.executable, script, "next", *common], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(step.stdout)["next_action"], "supporter")
        for role in ["supporter", "critic", "synthesis"]:
            write_json(t.root / (role + ".json"), getattr(self, role))
        outgoing = ["report.bin", "packet.json", "supporter.json", "critic.json", "synthesis.json"]
        write_json(t.root / "outgoing.json", outgoing)
        command = [sys.executable, script, "validate", *common, "--publication-list", str(t.root / "outgoing.json")]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)["status"], "SEQUENTIALLY_REVIEWED_READY_FOR_REQUIRED_CI")
        outgoing.append("unreviewed.py")
        write_json(t.root / "outgoing.json", outgoing)
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "HOLD")


if __name__ == "__main__":
    unittest.main()
