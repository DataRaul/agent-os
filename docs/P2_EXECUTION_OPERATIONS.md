# P2 manual execution operations

Status: `OPERATIONS_V1_READY`

This layer helps execute and resume the 90 manual specialist-reviewer conversations without running any model, reading the scoring oracle, changing benchmark packets, or granting reviewer admission.

## Scope

`scripts/specialist_reviewer_execution_ops.py` provides deterministic, local-only operations over the already pinned run packets and append-only attempt ledgers.

It can:

- initialize a packet-bound empty attempt ledger;
- import one or more manual attempt records without discarding earlier interrupted or invalid attempts;
- report completed/pending counts and the exact next pending case/replicate;
- emit the existing schema-v2 receipt only after all packet runs are complete;
- validate a baseline/reviewer pair before scoring, including exact candidate/model alignment and disjoint executor sessions across all attempts;
- produce a machine-readable overall progress manifest across the three candidate pairs, with the canonical 90-run target and next pending runs.

It cannot:

- execute a model;
- call a paid API;
- read or infer the scoring oracle;
- modify benchmark case content or packet hashes;
- fabricate missing session references;
- discard interrupted or invalid attempts;
- accept a rerun after a case/replicate is already completed;
- score evidence;
- admit a reviewer.

## Canonical workflow

Create an empty ledger for a packet:

```bash
python scripts/specialist_reviewer_execution_ops.py init-ledger \
  baseline-packet.json baseline-ledger.json
```

Import a manually recorded attempt:

```bash
python scripts/specialist_reviewer_execution_ops.py import-attempts \
  baseline-packet.json baseline-ledger.json attempt.json
```

The import file may be one attempt object, `{"attempt": {...}}`, or `{"attempts": [{...}, ...]}`. The resulting ledger is revalidated before it is written.

Show progress and the exact next pending run:

```bash
python scripts/specialist_reviewer_execution_ops.py status \
  baseline-packet.json baseline-ledger.json
```

Emit a packet receipt after all 15 runs are complete:

```bash
python scripts/specialist_reviewer_execution_ops.py emit-receipt \
  baseline-packet.json baseline-ledger.json > baseline-receipt.json
```

Validate one candidate's baseline/reviewer evidence before assembly/scoring:

```bash
python scripts/specialist_reviewer_execution_ops.py validate-pair \
  baseline-packet.json baseline-ledger.json \
  reviewer-packet.json reviewer-ledger.json
```

Create the overall progress manifest:

```bash
python scripts/specialist_reviewer_execution_ops.py overall \
  --pair research-baseline-packet.json research-baseline-ledger.json research-reviewer-packet.json research-reviewer-ledger.json \
  --pair provenance-baseline-packet.json provenance-baseline-ledger.json provenance-reviewer-packet.json provenance-reviewer-ledger.json \
  --pair runtime-baseline-packet.json runtime-baseline-ledger.json runtime-reviewer-packet.json runtime-reviewer-ledger.json
```

A complete overall manifest requires exactly three distinct candidate pairs and exactly 90 completed runs. `pre_score_ready=true` means only that the deterministic execution-evidence preconditions represented here are satisfied. It does not mean the reviewer passed the benchmark or is admitted.

## Attempt record minimum

Each attempt remains governed by `docs/P2_MANUAL_EXECUTION_LEDGER.md`. Every real attempt needs a unique `attempt_id` and a unique real `executor_session_id`. Completed attempts require the exact declared model configuration and normalized finding codes. Interrupted and invalid attempts remain in the ledger with a reason.

The baseline and reviewer modes must never reuse an executor session, including interrupted or invalid attempts.

## Pin preservation

These operations consume packet JSON as input. They deliberately do not regenerate packets and therefore do not silently move the evaluation to a newer public main SHA. The original benchmark pin, prompts, packet contents and packet digests remain the execution authority for the active P2 comparative evaluation.

## Validation

CI runs `scripts/test_specialist_reviewer_execution_ops.py` in addition to the existing packet, receipt, fragment and attempt-ledger tests. The operations tests cover resumable interruption preservation, exact next-run reporting, session reuse rejection, baseline/reviewer session separation, model-configuration mismatch rejection, 90-run aggregation and incomplete-evidence fail-closed behavior.
