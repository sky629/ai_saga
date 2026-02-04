"""Auth Provider Value Object."""

from enum import Enum


class AuthProvider(str, Enum):
    """인증 제공자 VO."""

    GOOGLE = "google"
    # KAKAO = "kakao"  # 추후 확장
