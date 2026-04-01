"""게임 타입 값 객체."""

from enum import Enum


class GameType(str, Enum):
    """시나리오가 사용하는 게임 진행 엔진 타입."""

    TRPG = "trpg"
    PROGRESSION = "progression"
