"""User Level Value Object."""

from enum import Enum

class UserLevel(str, Enum):
    """사용자 등급 VO."""
    NORMAL = "NORMAL"
    ADMIN = "ADMIN"
