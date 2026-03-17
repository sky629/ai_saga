"""커밋 메시지 훅 검증 스크립트 테스트."""

from __future__ import annotations

import tempfile
from pathlib import Path

from scripts.hooks.validate_commit_msg import main


def run_validator(subject: str) -> int:
    """임시 커밋 메시지 파일로 검증 스크립트를 실행한다."""
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False
    ) as file:
        file.write(subject)
        temp_path = Path(file.name)

    try:
        return main([str(temp_path)])
    finally:
        temp_path.unlink(missing_ok=True)


class TestValidateCommitMsg:
    """커밋 메시지 형식 검증."""

    def test_returns_zero_for_korean_conventional_commit(self) -> None:
        """허용된 타입과 한국어 제목이면 통과한다."""
        assert run_validator("fix: 로그인 오류 수정\n") == 0

    def test_returns_one_for_missing_type_prefix(self) -> None:
        """타입 접두사가 없으면 실패한다."""
        assert run_validator("로그인 오류 수정\n") == 1

    def test_returns_one_for_non_korean_subject(self) -> None:
        """제목에 한국어가 없으면 실패한다."""
        assert run_validator("feat: fix login bug\n") == 1

    def test_returns_one_for_unsupported_type_prefix(self) -> None:
        """허용되지 않은 타입 접두사는 실패한다."""
        assert run_validator("unknown: 로그인 오류 수정\n") == 1
