"""Validate that external workflow dependencies use immutable commit pins."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*(.*?)\s*$")
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class PinValidationError(ValueError):
    pass


def _parse_uses_value(raw: str, label: str) -> str:
    value = raw.strip()
    if not value:
        raise PinValidationError(f"{label} uses value missing")

    if value[0] in {"'", '"'}:
        quote = value[0]
        end = value.find(quote, 1)
        if end < 0:
            raise PinValidationError(f"{label} quoted uses value is unterminated")
        parsed = value[1:end]
        tail = value[end + 1 :].strip()
        if tail and not tail.startswith("#"):
            raise PinValidationError(f"{label} uses value has unsupported trailing content")
        value = parsed
    else:
        value = value.split("#", 1)[0].strip()
        if any(char.isspace() for char in value):
            raise PinValidationError(f"{label} uses value contains unsupported whitespace")

    if not value:
        raise PinValidationError(f"{label} uses value missing")
    return value


def _validate_uses(value: str, label: str) -> None:
    if value.startswith("./"):
        return
    if value.startswith("docker://"):
        raise PinValidationError(
            f"{label} docker action references are outside the current immutable GitHub pin contract"
        )
    if "@" not in value:
        raise PinValidationError(f"{label} external action reference must include @<commit-sha>")

    target, ref = value.rsplit("@", 1)
    if not target or "/" not in target:
        raise PinValidationError(f"{label} external action target invalid")
    if FULL_SHA_RE.fullmatch(ref) is None:
        raise PinValidationError(
            f"{label} external action {target} must use an exact "
            "40-character lowercase commit SHA"
        )


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

    for path in workflow_paths:
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            match = USES_RE.match(line)
            if match is None:
                continue
            relative = path.relative_to(root)
            label = f"{relative}:{line_number}"
            _validate_uses(_parse_uses_value(match.group(1), label), label)


def main() -> None:
    try:
        validate_workflows(ROOT)
    except (OSError, PinValidationError) as exc:
        raise SystemExit(f"CI_ACTION_PIN_VALIDATION_FAIL: {exc}") from None
    print("CI_ACTION_PIN_VALIDATION_PASS")


if __name__ == "__main__":
    main()
