# P2 specialist reviewer evaluation

## Goal

Determine whether any planned specialist reviewer earns its coordination cost beyond the established P1 baseline:

```text
one capable primary agent
+ relevant public Agent OS skills
+ deterministic validation
```

The existence of a reviewer concept is not evidence that a separate agent is useful. P2 measures incremental value before any candidate reviewer is promoted into `agents/`.

## Candidates

| Candidate | Baseline skills used in its benchmark |
| --- | --- |
| `research-validity-reviewer` | `research-data-integrity`, `provenance-freshness` |
| `evidence-provenance-reviewer` | `provenance-freshness`, `verified-completion` |
| `runtime-postcondition-verifier` | `verified-completion`, `state-mutation-idempotency`, `authority-boundary-review` |

These are candidate role IDs only. They are not implemented reviewer agents.

## Benchmark structure

Public-safe synthetic cases live in:

- `benchmarks/specialist-reviewer-evaluation/cases.json`
- `benchmarks/specialist-reviewer-evaluation/oracle.json`

The case file contains only the material presented to the evaluated runs. The oracle contains expected finding codes and admission policy and must not be supplied to the evaluated model/agent.

The benchmark is public, so it is not a secret holdout. The separation is procedural: runner inputs must exclude the oracle.

## Blinded run packets

`scripts/build_specialist_reviewer_run_packets.py` materializes one mode at a time from `cases.json` only. It does not read `oracle.json`. Baseline packets embed the exact public skill texts listed for the candidate; reviewer packets contain only the independent specialist objective. Both modes contain the same five cases, three replicates per case, model-configuration ID, normalized finding-code taxonomy, and an explicit independence contract.

Example:

```bash
python scripts/build_specialist_reviewer_run_packets.py research-validity-reviewer baseline --model-configuration-id MODEL_CONFIG > baseline.json
python scripts/build_specialist_reviewer_run_packets.py research-validity-reviewer reviewer --model-configuration-id MODEL_CONFIG > reviewer.json
```

Execute baseline and reviewer work independently with the same declared model configuration. A whole 15-run packet may use one isolated executor session, or each case/replicate may use its own fresh session. Do not merge baseline and reviewer contexts, expose one side's output to the other, or add the oracle to either execution context. The packet builder is an input-preparation utility only; it does not call a model, score results, or implement a specialist reviewer.

## Independent execution receipts

Actual comparative evidence must come from separately executed baseline and reviewer sessions, not from a single process fabricating both sides. Each execution produces a receipt bound to the exact blinded packet by canonical SHA-256.

Required receipt fields include:

- candidate, mode, and model-configuration ID matching the packet;
- exact `packet_sha256`;
- `oracle_supplied: false`;
- `peer_output_supplied: false`;
- one ordered result row for every packet case/replicate with normalized finding codes;
- optional non-negative tool-call and latency measurements.

Receipt schema v1 represents one executor session for the whole packet and requires one top-level `executor_session_id`. Receipt schema v2 represents `PER_RUN_SESSIONS`: each result row carries its own `executor_session_id`, every run in that receipt must use a distinct session, and baseline/reviewer session sets must be disjoint.

For manual or other one-run-per-session execution, save each completed run as an oracle-free fragment and collect the 15 fragments deterministically:

```bash
python scripts/collect_specialist_reviewer_run_fragments.py \
  baseline-packet.json baseline-fragment-*.json > baseline-receipt.json
python scripts/collect_specialist_reviewer_run_fragments.py \
  reviewer-packet.json reviewer-fragment-*.json > reviewer-receipt.json
```

Each fragment records packet identity, case/replicate identity, the actual executor-session reference, normalized finding codes, and truthful oracle/peer-output declarations. The collector rejects missing/duplicate runs, duplicate session references, packet/configuration mismatch, invalid finding codes, and declared exposure. It does not inspect `oracle.json` and does not prove provider-level model settings; the operator remains responsible for preserving evidence that the declared configuration was actually used.

After the two receipts are ready, assemble them with:

```bash
python scripts/assemble_specialist_reviewer_eval_result.py \
  baseline-packet.json baseline-receipt.json \
  reviewer-packet.json reviewer-receipt.json > combined-result.json
python scripts/score_specialist_reviewer_eval.py combined-result.json
```

The assembler does not read `oracle.json`. It rejects packet-digest mismatch, model-configuration mismatch, different case/replicate coverage, invalid finding codes, declared oracle/peer-output exposure, duplicate per-run sessions, and any baseline/reviewer session overlap. These checks strengthen evidence provenance but do not prove physical or provider-level session isolation or model-setting truth; the executor remains responsible for truthful receipt declarations.

## Fair comparison protocol

For one candidate reviewer:

1. Select that candidate's five cases.
2. Use the same declared model/configuration for baseline and reviewer runs.
3. Run exactly three independent replicates per case, as fixed by the oracle.
4. Baseline run receives the case plus the listed P1 skills. No separate reviewer is used.
5. Reviewer run receives the same case and relevant evidence independently.
6. Do not provide the reviewer the baseline answer, author confidence, hidden reasoning, or oracle.
7. Record each side independently as a packet-bound execution receipt containing only normalized finding codes plus optional tool-call/latency measurements.
8. Assemble the two receipts with `scripts/assemble_specialist_reviewer_eval_result.py`; the assembler must accept them without weakening any independence invariant.
9. Score the assembled result with:

```bash
python scripts/score_specialist_reviewer_eval.py path/to/combined-result.json
```

The scorer combines baseline and independent reviewer findings only for measurement. The reviewer itself must remain independent.

## Result shape

```json
{
  "schema_version": 1,
  "suite": "specialist-reviewer-evaluation",
  "candidate_reviewer": "research-validity-reviewer",
  "model_configuration_id": "same-config-for-baseline-and-reviewer",
  "reviewer_received_baseline_output": false,
  "runs": [
    {
      "case_id": "rvr-easy-01",
      "replicate": 1,
      "baseline_finding_codes": [],
      "reviewer_finding_codes": [],
      "baseline_tool_calls": 0,
      "reviewer_tool_calls": 0,
      "baseline_latency_ms": 0,
      "reviewer_latency_ms": 0
    }
  ]
}
```

Tool-call and latency values are optional. When present they must be non-negative.

## Admission rule

The initial public admission rule is deliberately conservative and simple. A candidate becomes **eligible for role implementation review**, not automatically admitted, only if all of the following hold:

- every candidate case has exactly three valid replicates;
- the independent reviewer finds expected material issues missed by baseline in at least two distinct cases;
- there are at least three incremental expected-finding observations across case/replicate pairs;
- the combined baseline-plus-reviewer expected-finding recall is at least 80%;
- the reviewer adds at most one false-positive observation across the full run;
- reviewer control cases remain false-positive free.

The scorer reports `ELIGIBLE_FOR_ROLE_IMPLEMENTATION_REVIEW` or `NO_INCREMENTAL_VALUE_DEMONSTRATED`.

Eligibility still does not create execution authority or require that a reviewer be added. Semantic review should also consider tool/latency overhead and whether the observed gain is likely to generalize.

## Scorer verification

CI runs `scripts/test_specialist_reviewer_eval.py` after repository validation. The smoke test exercises both an eligible fixture and a no-incremental-value fixture so the scorer's two terminal dispositions are executed rather than merely syntax-checked.

CI also runs `scripts/test_specialist_reviewer_run_packets.py`. That check verifies exact five-case × three-replicate coverage, identical baseline/reviewer case material, candidate baseline-skill loading, reviewer independence flags, and that the packet builder never reads `oracle.json`.

CI additionally runs `scripts/test_specialist_reviewer_execution_receipts.py` and `scripts/test_specialist_reviewer_run_fragments.py`. These checks verify packet binding, legacy single-session compatibility, per-run session provenance, disjoint baseline/reviewer sessions, no oracle/peer-output exposure, exact run identity, finding-code taxonomy enforcement, complete 15-run collection, and fail-closed rejection of tampered or incomplete evidence.

Smoke fixtures are constructed at test time and are not benchmark results or evidence for reviewer admission.

## Failure boundaries

Do not admit a reviewer because:

- it agrees with the baseline;
- it uses more words;
- it repeats findings already made by the baseline;
- it has access to the oracle;
- it sees the baseline output before independent review;
- it increases apparent recall by generating many unsupported findings;
- extra replicates are added until a favorable result appears;
- one unusually favorable case drives the result.

Do not copy private project incidents or fixtures into this benchmark.

## Terminal condition

P2 blinded evaluation infrastructure is ready when:

- benchmark cases and oracle validate deterministically;
- the scorer's eligible and no-value paths pass deterministic smoke tests;
- blinded baseline/reviewer run packets are generated without oracle access;
- packet symmetry, replicate coverage, skill loading, and independence invariants pass deterministically;
- packet-bound baseline/reviewer execution receipts can be assembled only when declared sessions are disjoint and packet/configuration identity matches;
- one-run-per-session fragments can be collected without collapsing or inventing executor-session provenance;
- receipt/fragment tampering, missing/duplicate runs, session reuse, and declared oracle/peer-output exposure fail closed;
- CI passes on the exact main candidate.

This establishes `BLINDED_RUN_PACKET_V1_READY__EXECUTION_RECEIPT_V1_READY__PER_RUN_COLLECTION_V1_READY`, not reviewer admission. Reviewer roles remain evaluation-gated until actual independent comparative runs demonstrate incremental value.
