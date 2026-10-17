# Package quality gate — experimental V1

This project-selected pilot does not promote specialist reviewers into the existing admission registry or claim measured reliability gains. It composes semantic review and verified completion with alignment and goal lineage.

## Components

The skill and role references are procedures. The aligner normally runs within the coordinator; supporter and critic run as separate sessions when invoked. They are not persistent services. The Python checker verifies identity, stages, coverage, provenance and budgets; it cannot verify truth, forged identities or actual object reading. Existing project gates and CI remain controlling.

An explicitly selected `SAME_CHAT_SEQUENTIAL` adapter/contract instead uses one active chat: alignment → build/QA → constructive Supporter pass → Critic pass → final synthesis. See `skills/package-quality-gate/references/sequential.md`. This mode provides structured self-review with honest identity; it is not independent review. Missing `review_mode` retains the existing `INDEPENDENT_SESSIONS` behavior. A mode mismatch holds old contracts until explicitly migrated and refrozen. Consumer selection is local, not portfolio-wide.

The `next` command returns the earliest missing pass (3 Supporter, 4 Critic, 5 synthesis), verifies preceding reports and final-candidate freshness, or returns readiness. It neither fabricates feedback nor launches models. The active coordinator executes the returned pass and invokes it again; this is an in-chat workflow trigger, not a background host hook. Repositories cannot inject instructions into already-running chats.

Sequential reports include `review_mode: SAME_CHAT_SEQUENTIAL`, `session_id` equal to the actual author session, `independent: false`, integer `stage` and `predecessor_digest`. Supporter links to the frozen packet digest; Critic links to the canonical Supporter report digest; synthesis links to the canonical Critic digest and both exact `report_digests`. Synthesis uses the common coverage/provenance/finding fields plus ordered `stages`, substantive `rationale`, `goal_contribution` and `next_gate: REQUIRED_CI`. `validate --synthesis <path>` permits the fourth validated sidecar and returns `SEQUENTIALLY_REVIEWED_READY_FOR_REQUIRED_CI` with `assurance: PROCEDURAL_SAME_CHAT_PASSES`. Neither result proves independence, semantic truth or completed CI. Hash-linked order is self-reported evidence, not authenticated chronology.

Sequential contracts require `stage_evidence` with nonempty `align` and `build_qa` path lists drawn from frozen `required_evidence`. Synthesis also requires `finding_dispositions`: every Supporter finding followed by every Critic finding in report order, each with `role`, `id`, `disposition` and `resolution_evidence` (empty when absent). This prevents silent removal or reinterpretation of pass findings during synthesis. Reports may still share blind spots; performance improvement remains unmeasured.

Root instructions invoke the protocol per bounded package. Thin adapters pin the shared implementation and declare local boundaries. Private overlays select projects, budgets and knowledge routes; the public layer never fetches private state. No paid API or scheduled Actions is introduced. Publication tools remain unrestricted: enforcement is procedural, not exclusive.

## Optional pre-build decision and business-value gate

An opt-in local adapter may select `plan_first: REQUIRED` together with `SAME_CHAT_SEQUENTIAL`. It invokes the shared offline pre-build receipt validator before Builder, requires a plan-to-implementation decision trace in frozen evidence, and requires business-value synthesis after the existing Supporter/Critic passes. It adds no review session, does not reset the existing review budget, and does not alter the downstream CI, publication or checkpoint controls. Without the explicit selection all existing package behavior remains unchanged. See [Plan-first portability](PLAN_FIRST_PORTABILITY.md) for accepted-plan, review, receipt, trace and value fields, evidence contracts, portability/pilot gates and self-reported limits.

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

## Concurrent lanes

A selecting project may supply `/project/docs/handovers/INDEX.json` with schema_version 1, project, branch, quality_adapter and lanes. Each stable slug has its own CURRENT/PREVIOUS paths at `docs/handovers/<lane>/`, an exact goal_ref (path and SHA-256), and optional unique aliases. Registrations are source-controlled; ordinary checkpoint writes never edit the index or another lane. Each full checkpoint records project, canonical lane_id and lane_goal_ref. An explicit reviewed bootstrap/migration creates missing pairs; preserve original predecessor bytes and historical constraints.

`lane_handover.py prepare` receives the freshly fetched state-branch head, expected lane CURRENT SHA-256 and next complete checkpoint. It checks identity, goal, history and budgets and emits only the two permitted byte-bound writes. `verify` reconstructs this exact plan against the supplied fresh head/current/registry. These offline checks neither fetch nor publish and cannot authenticate caller-supplied freshness.

The caller builds the tree from that exact latest branch head and updates the ref with expected_sha, no force, one commit and `[skip ci]`. A moved head rejects publication. Reread before the single bounded reconciliation: if another lane advanced, its latest tree must be retained while only this unchanged lane pair is rebuilt; if this lane advanced, reconcile completed work and budget instead of replaying stale state. Verify the pair and untouched other-lane entries afterward. An ambiguous result is reconciled against live files before a retry. No background lock service, automatic successor or new authority is introduced.

Example commands:

```bash
python scripts/lane_handover.py prepare --root /project --registry docs/handovers/INDEX.json --lane alpha --next docs/package_quality/evidence/pkg/next.json --snapshot-head EXACT_HEAD --expected-head EXACT_HEAD --expected-current CURRENT_SHA256 --output docs/package_quality/evidence/pkg/lane-plan.json
python scripts/lane_handover.py verify --root /project --plan docs/package_quality/evidence/pkg/lane-plan.json --live-head FRESH_HEAD
```

The seven isolated controls include three initially concurrent snapshots, real Git update-ref lease rejection and two-write rebasing that preserves all three lane histories, same-lane staleness, cross-lane writes, changed goals/registry/plan bytes, history/budget loss, symlinks and alias ambiguity. Live connector identity/publication remains separately verified by consumers.
