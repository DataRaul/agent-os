# P2 manual execution attempt ledger

## Purpose

The P2 comparative evaluation may be executed as many separate fresh conversations. The attempt ledger is the append-only operator record for that mode.

It solves two problems:

- resume safely after interruptions without losing which case/replicate is complete;
- preserve every attempted session instead of silently replacing failed or inconvenient runs.

The ledger does not run a model, inspect the oracle, score results, or admit a reviewer.

## Ledger identity

A ledger is bound to exactly one blinded packet and therefore to one:

- candidate reviewer;
- mode (`baseline` or `reviewer`);
- declared model-configuration ID;
- canonical packet SHA-256.

Top-level `oracle_supplied` and `peer_output_supplied` must both remain `false`.

## Attempt record

Each attempt records:

- unique `attempt_id`;
- exact case ID and replicate;
- actual executor/session reference;
- declared model-configuration ID;
- whether that configuration was confirmed before the run;
- status: `COMPLETED`, `INTERRUPTED`, or `INVALID`;
- explicit oracle/peer-output exposure declarations;
- normalized finding codes for completed attempts only;
- a reason for interrupted/invalid attempts;
- optional non-negative tool-call and latency measurements.

Executor-session references must be unique across attempts.

## Resume and rerun rule

Interrupted or invalid attempts remain in the ledger. A later fresh session may retry that same case/replicate.

Once a case/replicate has a `COMPLETED` attempt, no later attempt for that run is valid. This prevents silent favorable reruns or accidental duplicate completion.

A completed attempt is accepted only when its model configuration was explicitly confirmed and its finding codes are valid for the packet taxonomy.

## Progress summary

Run:

```bash
python scripts/summarize_specialist_reviewer_attempt_ledger.py \
  packet.json attempt-ledger.json
```

The deterministic summary reports:

- total packet runs;
- completed and pending runs;
- attempts recorded;
- interrupted and invalid attempts;
- exact missing case/replicate pairs.

The command is safe to run repeatedly while the 90-chat evaluation progresses.

## Receipt emission

When all 15 runs for that packet are complete:

```bash
python scripts/summarize_specialist_reviewer_attempt_ledger.py \
  packet.json attempt-ledger.json --emit-receipt > receipt.json
```

Receipt emission fails closed while any run remains pending. The emitted receipt uses `schema_version: 2` and `execution_layout: PER_RUN_SESSIONS`, preserving the accepted executor-session reference for every case/replicate.

The resulting baseline and reviewer receipts still pass through `scripts/assemble_specialist_reviewer_eval_result.py`, which requires disjoint baseline/reviewer sessions before scoring input can be assembled.

## Evidence limitation

The ledger records operator declarations and session references. It does not independently prove provider-level isolation, model settings, or the absence of unseen context. Those remain execution-evidence responsibilities.

## Terminal

`P2_MANUAL_ATTEMPT_LEDGER_V1_READY`
