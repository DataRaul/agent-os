# Portable portfolio priority, lane router and value checkpoint — V1

**Status:** prospective opt-in proposal. This public Agent OS contract is repository-neutral. It grants no authority to publish, merge, run a background agent, access paid services, or change existing frozen package receipts.

## Four approved controls
1. **Portfolio priority gate before alignment:** reconcile the locally pinned roadmap, owner steering and registered primary/secondary lanes before choosing a package. A selected P2 research task cannot assert authority to block independent P0 delivery.
2. **Non-blocking lane router:** use one P0 `MAIN_DELIVERY` lane and isolated `ISOLATED` secondary lanes. On a material blocker select `CONTINUE`, `ISOLATE_SECONDARY`, `PARK` or `ESCALATE_OWNER`. Shared database writers stay serialized under the consumer's rules; separate branches do not imply simultaneous unattended execution.
3. **Strategic Critic requirement:** challenge roadmap fit, higher-priority alternative, opportunity cost, lane choice and actual value checkpoint, *in addition* to correctness, security and rights. A Critic HOLD cannot authorize continuation.
4. **Continuous value/blocker checkpoint:** before repeating a stalled task, record measurable progress, unchanged blocker checks, cycles without material value, next primary action and owner escalation. Exceeding the policy limit rejects further `CONTINUE`.

## Usage
Consumer adds a dedicated `portfolio_priority` adapter selecting `scripts/portfolio_priority_gate.py` **at an exact reviewed Agent OS commit and file SHA-256**, with local policy path and `portfolio_gate_new_packages` prospective. Run:
```
python /exact/pinned/agent-os/scripts/portfolio_priority_gate.py \
  --root /consumer --policy config/portfolio_priority_policy.json \
  --decision docs/package_quality/plans/<package>-portfolio-decision.json
```
Freeze both policy and decision evidence for selected **new** packages alongside the pre-build plan. Execute before the Aligner, at material scope changes, and at every next-cycle boundary. It is *not* a substitute for plan-first acceptance, ordered Supporter/Critic/Synthesis, rights checks, CI or reviewed merge. Never mutate original adapters, past contracts or exhausted review budgets.

## Decision contract
`policy`: `schema_version:1`, `roadmap_path`, SHA-256 of exact roadmap bytes, `owner_steering_source`, `primary_lane`, `lanes` mapping each lane to `priority` and `branch_policy`, and nonnegative `limits.unchanged_blocker_checks` / `limits.cycles_without_value`.
`decision`: `schema_version:1`, lane/priority and exact roadmap hash + literal milestone, steering identity, business metric, next primary action, route, `blocks_primary:false`, progress and repeat counters, blocker and five nonempty `strategic_critic` challenges with disposition. Stalled work requires owner escalation and routing away from unchanged `CONTINUE`. An isolation decision identifies a registered secondary lane.

## Assurance boundary
Hash and schema validation prove that declared evidence was consistently captured at a known roadmap version. They **cannot prove that the roadmap choice is strategically optimal**, that a declared metric was independently measured or that a human actually approved an escalation. Treat self-reported Critic output as non-independent. Explicit owner decisions, current live repository state and local rights/financial/data gates outrank any receipt.

## Validation
Run `python -m unittest discover -s scripts -p 'test_portfolio_priority_gate.py'` with standard-library Python. All test inputs are synthetic, unrelated to any real stalled source. Cross-repository pilot outcomes are unmeasured until actual new packages use the selected adapters. No historical scenario replay is required.
