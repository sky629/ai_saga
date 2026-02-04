"""Game Master Domain Service.

순수 도메인 로직으로, 외부 의존성(LLM, DB) 없이 게임 규칙을 처리합니다.
"""

from app.game.domain.entities import GameSessionEntity
from app.game.domain.value_objects import EndingType


class GameMasterService:
    """게임 마스터 도메인 서비스.

    여러 엔티티에 걸친 도메인 로직을 처리합니다.
    외부 인프라에 의존하지 않는 순수 비즈니스 로직만 포함합니다.
    """

    @staticmethod
    def should_end_game(session: GameSessionEntity) -> bool:
        """게임 종료 조건 확인.

        Args:
            session: 현재 게임 세션

        Returns:
            게임 종료 여부
        """
        return session.is_final_turn

    @staticmethod
    def parse_ending_type(llm_response: str) -> EndingType:
        """LLM 응답에서 엔딩 타입 파싱.

        Args:
            llm_response: LLM이 생성한 엔딩 텍스트

        Returns:
            파싱된 EndingType
        """
        return EndingType.from_string(llm_response)

    @staticmethod
    def extract_narrative_from_ending(content: str) -> str:
        """엔딩 응답에서 내러티브 추출.

        Args:
            content: 전체 LLM 응답

        Returns:
            추출된 내러티브 텍스트
        """
        if "[엔딩 내러티브]:" in content:
            return content.split("[엔딩 내러티브]:")[1].strip()
        return content

    @staticmethod
    def summarize_recent_events(messages: list[str], limit: int = 3) -> str:
        """최근 이벤트 요약.

        Args:
            messages: 최근 메시지 목록 (AI 응답만)
            limit: 요약할 메시지 수

        Returns:
            요약된 이벤트 문자열
        """
        if not messages:
            return "없음"
        events = [f"- {msg[:100]}..." for msg in messages[-limit:]]
        return "\n".join(events) if events else "없음"

    @staticmethod
    def extract_action_options(
        content: str, max_options: int = 5
    ) -> list[str]:
        """응답에서 행동 옵션 추출.

        Args:
            content: LLM 응답 텍스트
            max_options: 최대 옵션 수

        Returns:
            추출된 옵션 목록
        """
        options = []
        lines = content.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("1.", "2.", "3.", "4.", "5.", "-", "•")):
                options.append(stripped)
        return options[:max_options]
