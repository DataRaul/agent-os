---
name: package-quality-gate
description: Align a bounded package to its authorized goal, then obtain constructive and fresh critical reviews before publication. Use only in workflows with an explicit project adapter selecting this experimental protocol, including resume and handover; do not activate across unrelated projects or for individual tool calls.
---

# Package quality gate

Read the selecting project's adapter and current instructions first. This is an experimental procedure, not a globally admitted reviewer or a tool permission grant.

Select `review_mode` from the adapter and contract. Missing mode means `INDEPENDENT_SESSIONS` for compatibility. If explicitly selected as `SAME_CHAT_SEQUENTIAL`, follow [same-chat sequence](references/sequential.md) instead of steps 4–6 below. Run the passes within the current chat without asking the owner to start another chat. Keep one actual session identity; never describe sequential passes as independent. All other evidence, scope, budget, CI and checkpoint gates remain controlling.

1. Apply [alignment](references/aligner.md) before substantive work. Reconcile live project state, versioned goal, latest steering and checkpoint. Retrieve settled context before asking questions; record a compact contract. If and only if a consumer adapter selects `plan_first: REQUIRED`, follow the opt-in [plan-first contract](../../docs/PLAN_FIRST_PORTABILITY.md): plan alternatives, challenge the solution and generate an accepted-plan receipt *before* Builder. Carry the exact receipt and complete decision trace into frozen required evidence. Missing/changed accepted plans, human-gated decisions or material deviations hold building/publication; existing packages without selection remain unchanged.
2. Build one bounded deliverable and run inexpensive relevant checks. Explain criterion → deliverable → evidence → contribution to the goal. Keep existing evidence, privacy, cost and human gates controlling.
3. Freeze the exact candidate with `scripts/package_quality_gate.py freeze`. Include all publication changes, untracked deliverables, outputs, adapter, contract, goal and required evidence. Keep review sidecars outside the subject to avoid self-referential hashes.
4. Launch a separate session using [supporter](references/supporter.md). Integrate only justified in-scope corrections. Changed files or criteria invalidate the candidate; freeze and recheck again.
5. Launch a fresh session using [critic](references/critic.md), initially without the supporter verdict or author's reasoning. Give it the exact final candidate, criteria and independent source locators.
6. Resolve findings with evidence; obtain both final-candidate reports. Run `validate` with the freshly reconciled base SHA and exact outgoing publication list. Unresolved material findings, unavailable independent sessions/required knowledge, exhausted budget or stale identity hold publication. A renamed self-check is not independent review.
7. Publish through existing authorized paths after validation. Run required CI and verify the resulting target. For a selecting adapter with a lane registry, use `scripts/lane_handover.py prepare` and `verify`: rotate only that lane’s CURRENT/PREVIOUS. Otherwise use `rotate`. Publish the exact pair on the latest tree in one commit with an expected-head lease; an unrelated-lane conflict requires a fresh tree, while a same-lane conflict requires explicit reconciliation. Honor stronger project stop rules.

Review each bounded deliverable package, including research, notebook evidence, documents and visualizations. Shorten tiny packets; do not launch reviewers for cells, tool calls, internal steps or review reports. Clear continues reuse the goal under remaining authority; they do not reset budgets or waive blockers.

Use the checker as a mechanical evidence check, not proof of semantic truth, authentic reviewer identity or non-bypassable enforcement. JSON session identifiers are self-reported; unrestricted publication tools can bypass this procedural gate. See `docs/PACKAGE_QUALITY_GATE.md` for formats and pilot measurement. Additional sessions consume existing account usage; no paid API, scheduled workflow or automatic successor chat is required.
