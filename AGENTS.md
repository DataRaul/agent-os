# Agent OS repository instructions

## Purpose

This repository is the public, reusable operating layer for AI-assisted work. Keep it generic, auditable, portable, and safe to publish.

## Public-boundary rules

- Do not add private repository names, private project state, credentials, secrets, personal data, proprietary business logic, unpublished evidence, or sensitive operational details.
- Project-specific mappings belong in a separate private overlay that implements the public overlay contract.
- Do not copy private Knowledge Core objects or private reasoning artifacts here. Public Agent OS may define interfaces for external knowledge systems, but not their private contents.
- Do not claim that possession of a tool, connector, token, or skill grants authority to use it.

## Skill rules

- Follow the open Agent Skills `SKILL.md` format.
- Every skill must have a narrow reusable purpose and a description that states when it should activate.
- Prefer procedures, verification rules, and failure boundaries over large generic prompts.
- Avoid embedding vendor documentation when a maintained upstream source should remain authoritative.
- Scripts are optional and must be inspectable, bounded, and necessary.
- A skill must not silently broaden permissions or external side effects.

## Agent/reviewer rules

- Add an independent reviewer only when role separation creates measurable value.
- Reviewer roles must name their independent evidence and output contract.
- Do not create agents whose main function is to agree with another agent.
- Completion must be verified against authoritative state where practical.

## Vendor trust rules

- Vendor-owned does not mean automatically executable.
- Record upstream owner, canonical URL, verified date, license status, requested tools/permissions, and admission state.
- Pin or review updates before adoption; do not auto-pull executable upstream changes into trusted workflows.
- Prefer the narrowest capability and minimum tool authority.

## Validation and delivery

- Run `python scripts/validate_agent_os.py` before proposing a merge.
- Treat green CI as scoped evidence, not universal proof.
- Inspect the final diff for unrelated changes and public-boundary violations.
- After merge, verify the resulting default-branch state before claiming completion.
