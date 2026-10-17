"""Synthetic contract tests for portable, opt-in plan-first protocol."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from package_quality_gate import GateError, digest, make_packet, validate, write_json
from plan_first_gate import PlanGateError, accepted_receipt, validate_binding
import test_package_quality_gate as fixtures


class PlanFirstTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.GateTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.temp.cleanup)
        t = self.fixture
        t.adapter.update({"review_mode": "SAME_CHAT_SEQUENTIAL", "plan_first": "REQUIRED"})
        t.contract.update({
            "review_mode": "SAME_CHAT_SEQUENTIAL",
            "stage_evidence": {"align": ["checks.txt"], "build_qa": ["checks.txt"]},
            "plan_first": {
                "plan_path": "plan.json", "review_path": "solution_review.json",
                "receipt_path": "prebuild_receipt.json", "trace_path": "trace.json",
            },
        })
        t.contract["required_evidence"] += [
            "plan.json", "solution_review.json", "prebuild_receipt.json", "trace.json"
        ]
        self.plan = {
            "schema_version": 1, "plan_id": "synthetic-plan", "revision": 1,
            "problem": "Slow synthetic report preparation",
            "affected_users": "Report readers", "root_cause": "Repeated manual steps",
            "desired_outcome": "Reliable inspectable report",
            "expected_value": "Less repeated processing work",
            "options": [
                {"id": "simple", "description": "Small local renderer",
                 "pros": "Low operational cost", "cons": "Limited scale"},
                {"id": "large", "description": "External service",
                 "pros": "Elastic scale", "cons": "External dependency"},
            ],
            "selected_option_id": "simple",
            "architecture": "One offline renderer", "tradeoffs": "Limited throughput",
            "estimated_cost": "No incremental spend", "authority": "AUTO + VERIFY",
            "decisions": [{"id": "d1", "decision": "Keep local renderer",
                           "rationale": "Within delegated scope",
                           "expected_consequences": "Low cost with bounded throughput",
                           "material": False, "authority": "AUTO + VERIFY"}],
            "acceptance_criteria": ["Report is readable"], "risks": ["Stale input"],
        }
        self.review = {
            "schema_version": 1, "review_mode": "SAME_CHAT_SEQUENTIAL",
            "session_id": "author", "model": "synthetic",
            "independent": False, "authority": "AUTO + VERIFY",
            "plan_digest": digest(self.plan), "verdict": "PLAN_ACCEPTED",
            "rationale": "Cheaper bounded option satisfies purpose",
            "dimensions": {
                k: "Checked with synthetic source and bounded constraints"
                for k in (
                    "problem_solution_fit", "alternatives", "architecture_tradeoffs",
                    "complexity", "security_compliance", "cost", "failure_scenarios",
                    "acceptance_criteria",
                )
            },
            "findings": [],
        }
        self.trace = {"schema_version": 1, "plan_digest": digest(self.plan),
                      "material_deviations": [],
                      "decisions": [{"id": "d1", "status": "IMPLEMENTED",
                                     "evidence": ["checks.txt"]}]}
        self.write_all()

    def write_all(self):
        t = self.fixture
        for path, doc in [
            ("adapter.json", t.adapter), ("contract.json", t.contract),
            ("plan.json", self.plan), ("solution_review.json", self.review),
            ("prebuild_receipt.json", accepted_receipt(self.plan, self.review)),
            ("trace.json", self.trace),
        ]:
            write_json(t.root / path, doc)
        t.packet = make_packet(t.root, "contract.json", ["report.bin"])
        self.supporter = self.report("supporter", 3, t.packet["candidate_digest"])
        self.critic = self.report("critic", 4, digest(self.supporter))
        self.synthesis = self.report("synthesis", 5, digest(self.critic))
        self.synthesis.update({
            "report_digests": {"supporter": digest(self.supporter),
                               "critic": digest(self.critic)},
            "finding_dispositions": [],
            "stages": ["align", "build_qa", "supporter", "critic", "synthesis"],
            "rationale": "Decision trace and coverage are complete",
            "goal_contribution": "Supports goal g1",
            "next_gate": "REQUIRED_CI",
            "business_value": {
                "problem": self.plan["problem"], "solution": "Local renderer",
                "observed_improvement": "Not yet measured after deployment",
                "verdict": "VALUE_NOT_YET_MEASURED",
                "acceptance_evidence": ["checks.txt"], "observations": [],
                "expected_but_unverified": ["Less repeated work"],
                "remaining_risks": ["Synthetic only"], "owner_actions": [],
                "executive_summary": "Checks passed; business benefit not yet verified",
            },
        })

    def report(self, role, stage, predecessor):
        row = self.fixture.review(role)
        row.update({
            "session_id": "author", "review_mode": "SAME_CHAT_SEQUENTIAL",
            "independent": False, "stage": stage, "predecessor_digest": predecessor,
        })
        return row

    def check(self):
        t = self.fixture
        return validate(t.root, t.packet, self.supporter,
                        self.critic, t.base, self.synthesis)

    def test_accepted_plan_with_value_unmeasured_is_ready_for_ci_only(self):
        result = self.check()
        self.assertEqual(result["status"], "SEQUENTIALLY_REVIEWED_READY_FOR_REQUIRED_CI")
        self.assertFalse(result["required_ci_complete"])
        self.assertFalse(result["independent_review_proven"])

    def test_two_unrelated_repository_adapters_use_same_core(self):
        for name in ("project-a", "project-b"):
            with self.subTest(name=name):
                self.fixture.adapter["project"] = name
                self.fixture.contract["project"] = name
                self.write_all()
                self.assertEqual(self.check()["status"],
                                 "SEQUENTIALLY_REVIEWED_READY_FOR_REQUIRED_CI")

    def test_rejected_and_revised_plans_fail_before_builder(self):
        for outcome in ("PLAN_REVISE", "PLAN_REJECTED", "HUMAN_DECISION_REQUIRED"):
            with self.subTest(outcome=outcome):
                review = dict(self.review, verdict=outcome)
                with self.assertRaises(PlanGateError):
                    accepted_receipt(self.plan, review)

    def test_not_a_human_peer_approval(self):
        self.review["independent"] = True
        with self.assertRaises(PlanGateError):
            accepted_receipt(self.plan, self.review)
        self.review["independent"] = False
        self.review["session_id"] = "invented-peer"
        self.review["plan_digest"] = digest(self.plan)
        write_json(self.fixture.root / "solution_review.json", self.review)
        write_json(self.fixture.root / "prebuild_receipt.json",
                   accepted_receipt(self.plan, self.review))
        with self.assertRaises(PlanGateError):
            make_packet(self.fixture.root, "contract.json", ["report.bin"])

    def test_human_gate_cannot_be_self_approved(self):
        self.plan["authority"] = "HUMAN_GATE"
        self.review["authority"] = "HUMAN_GATE"
        self.review["plan_digest"] = digest(self.plan)
        with self.assertRaises(PlanGateError):
            accepted_receipt(self.plan, self.review)

    def test_plan_revision_and_material_delegation_require_explicit_evidence(self):
        plan = copy.deepcopy(self.plan)
        del plan["revision"]
        with self.assertRaises(PlanGateError):
            accepted_receipt(plan, self.review)
        plan = copy.deepcopy(self.plan)
        plan["decisions"][0]["material"] = True
        review = dict(self.review, plan_digest=digest(plan))
        with self.assertRaises(PlanGateError):
            accepted_receipt(plan, review)
        plan["decisions"][0]["delegation_reference"] = "recorded-owner-delegation-id"
        review["plan_digest"] = digest(plan)
        self.assertEqual(accepted_receipt(plan, review)["status"], "PLAN_ACCEPTED")

    def test_unfrozen_material_delegation_cannot_approve_package(self):
        t = self.fixture
        self.plan["decisions"][0]["material"] = True
        self.plan["decisions"][0]["delegation_reference"] = "owner-consent.txt"
        self.review["plan_digest"] = digest(self.plan)
        self.trace["plan_digest"] = digest(self.plan)
        write_json(t.root / "plan.json", self.plan)
        write_json(t.root / "solution_review.json", self.review)
        write_json(t.root / "prebuild_receipt.json",
                   accepted_receipt(self.plan, self.review))
        write_json(t.root / "trace.json", self.trace)
        with self.assertRaises(PlanGateError):
            make_packet(t.root, "contract.json", ["report.bin"])
        (t.root / "owner-consent.txt").write_text("synthetic delegated authorization")
        t.contract["required_evidence"].append("owner-consent.txt")
        write_json(t.root / "contract.json", t.contract)
        self.assertEqual(make_packet(t.root, "contract.json", ["report.bin"])["schema_version"], 1)

    def test_plan_edit_invalidates_receipt_and_review(self):
        self.plan["architecture"] = "New unapproved architecture"
        write_json(self.fixture.root / "plan.json", self.plan)
        with self.assertRaises(PlanGateError):
            make_packet(self.fixture.root, "contract.json", ["report.bin"])

    def test_missing_material_deviation_reapproval_holds(self):
        self.trace["material_deviations"] = ["Swap primary processing engine"]
        write_json(self.fixture.root / "trace.json", self.trace)
        with self.assertRaises(PlanGateError):
            make_packet(self.fixture.root, "contract.json", ["report.bin"])

    def test_uncovered_decisions_or_unfrozen_evidence_holds(self):
        self.trace["decisions"] = []
        write_json(self.fixture.root / "trace.json", self.trace)
        with self.assertRaises(PlanGateError):
            make_packet(self.fixture.root, "contract.json", ["report.bin"])
        self.trace["decisions"] = [{"id": "d1", "status": "IMPLEMENTED",
                                    "evidence": ["not-reviewed.txt"]}]
        write_json(self.fixture.root / "trace.json", self.trace)
        with self.assertRaises(PlanGateError):
            make_packet(self.fixture.root, "contract.json", ["report.bin"])

    def test_no_business_value_synthesis_holds(self):
        del self.synthesis["business_value"]
        with self.assertRaises(PlanGateError):
            self.check()

    def test_demonstrated_value_requires_measurement(self):
        self.synthesis["business_value"]["verdict"] = "VALUE_DEMONSTRATED"
        with self.assertRaises(PlanGateError):
            self.check()
        self.synthesis["business_value"]["observations"] = [{
            "metric": "Minutes per run", "baseline": 10, "observed": 7,
            "evidence": ["checks.txt"],
        }]
        self.assertEqual(self.check()["status"],
                         "SEQUENTIALLY_REVIEWED_READY_FOR_REQUIRED_CI")

    def test_opt_in_enforced_and_legacy_remains_valid(self):
        t = self.fixture
        t.adapter["plan_first"] = "DISABLED"
        write_json(t.root / "adapter.json", t.adapter)
        with self.assertRaises(PlanGateError):
            make_packet(t.root, "contract.json", ["report.bin"])
        legacy = fixtures.GateTests()
        legacy.setUp()
        try:
            self.assertEqual(legacy.check()["status"], "REVIEWED_READY_FOR_REQUIRED_CI")
        finally:
            legacy.temp.cleanup()

    def test_prebuild_cli_receipt_generation(self):
        t = self.fixture
        output = t.root / "created-receipt.json"
        script = str(Path(__file__).with_name("plan_first_gate.py"))
        result = subprocess.run([
            sys.executable, script, "--root", str(t.root),
            "--plan", "plan.json", "--review", "solution_review.json",
            "--output", "created-receipt.json",
        ], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)["status"], "PLAN_ACCEPTED_PREBUILD_ONLY")
        self.assertEqual(json.loads(output.read_text()),
                         accepted_receipt(self.plan, self.review))


if __name__ == "__main__":
    unittest.main()
