"""Validate that GitHub-hosted workflow actions use immutable commit pins."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
EXTERNAL_USE_RE = re.compile(
    r"^\s*-\s+uses:\s+([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)@([^\s#]+)"
)
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class PinValidationError(ValueError):
    pass


def validate_workflows(root: Path = ROOT) -> None:
    workflow_dir = root / ".github" / "workflows"
    if not workflow_dir.is_dir():
        raise PinValidationError(".github/workflows directory missing")

    workflow_paths = sorted(
        path
        for pattern in ("*.yml", "*.yaml")
        for path in workflow_dir.glob(pattern)
    )
    if not workflow_paths:
        raise PinValidationError("no GitHub workflow files found")

    external_uses = 0
    for path in workflow_paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = EXTERNAL_USE_RE.match(line)
            if match is None:
                continue
            external_uses += 1
            owner, repository, ref = match.groups()
            if FULL_SHA_RE.fullmatch(ref) is None:
                relative = path.relative_to(root)
                raise PinValidationError(
                    f"{relative}:{line_number} external action "
                    f"{owner}/{repository} must use an exact 40-character lowercase commit SHA"
                )

    if external_uses == 0:
        raise PinValidationError("no external GitHub Action dependencies found")


def main() -> None:
    try:
        validate_workflows(ROOT)
    except (OSError, PinValidationError) as exc:
        raise SystemExit(f"CI_ACTION_PIN_VALIDATION_FAIL: {exc}") from None
    print("CI_ACTION_PIN_VALIDATION_PASS")


if __name__ == "__main__":
    main()
