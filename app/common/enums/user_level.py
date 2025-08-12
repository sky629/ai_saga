"""User level enumeration."""

from enum import IntEnum


class UserLevel(IntEnum):
    """User level enumeration."""

    NORMAL = 100
    ADMIN = 1000

    @classmethod
    def is_admin(cls, level: int) -> bool:
        """Check if user level is admin."""
        return level >= cls.ADMIN.value

    @classmethod
    def is_normal(cls, level: int) -> bool:
        """Check if user level is normal user."""
        return level == cls.NORMAL.value
