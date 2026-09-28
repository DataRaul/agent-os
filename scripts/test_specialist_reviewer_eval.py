from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCORER = ROOT / "scripts" / "score_specialist_reviewer_eval.py"
CASES = json.loads(
    (ROOT / "benchmarks" / "specialist-reviewer-evaluation" / "cases.json").read_text(
        encoding="utf-8"
    )
)
ORACLE = json.loads(
    (ROOT / "benchmarks" / "specialist-reviewer-evaluation" / "oracle.json").read_text(
        encoding="utf-8"
    )
)

CANDIDATE = "research-validity-reviewer"
REPS = ORACLE["replicates_per_case"]


def candidate_case_ids() -> list[str]:
    return [
        case["id"]
        for case in CASES["cases"]
        if case["reviewer_candidate"] == CANDIDATE
    ]


def run_scorer(payload: dict) -> dict:
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        encoding="utf-8",
        delete=False,
    ) as handle:
        json.dump(payload, handle)
        path = Path(handle.name)
    try:
        completed = subprocess.run(
            [sys.executable, str(SCORER), str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise SystemExit(
                "SCORER_SMOKE_FAIL: "
                + (completed.stderr.strip() or completed.stdout.strip())
            )
        return json.loads(completed.stdout)
    finally:
        path.unlink(missing_ok=True)


def make_payload(mode: str) -> dict:
    runs: list[dict] = []
    for case_id in candidate_case_ids():
        expected = list(ORACLE["expected"][case_id])
        for replicate in range(1, REPS + 1):
            if mode == "eligible":
                if case_id == "rvr-easy-01":
                    baseline = []
                    reviewer = ["TEMPORAL_LEAKAGE"]
                elif case_id == "rvr-normal-02":
                    baseline = expected
                    reviewer = []
                elif case_id == "rvr-deceptive-03":
                    baseline = ["SURVIVORSHIP_BIAS"]
                    reviewer = ["EVALUATION_SELECTION_LEAKAGE"]
                elif case_id == "rvr-control-04":
                    baseline = []
                    reviewer = []
                elif case_id == "rvr-adversarial-05":
                    baseline = ["DENOMINATOR_DRIFT"]
                    reviewer = ["INFERENCE_SCOPE_OVERSTATEMENT"]
                else:
                    raise AssertionError(case_id)
            elif mode == "no-value":
                baseline = expected
                reviewer = []
            else:
                raise AssertionError(mode)

            runs.append(
                {
                    "case_id": case_id,
                    "replicate": replicate,
                    "baseline_finding_codes": baseline,
                    "reviewer_finding_codes": reviewer,
                }
            )

    return {
        "schema_version": 1,
        "suite": "specialist-reviewer-evaluation",
        "candidate_reviewer": CANDIDATE,
        "model_configuration_id": "deterministic-smoke-fixture",
        "reviewer_received_baseline_output": False,
        "runs": runs,
    }


def main() -> None:
    eligible = run_scorer(make_payload("eligible"))
    if eligible.get("disposition") != "ELIGIBLE_FOR_ROLE_IMPLEMENTATION_REVIEW":
        raise SystemExit(f"SCORER_SMOKE_FAIL: unexpected eligible result: {eligible}")
    if eligible.get("combined_expected_recall") != 1.0:
        raise SystemExit("SCORER_SMOKE_FAIL: expected full combined recall")

    no_value = run_scorer(make_payload("no-value"))
    if no_value.get("disposition") != "NO_INCREMENTAL_VALUE_DEMONSTRATED":
        raise SystemExit(f"SCORER_SMOKE_FAIL: unexpected no-value result: {no_value}")

    print("SPECIALIST_REVIEWER_SCORER_SMOKE_PASS")


if __name__ == "__main__":
    main()
