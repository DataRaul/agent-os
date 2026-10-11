# Package quality gate — experimental V1

This project-selected pilot does not promote specialist reviewers into the existing admission registry or claim measured reliability gains. It composes semantic review and verified completion with alignment and goal lineage.

## Components

The skill and role references are procedures. The aligner normally runs within the coordinator; supporter and critic run as separate sessions when invoked. They are not persistent services. The Python checker verifies identity, stages, coverage, provenance and budgets; it cannot verify truth, forged identities or actual object reading. Existing project gates and CI remain controlling.

Root instructions invoke the protocol per bounded package. Thin adapters pin the shared implementation and declare local boundaries. Private overlays select projects, budgets and knowledge routes; the public layer never fetches private state. No paid API or scheduled Actions is introduced. Publication tools remain unrestricted: enforcement is procedural, not exclusive.

## Invocation

Use versioned goal JSON, per-package contract JSON, candidate/evidence files, packet JSON and two report JSONs. Reports and packet are sidecars outside the subject; preserve history.

```bash
python scripts/package_quality_gate.py freeze --root /project --contract docs/package_quality/contracts/pkg.json --output docs/package_quality/evidence/pkg/packet.json --paths path/to/change path/to/artifact
python scripts/package_quality_gate.py validate --root /project --packet docs/package_quality/evidence/pkg/packet.json --supporter docs/package_quality/evidence/pkg/supporter.json --critic docs/package_quality/evidence/pkg/critic.json --current-base EXACT_LIVE_BASE --publication-list /scratch/outgoing-paths.json
python scripts/package_quality_gate.py rotate --root /project --current docs/handovers/lane/CURRENT.json --next /scratch/next.json --expected-current SHA256 --output /scratch/rotation.json
```

Use `--git-base` on freeze/validate in real checkouts to reject omitted changed/untracked paths. For connectors supply exact outgoing tree entry paths to `--publication-list`; only frozen candidate paths and the three validated sidecars may be published. Verify each actual tree entry's bytes and mode against the packet immediately before mutation. Explicit deletions use `--deletions`. Binary files hash as bytes. V1 supports regular files only: reject absolute paths, traversal and all symlinks, including linked parents. Hashes bind bytes and `git_modes` binds executable/non-executable Git mode; changing either invalidates the packet. Submodules and alternate Git object types require a future explicit contract.

Goal, contract, adapter, evidence, candidate and base bind the packet digest. Any changes invalidate reports. The live base must come from a fresh authoritative read; the checker makes no network calls. Publish with an expected-head lease. Never describe a supplied base as independently fetched by the checker.

## Formats

Goal: `schema_version: 1`, `goal_id`, `revision`, `outcome`, `purpose`, nonempty `success_criteria` (unique `id`, `description`), `constraints`, `intent_provenance`, `changes`.

Contract: `schema_version: 1`, `project`, `lane_id`, `package_id`, `base_commit`, `author_session_id`, `goal_path`, `adapter_path`, `intent_provenance`, `outcome`, `contribution`, nonempty `scope`, `non_goals`, `inputs`, `criteria` (unique `id`, `description`, nonempty `goal_criteria`), nonempty `required_evidence` paths, `mandatory_knowledge_domains`, `authority` (`AUTO` or `AUTO + VERIFY` to publish), `human_decisions`, `assumptions`, `dependencies`, `next_action`, `stop_boundary`, `budget` (`round`, `max_rounds`, `usage` string, `unknown` if unavailable). Resume never resets budgets.

Adapter: `schema_version: 1`, `project`, `mode: PROCEDURAL_PILOT`, `max_rounds`, `constraints`, optional `required_checks` (criterion IDs).

Review: `schema_version: 1`, `role` (`supporter`/`critic`), distinct `session_id`, `model`, `candidate_digest`, `verdict` (`PASS`, `NEEDS_REPAIR`, `HOLD`), `knowledge` (records with `domain`, exact 40-character `commit`, `object`, `applied_rule`, `criterion_id`), `coverage` (one record per criterion: `criterion_id`, `result: PASS`, nonempty `evidence` paths from required evidence), `findings` (unique `id`, `kind`, `material` boolean, `evidence`, `remedy`, `disposition`, `resolution_evidence` paths). A material finding passes only if RESOLVED with hashed required resolution evidence. Optional findings may be DEFERRED. Both reviewers record all mandatory knowledge domains and may add others.

`validate` returns `REVIEWED_READY_FOR_REQUIRED_CI` and report hashes. This does not mean merged, deployed, research-valid or owner-accepted. Critics initially receive no peer verdict.

## Checkpoints

Add `package_quality` to the existing checkpoint, retaining all local fields. Include goal (`path`, `sha256`), package reference, status, last evidence, reviews, unfinished criteria, failures, decisions, budget, constraints, next action and `predecessor_sha256`. `rotate` validates and prepares CURRENT/PREVIOUS contents; it does not mutate the authoritative pair. Publish both in one Git tree/commit and atomically update the branch with a lease. On conflict reread and reconcile. Rolling pointers plus Git history at pinned commits preserve lineage. Concurrent lanes need separate pointers or explicit single-writer coordination.

Checkpoint budgets require integer `round` and `max_rounds` plus `usage`. Rotation rejects dropped existing nested object fields, erased failure/decision/constraint history, and decreased/widened same-package round budgets. Append new resolutions rather than deleting history. A new package may start its own review rounds under the unchanged adapter cap; carry other resource ceilings and unresolved authority forward. Field-name preservation does not verify updated values or prove semantic honesty: the coordinator/reviewers still verify actual dispositions and sourced revisions. Existing live-state arrays may change when fresh evidence justifies it; this checker is not a generic immutable-state policy.

## Pilot and limits

Run only in selected projects. Honor stronger local repair/stop rules. Budget exhaustion holds work. Review calls add usage and elapsed time; telemetry may be unknown. An exclusive publisher with isolated credentials is a separate future implementation.

Before wider rollout compare baseline and protocol on identical frozen clean, deceptive and failing packages, with hidden outcomes and thresholds chosen first. Record missed defects, false findings, unnecessary questions, drift, rework, sessions, time, observable usage and Actions. Unit tests and self-review do not complete this comparative pilot or the historical reviewer benchmark.
