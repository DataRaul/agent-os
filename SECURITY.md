# Security policy

## Public repository boundary

Do not open issues or pull requests containing:
- credentials or secrets;
- private repository content;
- personal data;
- proprietary/private eval fixtures;
- sensitive operational details.

If sensitive material is accidentally committed, treat it as exposed and rotate/revoke affected credentials or secrets. Removing it from a later commit is not sufficient remediation.

## External skills and plugins

External capabilities are not trusted merely because they are convenient or popular.

Admission follows `docs/TRUST_MODEL.md`. Executable scripts, hooks, network access, credential use, write authority, and update behavior require explicit review.

## Reporting

Use GitHub's private vulnerability reporting for security vulnerabilities when available. Do not publish exploit details for an unpatched vulnerability in a public issue.
