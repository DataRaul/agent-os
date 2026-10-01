# Stable 1.0.0 release candidate

Status: `FIRST_STABLE_RELEASE_CANDIDATE_PREPARED`

The public repository is prepared for a first stable `v1.0.0` publication, but no stable tag or GitHub Release is created by this preparation.

The stable candidate is based on published prerelease `v1.0.0-rc.1` at exact commit `7bc62182683857c285bb6487d80b1507c4457dd6`.

RC validation established:

- the published release is a prerelease and not a draft;
- its tag resolves to the authorized RC commit;
- post-publication main validation and publication-gate runs passed;
- registry version and canonical digest are unchanged;
- every stable interface, capability implementation, and registered eval path has the same Git blob identity as the RC;
- only release-control/documentation work occurred after the RC tag.

The machine-readable contract is `catalog/stable-release-candidate.json`. Its validator fails closed on stable-surface drift, registry drift, RC-publication mismatch, version mismatch, or premature stable-publication claims.

Stable publication remains a separate explicit human gate. Consumer/private-overlay pin advancement remains separate again after publication.
