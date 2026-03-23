"""게임 메모리 타입 값 객체."""

from enum import Enum


class GameMemoryType(str, Enum):
    """검색용 게임 메모리 타입."""

    USER_ACTION = "user_action"
    ASSISTANT_NARRATIVE = "assistant_narrative"
