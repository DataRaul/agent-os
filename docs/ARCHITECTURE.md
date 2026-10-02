# Agent OS architecture

## Scope

Agent OS owns reusable **ways of working** for AI-assisted software, data, research, and project execution.

It does not own:
- project-local truth;
- private organizational or personal context;
- private reusable knowledge;
- credentials or execution authority.

## Layer model

```text
PUBLIC AGENT OS
  skills + reviewer roles + evals + trust policy + routing
                      |
                      v
OPTIONAL PRIVATE OVERLAY
  project mappings + private skills/evals + private policies
  + routes to private knowledge/reasoning systems
                      |
                      v
EXISTING PROJECT REPOSITORIES
  code + data contracts + tests + runtime state + permissions
```

The project repository remains authoritative for its own implementation and current state.

## Public Agent OS responsibilities

1. Define portable reusable skills.
2. Define generic independent reviewer/verifier roles.
3. Define complexity routing defaults.
4. Define a vendor trust/admission model.
5. Provide eval cases that test normal and deceptive failure modes.
6. Define the interface a private overlay can implement.
7. Validate its own structure deterministically.

## Private overlay responsibilities

The private overlay is not part of this repository. It may:
- map public skills to specific repositories;
- select vendor skills for a project's actual stack;
- define private reviewer activation;
- add private eval fixtures;
- define authority/human gates;
- route material decisions to private knowledge or reasoning systems.

The public repository must never require those private details to remain useful.

## Task-class routing

Public capabilities are selected by generic work class and evidence need, not by private repository identity.

For consequential bounded runs, `BOUNDED_EVIDENCE_PRODUCING_RUN` may activate `bounded-run-integrity` when process success is weaker than proof of the required project postcondition. The consumer supplies project identity, authority, thresholds and routing privately; the public capability remains repository-neutral and authority-free.

Use the smallest sufficient capability chain. Registration does not imply always-on activation, automatic execution, or consumer adoption.

## Knowledge-system boundary

Agent OS may call or consult a knowledge/reasoning system through an adapter or private overlay.

The distinction is:

```text
Agent OS       = how to work
Knowledge base = reusable reasoning / domain knowledge
Project repo   = what is true here now
Private overlay= how the public operating layer maps onto private projects
```

No layer may silently take authority from another.

## Complexity principle

Start with:

```text
one capable agent
+ smallest sufficient skills
+ deterministic tools/evaluators
```

Add independent agents only when separate context, evidence, permissions, or parallelism creates measurable value.
