"""Isolated three-lane Git lease and checkpoint failure-path controls."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from lane_handover import prepare, verify, GateError


def dump(value):
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


class LaneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.index = "docs/handovers/INDEX.json"
        value = {"schema_version": 1, "project": "sample-project", "branch": "state", "lanes": {}, "quality_adapter": "config/quality.json"}
        self.write("config/quality.json", dump({"project": "sample-project", "max_rounds": 2}))
        for lane in ["alpha", "beta", "gamma"]:
            goal = f"docs/goals/{lane}.json"; self.write(goal, dump({"goal": lane}))
            ref = {"path": goal, "sha256": hashlib.sha256((self.root / goal).read_bytes()).hexdigest()}
            row = {"current": f"docs/handovers/{lane}/CURRENT.json", "previous": f"docs/handovers/{lane}/PREVIOUS.json", "goal_ref": ref, "aliases": [lane + "-alias"]}
            value["lanes"][lane] = row
            doc = {"schema_version": 1, "project": value["project"], "lane_id": lane, "lane_goal_ref": ref, "sequence": 0,
                   "legacy": {"authority": {"hold": True}},
                   "package_quality": {"schema_version": 1, "package_ref": "initial", "status": "RECONCILE_REQUIRED", "next_action": "Read live sources", "predecessor_sha256": "0" * 64,
                                       "goal_ref": ref, "last_evidence": [], "reviews": [], "unfinished_criteria": [], "failures": ["known hold"], "decisions": ["preserve scope"], "constraints": ["no paid calls"], "budget": {"round": 1, "max_rounds": 2, "usage": "unknown"}}}
            # Deliberate whitespace tests exact PREVIOUS byte preservation.
            self.write(row["current"], dump(doc) + " \n"); self.write(row["previous"], dump(doc))
        self.write(self.index, dump(value))
        self.git("init", "-b", "state"); self.git("config", "user.name", "Test"); self.git("config", "user.email", "test@example.invalid")
        self.git("add", "."); self.git("commit", "-m", "baseline")
        self.base = self.git("rev-parse", "HEAD").strip()

    def tearDown(self):
        self.temp.cleanup()

    def write(self, path, content):
        p = self.root / path; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(content)

    def git(self, *args, input=None, env=None, check=True):
        result = subprocess.run(["git", "-C", str(self.root), *args], input=input, capture_output=True, text=True, env=env)
        if check:
            self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout if check else result

    def plan(self, lane="alpha", head=None):
        path = f"docs/handovers/{lane}/CURRENT.json"; old = (self.root / path).read_bytes(); doc = json.loads(old)
        doc["sequence"] += 1; doc["package_quality"]["predecessor_sha256"] = hashlib.sha256(old).hexdigest()
        actual = head or self.base
        return prepare(self.root, self.index, lane, doc, actual, actual, hashlib.sha256(old).hexdigest())

    def commit_plan(self, plan, base, expected):
        with tempfile.TemporaryDirectory() as temp:
            env = {**os.environ, "GIT_INDEX_FILE": str(Path(temp) / "index")}
            self.git("read-tree", base, env=env)
            for row in plan["writes"]:
                blob = self.git("hash-object", "-w", "--stdin", input=row["content"]).strip()
                self.git("update-index", "--add", "--cacheinfo", row["mode"] + "," + blob + "," + row["path"], env=env)
            tree = self.git("write-tree", env=env).strip()
            commit = self.git("commit-tree", tree, "-p", base, input="lane checkpoint [skip ci]\n").strip()
            update = self.git("update-ref", "refs/heads/state", commit, expected, check=False)
            return commit, update

    def test_three_concurrent_lane_snapshots_reconcile_without_lost_updates(self):
        plans = {lane: self.plan(lane) for lane in ["alpha", "beta", "gamma"]}
        first, result = self.commit_plan(plans["alpha"], self.base, self.base)
        self.assertEqual(result.returncode, 0)
        with self.assertRaises(GateError):
            verify(self.root, plans["beta"], first)
        _, stale = self.commit_plan(plans["beta"], self.base, self.base)
        self.assertNotEqual(stale.returncode, 0)
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), first)
        latest = first
        for lane in ["beta", "gamma"]:
            # Own unchanged checkpoint is reread; publisher builds only two writes on latest tree.
            plan = self.plan(lane, latest); verify(self.root, plan, latest)
            latest, result = self.commit_plan(plan, latest, latest); self.assertEqual(result.returncode, 0)
        for lane in ["alpha", "beta", "gamma"]:
            current = self.git("show", latest + f":docs/handovers/{lane}/CURRENT.json")
            previous = self.git("show", latest + f":docs/handovers/{lane}/PREVIOUS.json")
            self.assertEqual(json.loads(current)["sequence"], 1)
            self.assertEqual(json.loads(previous)["sequence"], 0)
            self.assertEqual(previous, (self.root / f"docs/handovers/{lane}/CURRENT.json").read_text())
        self.assertEqual(self.git("show", latest + ":" + self.index), (self.root / self.index).read_text())

    def test_wrong_lane_and_unknown_alias_rejected(self):
        plan = self.plan(); self.assertEqual(verify(self.root, plan, self.base)["lane_id"], "alpha")
        row = plan["writes"][0]; doc = json.loads(row["content"]); doc["lane_id"] = "beta"
        with self.assertRaises(GateError):
            prepare(self.root, self.index, "alpha", doc, self.base, self.base, plan["expected_current_sha256"])
        with self.assertRaises(GateError):
            prepare(self.root, self.index, "unknown", doc, self.base, self.base, plan["expected_current_sha256"])

    def test_shared_or_cross_lane_plan_write_rejected(self):
        for path in [self.index, "docs/handovers/beta/CURRENT.json", "docs/handovers/CURRENT.json"]:
            plan = self.plan(); plan["writes"][1]["path"] = path
            with self.assertRaises(GateError): verify(self.root, plan, self.base)

    def test_same_lane_advance_rejected(self):
        plan = self.plan(); self.write("docs/handovers/alpha/CURRENT.json", plan["writes"][0]["content"])
        with self.assertRaises(GateError): verify(self.root, plan, self.base)

    def test_budget_and_history_retained(self):
        old_path = self.root / "docs/handovers/alpha/CURRENT.json"; old = old_path.read_bytes()
        for mutate in [lambda d: d["package_quality"]["budget"].update(max_rounds=3),
                       lambda d: d["package_quality"].update(failures=[]),
                       lambda d: d["legacy"]["authority"].clear()]:
            doc = json.loads(old); doc["package_quality"]["predecessor_sha256"] = hashlib.sha256(old).hexdigest(); mutate(doc)
            with self.assertRaises(GateError):
                prepare(self.root, self.index, "alpha", doc, self.base, self.base, hashlib.sha256(old).hexdigest())

    def test_goal_registry_and_plan_tampering_rejected(self):
        plan = self.plan()
        changed = copy.deepcopy(plan); changed["writes"][1]["content"] += "\n"
        with self.assertRaises(GateError): verify(self.root, changed, self.base)
        self.write("docs/goals/alpha.json", dump({"goal": "other"}))
        with self.assertRaises(GateError): verify(self.root, plan, self.base)

    def test_symlink_and_ambiguous_alias_rejected(self):
        index = json.loads((self.root / self.index).read_text()); index["lanes"]["beta"]["aliases"] = ["alpha"]
        self.write(self.index, dump(index))
        with self.assertRaises(GateError): self.plan()
        index["lanes"]["beta"]["aliases"] = []; self.write(self.index, dump(index))
        p = self.root / "docs/handovers/alpha/CURRENT.json"; p.rename(p.with_name("actual.json")); p.symlink_to("actual.json")
        with self.assertRaises(GateError): self.plan()


if __name__ == "__main__":
    unittest.main()
