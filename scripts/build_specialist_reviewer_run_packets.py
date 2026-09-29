"""Build blinded public-safe run packets for P2 specialist reviewer evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "benchmarks" / "specialist-reviewer-evaluation" / "cases.json"
REPLICATES_PER_CASE = 3

REVIEWER_OBJECTIVES = {
    "research-validity-reviewer": (
        "Independently inspect the research scenario for material validity, "
        "data-design, temporal, denominator, selection, and inference-scope failures."
    ),
    "evidence-provenance-reviewer": (
        "Independently inspect the scenario for evidence provenance, freshness, "
        "candidate alignment, source hierarchy, and unresolved authority conflicts."
    ),
    "runtime-postcondition-verifier": (
        "Independently inspect the scenario for runtime postcondition mismatch, "
        "partial state, checkpoint ordering, version drift, and authority-gate failures."
    ),
}


def die(message: str) -> None:
    raise SystemExit(f"REVIEWER_PACKET_FAIL: {message}")


def load_cases() -> dict:
    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("suite") != "specialist-reviewer-evaluation":
        die("invalid benchmark case document")
    return data


def load_skill(skill_id: str) -> dict[str, str]:
    path = ROOT / "skills" / skill_id / "SKILL.md"
    if not path.is_file():
        die(f"baseline skill missing: {skill_id}")
    return {
        "skill_id": skill_id,
        "path": str(path.relative_to(ROOT)),
        "content": path.read_text(encoding="utf-8"),
    }


def build_packet(candidate: str, mode: str, model_configuration_id: str) -> dict:
    data = load_cases()
    candidates = data.get("candidates", {})
    if candidate not in candidates or candidate not in REVIEWER_OBJECTIVES:
        die(f"unknown reviewer candidate: {candidate}")
    if mode not in {"baseline", "reviewer"}:
        die(f"unsupported mode: {mode}")
    if not model_configuration_id.strip():
        die("model configuration ID must be non-empty")

    cases = [
        case
        for case in data.get("cases", [])
        if isinstance(case, dict) and case.get("reviewer_candidate") == candidate
    ]
    if len(cases) != 5:
        die(f"{candidate} must have exactly five benchmark cases")

    runs = []
    for case in cases:
        for replicate in range(1, REPLICATES_PER_CASE + 1):
            runs.append(
                {
                    "case_id": case["id"],
                    "replicate": replicate,
                    "level": case["level"],
                    "scenario": case["scenario"],
                }
            )

    packet = {
        "schema_version": 1,
        "suite": "specialist-reviewer-evaluation",
        "candidate_reviewer": candidate,
        "mode": mode,
        "model_configuration_id": model_configuration_id,
        "independence_contract": {
            "oracle_supplied": False,
            "peer_output_supplied": False,
            "hidden_reasoning_requested": False,
            "same_model_configuration_required_for_pair": True,
        },
        "output_contract": {
            "format": "finding_codes_only",
            "allowed_finding_codes": data["finding_code_taxonomy"],
            "unsupported_findings_forbidden": True,
        },
        "runs": runs,
    }

    if mode == "baseline":
        packet["instructions"] = (
            "Act as the capable primary-agent baseline. Use only the supplied scenario "
            "and baseline Agent OS skills. Return only supported normalized finding codes."
        )
        packet["baseline_skills"] = [
            load_skill(skill_id) for skill_id in candidates[candidate]["baseline_skills"]
        ]
    else:
        packet["instructions"] = (
            "Act as an independent specialist reviewer. Do not assume a baseline answer "
            "exists. Return only supported normalized finding codes."
        )
        packet["reviewer_objective"] = REVIEWER_OBJECTIVES[candidate]
        packet["reviewer_received_baseline_output"] = False

    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", choices=sorted(REVIEWER_OBJECTIVES))
    parser.add_argument("mode", choices=("baseline", "reviewer"))
    parser.add_argument("--model-configuration-id", required=True)
    args = parser.parse_args()

    packet = build_packet(args.candidate, args.mode, args.model_configuration_id)
    print(json.dumps(packet, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
