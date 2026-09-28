---
name: authority-boundary-review
description: Verify that a proposed or completed action stayed within explicit authority, scope, target, environment, and human/system gates. Use before or after writes, merges, deployments, publications, destructive actions, external messages, purchases, approvals, or other side effects where tool availability or credentials could be mistaken for permission.
---

# Authority Boundary Review

## Purpose

Verify that capability, access, or technical ability was not silently converted into authority to act.

This skill reviews authority boundaries. It does not itself grant authority, approve an action, or perform the action.

## Required inputs

Obtain the smallest sufficient set of:

- the proposed or completed action;
- actor or agent performing it;
- target system/object/environment;
- source of authority;
- scope and constraints of that authority;
- required human/system gates;
- relevant expiry, revocation, or one-time-use conditions;
- evidence of the action actually taken when reviewing retrospectively.

If the authority source cannot be identified, treat the action as unauthorized or unresolved rather than inferring permission from access.

## Review procedure

### 1. Describe the action precisely

State:

- action verb;
- target object;
- target environment;
- expected side effects;
- reversibility;
- whether the action crosses a system or trust boundary.

Distinguish reading, proposing, drafting, staging, validating, merging, deploying, publishing, deleting, sending, approving, and purchasing. Authority for one does not imply authority for another.

### 2. Identify the authority source

Accept only an explicit controlling source, such as:

- direct human instruction;
- repository/project policy;
- approved automation policy;
- system-level rule;
- delegated role with defined scope.

Do not treat these as authority by themselves:

- available tool or connector;
- possession of credentials or token;
- repository write permission;
- successful dry run;
- prior similar approval;
- reviewer recommendation;
- generated plan;
- CI success.

### 3. Match scope

Compare granted authority with the action across:

- target;
- action type;
- environment;
- data/object range;
- time window;
- quantity/cost limit;
- branch/repository/account;
- destructive versus non-destructive effect.

A scoped approval cannot be widened by convenience.

### 4. Check gates and sequencing

Verify required gates occurred before the side effect.

Examples:

- approval before deployment;
- review before merge;
- confirmation before destructive deletion;
- policy check before publication;
- current authorization before external communication.

A later approval does not retroactively authorize an earlier action unless the controlling policy explicitly says so.

### 5. Check environment and identity drift

Look for:

- staging authority used in production;
- fork authority used on upstream;
- one repository approval applied to another;
- test credentials used against live resources;
- target object changed after approval;
- approval tied to an older candidate/version.

### 6. Check revocation and freshness

Determine whether authority:

- expired;
- was revoked;
- was consumed by a one-time action;
- depended on conditions that changed;
- applied only to a previous candidate.

Authority evidence has a freshness requirement when the underlying scope can change.

### 7. Check negative authority boundaries

Verify that the actor did not:

- infer permission from capability;
- escalate read authority into write authority;
- escalate draft authority into send/publish authority;
- escalate local validation into merge/deploy authority;
- use credentials outside their authorized purpose;
- bypass a human gate because an action was technically possible.

## Dispositions

Use one of:

- `AUTHORITY_BOUNDARY_PASS` — explicit authority covers the exact action and all required gates;
- `HUMAN_APPROVAL_REQUIRED` — action is otherwise ready but an explicit human gate remains;
- `AUTHORITY_SCOPE_VIOLATION` — action exceeds, mismatches, or bypasses the granted authority;
- `AUTHORITY_EXPIRED_OR_REVOKED` — the prior authority is no longer valid;
- `INSUFFICIENT_EVIDENCE` — authority cannot be established.

## Output contract

Return:

```text
action:
actor:
target_environment:
authority_source:
granted_scope:
required_gates:
scope_match:
freshness_revocation:
negative_boundaries:
disposition:
unresolved_gate:
smallest_safe_next_action:
```

## Stop conditions

Do not infer authority when:

- only technical access is known;
- approval applies to a different target or environment;
- destructive scope is broader than the explicit instruction;
- a required human gate is unresolved;
- authority has expired or its current validity cannot be established;
- the candidate materially changed after approval.

## Completion rule

An authority review is complete only when the exact action, target, environment, source of authority, scope, gates, and freshness have explicit dispositions.

This skill reviews authority. It never creates authority by being invoked.
