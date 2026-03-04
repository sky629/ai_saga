#!/usr/bin/env python3
"""Validate commit message format (Korean required)."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("commit message file path is required")
        return 1

    msg_file = Path(sys.argv[1])
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
    if len(subject) > 72:
        print("커밋 제목은 72자 이하여야 합니다.")
        return 1

    if not re.search(r"[가-힣]", subject):
        print("커밋 메시지 제목은 한국어를 포함해야 합니다.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
