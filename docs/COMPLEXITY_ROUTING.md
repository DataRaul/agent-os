# Complexity routing

Complexity controls how much agent machinery should be activated.

## C0 — trivial

Use:
- main agent only;
- deterministic checks when available.

Examples: small text edits, obvious formatting, narrow low-risk changes.

## C1 — normal bounded work

Use:
- main agent;
- relevant skills;
- repository tests/validation.

Add no reviewer by default.

## C2 — material change

Use:
- main agent;
- relevant skills;
- deterministic validation;
- one independent reviewer, normally the Silent Failure Reviewer.

Typical triggers:
- multi-file semantic changes;
- state or schema changes;
- material PRs;
- changes whose failure can pass existing CI;
- significant integration behavior.

## C3 — high blast radius or high uncertainty

Use:
- main agent;
- relevant skills;
- Silent Failure Reviewer;
- one domain-appropriate independent verifier/reviewer;
- security review when security-relevant;
- explicit final postcondition verification.

Typical triggers:
- destructive or irreversible mutations;
- migrations;
- external runtime writes;
- data-integrity-sensitive pipelines;
- consequential research validity;
- cross-system authority boundaries;
- high-cost or hard-to-reverse changes.

## Escalation rule

Complexity is earned by risk or information value, not by task length.

Do not escalate merely because:
- a task is verbose;
- many files exist;
- multiple agents are available.

## De-escalation rule

If independent reviewers share the same evidence and produce no measurable incremental coverage, collapse back toward one agent plus deterministic checks.
