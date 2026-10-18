"""Synthetic tests: generic two-lane portfolio. No real source or held-recipe replay."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from portfolio_priority_gate import PortfolioGateError, validate


class PortfolioGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.roadmap = "# Roadmap\n## P0: Deliver useful output\n## P2: Explore experimental sources\n"
        (self.root / "ROADMAP.md").write_text(self.roadmap)
        self.policy = {
            "schema_version": 1, "roadmap_path": "ROADMAP.md",
            "roadmap_sha256": hashlib.sha256(self.roadmap.encode()).hexdigest(),
            "primary_lane": "delivery", "owner_steering_source": "standing-owner-decision",
            "lanes": {"delivery": {"priority": "P0", "branch_policy": "MAIN_DELIVERY"},
                      "research": {"priority": "P2", "branch_policy": "ISOLATED"}},
            "limits": {"unchanged_blocker_checks": 1, "cycles_without_value": 1}}
        self.decision = {
            "schema_version": 1, "lane_id": "delivery", "selected_priority": "P0",
            "roadmap_sha256": self.policy["roadmap_sha256"],
            "milestone_line": "## P0: Deliver useful output",
            "owner_steering_source": "standing-owner-decision",
            "business_metric": "usable units delivered",
            "next_primary_action": "Implement next eligible source",
            "route": "CONTINUE", "blocks_primary": False,
            "unchanged_blocker_checks": 0, "cycles_without_value": 0,
            "material_progress": True, "blocker": "",
            "strategic_critic": {
                "roadmap_challenge": "P0 selected against roadmap",
                "higher_priority_alternative": "None evidenced",
                "opportunity_cost": "One bounded development cycle",
                "lane_routing_challenge": "Delivery stays primary",
                "value_checkpoint_challenge": "Measured units required",
                "disposition": "ALIGNED"}}
        self.persist()

    def persist(self):
        (self.root / "policy.json").write_text(json.dumps(self.policy))
        (self.root / "decision.json").write_text(json.dumps(self.decision))

    def check(self):
        self.persist()
        return validate(self.root, "policy.json", "decision.json")

    def test_valid_primary(self):
        self.assertEqual(self.check()["route"], "CONTINUE")

    def test_detects_stale_roadmap(self):
        self.policy["roadmap_sha256"] = "0" * 64
        with self.assertRaises(PortfolioGateError): self.check()

    def test_no_progress_escalates(self):
        self.decision.update({"material_progress": False, "cycles_without_value": 1})
        with self.assertRaises(PortfolioGateError): self.check()
        self.decision.update({"route": "ISOLATE_SECONDARY", "secondary_lane": "research",
                              "owner_escalation": {"issue": "No value", "options": "Split or park",
                                                   "recommendation": "Split", "owner_action": "NONE"}})
        self.assertEqual(self.check()["route"], "ISOLATE_SECONDARY")

    def test_second_unchanged_blocker_is_hold(self):
        self.decision.update({"unchanged_blocker_checks": 2, "blocker": "Input unavailable"})
        with self.assertRaises(PortfolioGateError): self.check()

    def test_critic_can_veto(self):
        self.decision["strategic_critic"]["disposition"] = "HOLD"
        with self.assertRaises(PortfolioGateError): self.check()

    def test_secondary_cannot_block_primary(self):
        self.decision.update({"lane_id": "research", "selected_priority": "P2",
                              "milestone_line": "## P2: Explore experimental sources",
                              "blocks_primary": True})
        with self.assertRaises(PortfolioGateError): self.check()
        self.decision["blocks_primary"] = False
        self.assertEqual(self.check()["lane_id"], "research")

    def test_missing_critic_opportunity_cost(self):
        del self.decision["strategic_critic"]["opportunity_cost"]
        with self.assertRaises(PortfolioGateError): self.check()

    def test_unsafe_paths(self):
        with self.assertRaises(PortfolioGateError):
            validate(self.root, "../private/policy.json", "decision.json")


if __name__ == "__main__":
    unittest.main()
