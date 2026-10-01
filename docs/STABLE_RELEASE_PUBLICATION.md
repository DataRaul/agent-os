# Stable v1.0.0 publication record

Status: `STABLE_V1_0_0_PUBLISHED`

Stable GitHub release `v1.0.0` was published on 2026-10-01 at exact commit `62fd8466971f4c8055ffefa3606d1cb1e28c7974`.

The release is:

- named `Agent OS v1.0.0`;
- not a draft;
- not a prerelease;
- the current GitHub latest release;
- bound to registry version 2 and its canonical digest;
- based on the stable candidate whose public stable surface was byte-identical to the published RC.

The machine-readable record is `catalog/stable-release-publication.json`.

The tagged stable candidate remains immutable preparation evidence. This post-publication record intentionally lives on later main and does not retag or rewrite `v1.0.0`.

Stable publication does not advance any consumer or private-overlay pin and grants no runtime authority. Any consumer/private-overlay adoption of the stable SHA remains a separate explicit decision.

Validate the repository-held publication record with:

```bash
python scripts/validate_stable_release_publication.py
python scripts/test_stable_release_publication.py
```
