#!/usr/bin/env python3
"""커밋 메시지 형식을 검증한다."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOWED_TYPES = {
    "feat",
    "fix",
    "chore",
    "docs",
    "refactor",
    "test",
    "perf",
    "ci",
    "build",
    "style",
    "revert",
}

SUBJECT_PATTERN = re.compile(r"^(?P<type>[a-z]+): (?P<subject>.+)$")


def validate_subject(subject: str) -> tuple[bool, str]:
    """커밋 제목 규칙을 검증한다."""
    if len(subject) > 72:
        return False, "커밋 제목은 72자 이하여야 합니다."

    match = SUBJECT_PATTERN.match(subject)
    if not match:
        return (
            False,
            "커밋 메시지 제목은 " "'type: 한국어 제목' 형식이어야 합니다.",
        )

    commit_type = match.group("type")
    if commit_type not in ALLOWED_TYPES:
        allowed = ", ".join(sorted(ALLOWED_TYPES))
        return (
            False,
            "커밋 타입은 다음 중 하나여야 합니다: " f"{allowed}",
        )

    commit_subject = match.group("subject")
    if not re.search(r"[가-힣]", commit_subject):
        return False, "커밋 메시지 제목은 한국어를 포함해야 합니다."

    return True, ""


def main(argv: list[str] | None = None) -> int:
    """커밋 메시지 파일을 읽어 검증 결과를 반환한다."""
    args = argv if argv is not None else sys.argv[1:]
    if len(args) < 1:
        print("commit message file path is required")
        return 1

    msg_file = Path(args[0])
    if not msg_file.exists():
        print(f"commit message file not found: {msg_file}")
        return 1

    content = msg_file.read_text(encoding="utf-8")
    lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    if not lines:
        print("커밋 메시지가 비어 있습니다.")
        return 1

    subject = lines[0]
    is_valid, error_message = validate_subject(subject)
    if not is_valid:
        print(error_message)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
