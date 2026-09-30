"""Collect independent per-run P2 execution fragments into one packet-bound receipt.

The collector is deterministic and oracle-free. It is intended for manual or other
execution environments where each case/replicate is run in a separate fresh session.
It validates fragment identity, packet binding, session uniqueness, and finding-code
shape, then emits a schema-v2 PER_RUN_SESSIONS receipt accepted by the main assembler.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


class FragmentError(ValueError):
    pass


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FragmentError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise FragmentError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise FragmentError(f"{path} must contain a JSON object")
    return data


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FragmentError(f"{label} must be a non-empty string")
    return value


def validate_packet(packet: dict) -> None:
    if packet.get("schema_version") != 1:
        raise FragmentError("packet schema_version must equal 1")
    if packet.get("suite") != "specialist-reviewer-evaluation":
        raise FragmentError("packet suite mismatch")
    if packet.get("mode") not in {"baseline", "reviewer"}:
        raise FragmentError("packet mode invalid")
    require_string(packet.get("candidate_reviewer"), "candidate_reviewer")
    require_string(packet.get("model_configuration_id"), "model_configuration_id")

    contract = packet.get("independence_contract")
    if not isinstance(contract, dict):
        raise FragmentError("packet independence contract missing")
    for key in ("oracle_supplied", "peer_output_supplied", "hidden_reasoning_requested"):
        if contract.get(key) is not False:
            raise FragmentError(f"packet independence violation: {key}")
    if contract.get("same_model_configuration_required_for_pair") is not True:
        raise FragmentError("packet configuration-pair requirement missing")

    output = packet.get("output_contract")
    if not isinstance(output, dict) or output.get("format") != "finding_codes_only":
        raise FragmentError("packet output contract invalid")
    taxonomy = output.get("allowed_finding_codes")
    if (
        not isinstance(taxonomy, list)
        or not taxonomy
        or len(taxonomy) != len(set(taxonomy))
        or any(not isinstance(code, str) or not code for code in taxonomy)
    ):
        raise FragmentError("packet finding-code taxonomy invalid")

    runs = packet.get("runs")
    if not isinstance(runs, list) or not runs:
        raise FragmentError("packet runs must be non-empty")
    seen: set[tuple[str, int]] = set()
    for run in runs:
        if not isinstance(run, dict):
            raise FragmentError("packet run must be object")
        case_id = require_string(run.get("case_id"), "case_id")
        replicate = run.get("replicate")
        if not isinstance(replicate, int) or isinstance(replicate, bool) or replicate < 1:
            raise FragmentError(f"packet {case_id} replicate invalid")
        run_key = (case_id, replicate)
        if run_key in seen:
            raise FragmentError(f"packet duplicate run: {run_key}")
        seen.add(run_key)


def validate_fragment(packet: dict, fragment: dict) -> tuple[tuple[str, int], dict]:
    if fragment.get("schema_version") != 1:
        raise FragmentError("fragment schema_version must equal 1")
    if fragment.get("suite") != "specialist-reviewer-evaluation":
        raise FragmentError("fragment suite mismatch")
    for key in ("candidate_reviewer", "mode", "model_configuration_id"):
        if fragment.get(key) != packet.get(key):
            raise FragmentError(f"fragment {key} mismatch")
    if fragment.get("packet_sha256") != canonical_sha256(packet):
        raise FragmentError("fragment packet digest mismatch")
    if fragment.get("oracle_supplied") is not False:
        raise FragmentError("fragment must declare oracle_supplied=false")
    if fragment.get("peer_output_supplied") is not False:
        raise FragmentError("fragment must declare peer_output_supplied=false")

    case_id = require_string(fragment.get("case_id"), "fragment case_id")
    replicate = fragment.get("replicate")
    if not isinstance(replicate, int) or isinstance(replicate, bool) or replicate < 1:
        raise FragmentError(f"fragment {case_id} replicate invalid")
    session_id = require_string(
        fragment.get("executor_session_id"),
        f"fragment {case_id}/{replicate} executor_session_id",
    )

    taxonomy = set(packet["output_contract"]["allowed_finding_codes"])
    codes = fragment.get("finding_codes")
    if (
        not isinstance(codes, list)
        or len(codes) != len(set(codes))
        or any(not isinstance(code, str) or code not in taxonomy for code in codes)
    ):
        raise FragmentError(f"fragment {case_id}/{replicate} finding_codes invalid")

    result = {
        "case_id": case_id,
        "replicate": replicate,
        "executor_session_id": session_id,
        "finding_codes": codes,
    }
    for key in ("tool_calls", "latency_ms"):
        value = fragment.get(key)
        if value is not None:
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                raise FragmentError(f"fragment {case_id}/{replicate} {key} invalid")
            result[key] = value

    return (case_id, replicate), result


def collect(packet: dict, fragments: list[dict]) -> dict:
    validate_packet(packet)
    expected_order = [(run["case_id"], run["replicate"]) for run in packet["runs"]]
    expected = set(expected_order)
    by_run: dict[tuple[str, int], dict] = {}
    sessions: set[str] = set()

    for fragment in fragments:
        if not isinstance(fragment, dict):
            raise FragmentError("fragment must contain a JSON object")
        run_key, result = validate_fragment(packet, fragment)
        if run_key not in expected:
            raise FragmentError(f"fragment run not present in packet: {run_key}")
        if run_key in by_run:
            raise FragmentError(f"duplicate fragment for run: {run_key}")
        session_id = result["executor_session_id"]
        if session_id in sessions:
            raise FragmentError(
                f"per-run fragments must use distinct executor sessions: {session_id}"
            )
        sessions.add(session_id)
        by_run[run_key] = result

    missing = [run_key for run_key in expected_order if run_key not in by_run]
    if missing:
        raise FragmentError(
            "missing fragment runs: "
            + ", ".join(f"{case_id}/{replicate}" for case_id, replicate in missing)
        )

    return {
        "schema_version": 2,
        "suite": "specialist-reviewer-evaluation",
        "candidate_reviewer": packet["candidate_reviewer"],
        "mode": packet["mode"],
        "model_configuration_id": packet["model_configuration_id"],
        "packet_sha256": canonical_sha256(packet),
        "execution_layout": "PER_RUN_SESSIONS",
        "oracle_supplied": False,
        "peer_output_supplied": False,
        "runs": [by_run[run_key] for run_key in expected_order],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("fragments", type=Path, nargs="+")
    args = parser.parse_args()

    try:
        result = collect(
            load_json(args.packet),
            [load_json(path) for path in args.fragments],
        )
    except FragmentError as exc:
        raise SystemExit(f"REVIEWER_FRAGMENT_FAIL: {exc}") from None

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
