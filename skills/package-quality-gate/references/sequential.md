# Same-chat sequential workflow

Use only when both adapter and current package contract select `review_mode: SAME_CHAT_SEQUENTIAL`. This is an owner-selected review method, not fallback permission to waive another project's independent gate.

1. Align internally before substantive work. Read current instructions, goal, contract and lane checkpoint; preserve latest owner steering and remaining budget. Record authority and acceptance criteria.
2. Build and run relevant QA. Freeze the exact candidate, including tests, required evidence, contract, goal and adapter. Alignment and build evidence must be in the frozen required evidence, with each mapped to a criterion.
3. Run `next` with the frozen packet, fresh base and current-round report paths. Execute its returned Supporter pass in this chat: inspect actual deliverables, completeness, integration and goal contribution. Use the constructive checklist in `supporter.md` without its separate-session requirement. Record actual session/model, `review_mode`, `independent: false`, `stage: 3` and `predecessor_digest` equal to the packet digest. Give substantive criterion evidence and findings, not an automatic PASS.
4. Run `next` again. Execute its Critic pass against the same exact candidate: reread artifacts and original acceptance criteria, challenge assumptions, counterexamples, failure paths and contradictory evidence. Use `critic.md` without claiming a fresh or isolated context. Record `stage: 4` and predecessor equal to the canonical Supporter report digest. Context is shared; do not claim blindness.
5. Run `next` again. Synthesize the exact two reports: reconcile findings, dispositions and evidence; check every criterion and goal contribution; keep missing evidence or unresolved material findings on HOLD. Use the common review fields with `role: synthesis`, `stage: 5`, the actual author session, `independent: false`, predecessor equal to the Critic report digest, and `report_digests` for both. Add ordered `stages: [align, build_qa, supporter, critic, synthesis]`, substantive `rationale`, `goal_contribution`, and `next_gate: REQUIRED_CI`.
6. Run `next` and then `validate --synthesis <path>` with the exact outgoing publication inventory and fresh base. Readiness is `SEQUENTIALLY_REVIEWED_READY_FOR_REQUIRED_CI`; proceed through existing authorized PR/CI/merge and lane-specific checkpoint rules. Readiness does not establish merge, deployment, research validity or owner acceptance.

Run this sequence automatically within the active turn at each substantive package boundary. A clear continue/resume resumes the earliest unmet stage; do not stop for ritual permission or return a proposal when execution is authorized. The coordinator drives the workflow with tools; `next` selects a stage but cannot run an LLM, inject instructions into another chat, or continue after the chat stops. Repository instructions must be loaded on takeover. Unsupported hosts must report their exact limitation.

Both passes retain mandatory Knowledge Core provenance and the common coverage/finding contract. Synthesis retains it too. Reports remain sidecars outside their own hashed subject. Compute report digests with `package_quality_gate.digest` (canonical JSON), not file hashes. The checker separately returns report file hashes for publication verification.

The contract requires `stage_evidence: {align: [<required evidence paths>], build_qa: [<required evidence paths>]}`. Synthesis requires `finding_dispositions` containing each Supporter finding then each Critic finding in report order, with exact `role`, `id`, `disposition`, and `resolution_evidence` (empty when absent). Use `[]` only when both reports have no findings. Explain why each disposition is justified; preserving the fields alone does not establish truth.

For a repair, retain the failed reports in the lane's evidence history, increment the existing bounded review round, update legitimate QA evidence, and refreeze. Use new-round report paths and repeat both passes plus synthesis against the final candidate. Any candidate/base/contract/goal/adapter/evidence change invalidates old reports. Report edits invalidate successor links. Never rename the same session to simulate independence, reset budget, reuse old independent reports as sequential evidence, or use synthesis to waive a material defect.

Example after freeze:

```bash
python scripts/package_quality_gate.py next --root /project --packet packet.json --supporter supporter.json --critic critic.json --synthesis synthesis.json --current-base EXACT_FRESH_BASE
python scripts/package_quality_gate.py validate --root /project --packet packet.json --supporter supporter.json --critic critic.json --synthesis synthesis.json --current-base EXACT_FRESH_BASE --publication-list /scratch/outgoing.json
```

The ordered report chain is mechanically checked but self-reported; it cannot prove mental independence, execution chronology, reasoning quality or semantic truth. Independent-session mode remains separately selectable. No paid API, scheduled Actions or persistent reviewer service is introduced.
