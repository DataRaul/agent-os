# Release publication record

Status: `V1_0_0_RC1_PUBLISHED`

GitHub prerelease `v1.0.0-rc.1` was published on 2026-10-01 at exact commit `7bc62182683857c285bb6487d80b1507c4457dd6`.

The machine-readable record is `catalog/release-publication.json`. It binds the published tag to the release-candidate version, tagged commit, candidate-manifest blob, registry version/digest, GitHub release ID, and prerelease state.

This record is post-publication evidence. The original `catalog/release-candidate.json` remains the immutable preparation-state contract that existed at the tagged commit; it is intentionally not rewritten to claim that publication had already occurred.

Publication of the RC does not:

- publish stable `v1.0.0`;
- advance any consumer or private-overlay pin;
- grant runtime authority;
- admit P2 specialist reviewers;
- make the P5 fixture router a production runtime;
- admit excluded vendor tooling.

The next release gate is RC validation followed by separate explicit authority for stable `v1.0.0` publication.

Validate the local post-publication record with:

```bash
python scripts/validate_release_publication.py
python scripts/test_release_publication.py
```

These checks are deterministic and offline. They verify repository-held publication evidence; they do not query GitHub or republish anything.
