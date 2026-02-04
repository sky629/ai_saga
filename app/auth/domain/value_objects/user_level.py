"""User Level Value Object."""

from enum import IntEnum


class UserLevel(IntEnum):
    """사용자 등급 VO."""

    NORMAL = 100
    ADMIN = 1000
