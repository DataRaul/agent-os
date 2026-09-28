from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "benchmarks" / "specialist-reviewer-evaluation" / "cases.json"
ORACLE_PATH = ROOT / "benchmarks" / "specialist-reviewer-evaluation" / "oracle.json"


def die(message: str) -> None:
    raise SystemExit(f"REVIEWER_EVAL_FAIL: {message}")


def load(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"missing file: {path}")
    except json.JSONDecodeError as exc:
        die(f"invalid JSON in {path}: {exc}")


def require_nonnegative_optional(run: dict, key: str) -> int | float | None:
    value = run.get(key)
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        die(f"{key} must be a non-negative number when supplied")
    return value


def main() -> None:
    if len(sys.argv) != 2:
        die("usage: python scripts/score_specialist_reviewer_eval.py result.json")

    result_path = Path(sys.argv[1])
    result = load(result_path)
    cases_doc = load(CASES_PATH)
    oracle = load(ORACLE_PATH)

    if not isinstance(result, dict):
        die("result must be a JSON object")
    if result.get("schema_version") != 1:
        die("unsupported result schema_version")
    if result.get("suite") != "specialist-reviewer-evaluation":
        die("wrong result suite")
    if result.get("reviewer_received_baseline_output") is not False:
        die("reviewer_received_baseline_output must be false")
    model_config = result.get("model_configuration_id")
    if not isinstance(model_config, str) or not model_config.strip():
        die("model_configuration_id is required")

    candidate = result.get("candidate_reviewer")
    candidates = cases_doc.get("candidates", {})
    if candidate not in candidates:
        die(f"unknown candidate_reviewer: {candidate!r}")

    taxonomy = set(cases_doc.get("finding_code_taxonomy", []))
    all_cases = cases_doc.get("cases", [])
    candidate_cases = {
        case["id"]: case
        for case in all_cases
        if isinstance(case, dict) and case.get("reviewer_candidate") == candidate
    }
    if not candidate_cases:
        die(f"no benchmark cases found for {candidate}")

    expected_map = oracle.get("expected", {})
    min_reps = oracle.get("minimum_replicates_per_case")
    policy = oracle.get("admission_policy", {})
    if not isinstance(min_reps, int) or isinstance(min_reps, bool) or min_reps < 1:
        die("oracle minimum_replicates_per_case invalid")

    runs = result.get("runs")
    if not isinstance(runs, list) or not runs:
        die("runs must be a non-empty array")

    seen_pairs: set[tuple[str, int]] = set()
    replicates: Counter[str] = Counter()
    incremental_cases: set[str] = set()
    incremental_expected_observations = 0
    baseline_true_observations = 0
    reviewer_true_observations = 0
    combined_true_observations = 0
    baseline_false_positive_observations = 0
    reviewer_false_positive_observations = 0
    reviewer_control_false_positive_observations = 0
    overhead = defaultdict(float)
    overhead_counts = Counter()

    for run in runs:
        if not isinstance(run, dict):
            die("each run must be an object")
        case_id = run.get("case_id")
        replicate = run.get("replicate")
        if case_id not in candidate_cases:
            die(f"result includes unknown or wrong-candidate case: {case_id!r}")
        if not isinstance(replicate, int) or isinstance(replicate, bool) or replicate < 1:
            die(f"{case_id}: replicate must be a positive integer")
        pair = (case_id, replicate)
        if pair in seen_pairs:
            die(f"duplicate case/replicate: {case_id} replicate {replicate}")
        seen_pairs.add(pair)
        replicates[case_id] += 1

        baseline_codes = run.get("baseline_finding_codes")
        reviewer_codes = run.get("reviewer_finding_codes")
        for label, codes in (("baseline_finding_codes", baseline_codes), ("reviewer_finding_codes", reviewer_codes)):
            if not isinstance(codes, list) or any(not isinstance(code, str) for code in codes):
                die(f"{case_id}: {label} must be an array of strings")
            if len(codes) != len(set(codes)):
                die(f"{case_id}: {label} contains duplicates")
            unknown = set(codes) - taxonomy
            if unknown:
                die(f"{case_id}: {label} contains unknown codes: {sorted(unknown)}")

        expected = set(expected_map.get(case_id, []))
        baseline = set(baseline_codes)
        reviewer = set(reviewer_codes)
        combined = baseline | reviewer

        baseline_true_observations += len(baseline & expected)
        reviewer_true_observations += len(reviewer & expected)
        combined_true_observations += len(combined & expected)

        baseline_false_positive_observations += len(baseline - expected)
        reviewer_false_positive_observations += len(reviewer - expected)
        if not expected:
            reviewer_control_false_positive_observations += len(reviewer)

        incremental = (reviewer & expected) - baseline
        if incremental:
            incremental_cases.add(case_id)
            incremental_expected_observations += len(incremental)

        for key in ("baseline_tool_calls", "reviewer_tool_calls", "baseline_latency_ms", "reviewer_latency_ms"):
            value = require_nonnegative_optional(run, key)
            if value is not None:
                overhead[key] += value
                overhead_counts[key] += 1

    missing_cases = sorted(set(candidate_cases) - set(replicates))
    under_replicated = {
        case_id: count
        for case_id, count in replicates.items()
        if count < min_reps
    }
    complete = not missing_cases and not under_replicated

    min_cases = policy.get("minimum_incremental_distinct_cases", 0)
    min_observations = policy.get("minimum_incremental_expected_observations", 0)
    max_fp = policy.get("maximum_reviewer_false_positive_observations", 0)
    require_control_clean = bool(policy.get("require_control_false_positive_free", False))

    eligible = (
        complete
        and len(incremental_cases) >= min_cases
        and incremental_expected_observations >= min_observations
        and reviewer_false_positive_observations <= max_fp
        and (not require_control_clean or reviewer_control_false_positive_observations == 0)
    )

    disposition = (
        policy.get("eligible_disposition", "ELIGIBLE_FOR_ROLE_IMPLEMENTATION_REVIEW")
        if eligible
        else policy.get("noneligible_disposition", "NO_INCREMENTAL_VALUE_DEMONSTRATED")
    )

    output = {
        "suite": "specialist-reviewer-evaluation",
        "candidate_reviewer": candidate,
        "model_configuration_id": model_config,
        "complete": complete,
        "missing_cases": missing_cases,
        "under_replicated": under_replicated,
        "minimum_replicates_per_case": min_reps,
        "baseline_true_observations": baseline_true_observations,
        "reviewer_true_observations": reviewer_true_observations,
        "combined_true_observations": combined_true_observations,
        "incremental_distinct_cases": sorted(incremental_cases),
        "incremental_expected_observations": incremental_expected_observations,
        "baseline_false_positive_observations": baseline_false_positive_observations,
        "reviewer_false_positive_observations": reviewer_false_positive_observations,
        "reviewer_control_false_positive_observations": reviewer_control_false_positive_observations,
        "reported_overhead_totals": dict(overhead),
        "reported_overhead_sample_counts": dict(overhead_counts),
        "disposition": disposition,
        "note": "Eligibility permits role-implementation review only; it does not automatically admit a reviewer or grant authority."
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
