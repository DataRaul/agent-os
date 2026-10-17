# Plan-first solution review — portable opt-in V1

## Purpose and adoption

Bring important solution decisions forward without replacing the existing Aligner, Builder/QA, frozen candidate, Supporter, Critic, Synthesis, CI, authorized publication or lane checkpoint controls. This is a public, repository-neutral evidence contract; local knowledge, goal, authority, tests, CI and deployment remain with each consumer. No private dependency or new agent is required.

A consumer opts in **per package** by selecting both `review_mode: SAME_CHAT_SEQUENTIAL` and `plan_first: REQUIRED` in its local package-quality adapter, and adding a `plan_first` path object to its local contract. Missing `plan_first` on the adapter means `DISABLED` and existing packages are unchanged. In V1 a plan-first package uses an actual same-chat identity and `independent: false`; no human peer review or authenticated pre-build chronology is claimed.

## Execution sequence

1. **Align:** use the existing goal and Knowledge Core/Aligner to identify business problem, affected users, root cause, intended outcome, expected value, acceptance criteria, constraints and decision authority.
2. **Plan:** record at least two options, selected approach, trade-offs, costs, risks, architecture and individual implementation decisions with IDs.
3. **Pre-Build Solution Review:** challenge fit, alternatives, architecture/trade-offs, complexity, security/compliance, cost, failure scenarios and acceptance criteria. Record substantive reasons and any findings. Outcomes: `PLAN_ACCEPTED`, `PLAN_REVISE`, `PLAN_REJECTED`, or `HUMAN_DECISION_REQUIRED`. Only accepted, delegated decisions can pass. Keep superseded/rejected records in local history.
4. **Receipt:** before substantive Builder work, invoke `python scripts/plan_first_gate.py --root /project --plan path/to/plan.json --review path/to/solution_review.json --output path/to/prebuild_receipt.json`. This checks the accepted plan and records the exact canonical plan/review digests. It is a procedural receipt: it cannot prove when the review happened, who authored it, or whether a human granted authority.
5. **Build + QA:** implement only the accepted plan. Link each planned decision to frozen evidence in a trace, with status `IMPLEMENTED` or `JUSTIFIED_NONMATERIAL_DEVIATION` and a rationale for the latter. Material changes stop: revise/re-accept the plan and regenerate the receipt. Record all earlier findings; do not silently erase review budgets.
6. **Freeze and review:** put the plan, solution review, prebuild receipt and decision trace in the contract's `required_evidence`. The existing package quality gate freezes their exact bytes alongside the contract, adapter, goal, QA evidence and code. Preserve same-chat Supporter, Critic and Synthesis and the current per-package review limits.
7. **Business value:** Synthesis reports the original problem, delivered solution, acceptance evidence, observed improvement (or not yet measured), projected benefits, remaining risks, owner actions and a `VALUE_*` verdict. `VALUE_DEMONSTRATED` and `VALUE_PARTIALLY_DEMONSTRATED` require numeric observations with frozen evidence; the checker cannot establish real-world causality or measurement reliability.
8. **Existing downstream controls:** mandatory quality validator, CI, authorized PR/merge/deployment and isolated CURRENT/PREVIOUS checkpoint rotation remain required. A package-ready verdict is not deployment or business acceptance.

## Repository adapter contract

Local adapter fields (existing required fields are unchanged):

```json
{
  "schema_version": 1,
  "project": "example",
  "mode": "PROCEDURAL_PILOT",
  "review_mode": "SAME_CHAT_SEQUENTIAL",
  "plan_first": "REQUIRED",
  "max_rounds": 2,
  "constraints": ["No paid services"],
  "required_checks": []
}
```

Local package contract addition:

```json
{
  "review_mode": "SAME_CHAT_SEQUENTIAL",
  "plan_first": {
    "plan_path": "docs/package_quality/plans/p1.json",
    "review_path": "docs/package_quality/plans/p1-review.json",
    "receipt_path": "docs/package_quality/plans/p1-receipt.json",
    "trace_path": "docs/package_quality/plans/p1-trace.json"
  }
}
```

All four local paths **must** be added to that contract's `required_evidence`. The example snippets are additions to the already-existing adapter and contract schemas; they are not complete replacements. Local CI commands, domain adapters, execution permissions and checkpoint paths are not interpreted by Agent OS. Only project owners authorize local adoption.

## Evidence schema (V1)

- **Plan:** `schema_version: 1`, `plan_id`, `revision` (positive integer), `problem`, `affected_users`, `root_cause`, `desired_outcome`, `expected_value`, `options` (at least two distinct objects with `id`, `description`, `pros`, `cons`), `selected_option_id`, `architecture`, `tradeoffs`, `estimated_cost`, `authority` (`AUTO` or `AUTO + VERIFY`), `decisions` (nonempty unique `id`, `decision`, `rationale`, `expected_consequences`, `authority`, explicit boolean `material`; material decisions additionally require a source-locatable `delegation_reference`), `acceptance_criteria` (nonempty string array), `risks` (string array).
- **Review:** `schema_version: 1`, `review_mode: SAME_CHAT_SEQUENTIAL`, `session_id` (actual author session), `model`, `independent: false`, `authority`, `plan_digest` (canonical JSON SHA-256), `verdict`, `rationale`, `dimensions` (all eight documented snake-case dimensions with substantive text), `findings` (array of `id`, `finding`, `disposition`; material findings also require `material` and `resolution` when resolved). Unsupported authority claims and unresolved material findings fail closed.
- **Receipt:** generated by `plan_first_gate.py`, not manually self-issued. Its canonical digests, approval status, session, authority and explicit self-reported assurance must still match unchanged plan/review. This is not cryptographic attestation of chronology or external authorization.
- **Trace:** `schema_version: 1`, `plan_digest`, `decisions` (exactly one row per plan decision: `id`, `status`, nonempty `evidence` path array, and `rationale` for nonmaterial deviations), `material_deviations: []`. Evidence must be in frozen `required_evidence`. Material deviations stop even if the author asserts they were justified.
- **Business value within Synthesis:** `business_value` with `problem`, `solution`, `observed_improvement`, `executive_summary`, `verdict`, `acceptance_evidence`, `observations` (numeric `baseline`/`observed` plus `metric` and frozen `evidence`), `expected_but_unverified`, `remaining_risks`, `owner_actions`. Verdicts: `VALUE_DEMONSTRATED`, `VALUE_PARTIALLY_DEMONSTRATED`, `VALUE_NOT_YET_MEASURED`, `VALUE_NOT_DEMONSTRATED`. Never report the expected value as an observation.

## Portability gate and pilot adoption

Use one versioned implementation in Agent OS and only local JSON adapters in two different synthetic consumers (automated tests), then **three real bounded roadmap packages** across explicitly opting-in consumers. At least two distinct real repositories must demonstrate the same shared implementation with no duplicated core code. The portability gate stays **PENDING** until those real pilots show equivalent behavior, correct local authority boundaries, package-specific CI, privacy isolation and sound checkpoint behavior. Do not migrate old/unfinished packages merely to manufacture a pilot.

Track baseline and pilot: lead time, owner attention, plan revisions/rejections, implementation rework, review rounds, defects/escapes, CI resource use, model usage (unknown when unavailable), and evidence of business outcomes. The earlier speaker's figures are hypotheses, not forecasts or acceptance thresholds. Seek Knowledge Core Consultant and Project Coach evaluation and identify two improvements. Final adoption verdict is `ACCEPT`, `IMPROVE_AND_RETEST` or `REJECT`; passing synthetic tests alone is insufficient.

## Restrictions

Preserve existing budgets and historical findings, same-chat identity honesty, candidate freezing, pinned validation, required CI and parallel lane checkpoint isolation. Public Agent OS never pulls local private knowledge or acts on private repositories; costs remain within authorized existing services. Changes to this public contract are versioned and consumers adopt a reviewed exact commit explicitly. No automatic deployment, no global switch, no new paid API, and no pretense that procedural JSON gates prevent bypass by arbitrary publication tools.
