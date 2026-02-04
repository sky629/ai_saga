"""Create User / Login Use Case."""

from typing import Optional

from pydantic import BaseModel

from app.auth.application.ports import (
    SocialAccountRepositoryInterface,
    UserRepositoryInterface,
)
from app.auth.domain.entities import SocialAccountEntity, UserEntity
from app.auth.domain.value_objects import AuthProvider, UserLevel
from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7


class CreateUserInput(BaseModel):
    """소셜 로그인/회원가입 입력 DTO."""

    model_config = {"frozen": True}

    provider: AuthProvider
    provider_user_id: str
    email: str
    name: str = ""
    profile_image_url: Optional[str] = None
    provider_data: dict = {}
    email_verified: bool = False


class CreateUserResult(BaseModel):
    """결과 DTO."""

    model_config = {"frozen": True}

    user: UserEntity
    is_new_user: bool


class CreateUserUseCase:
    """사용자 생성(로그인) 유스케이스."""

    def __init__(
        self,
        user_repo: UserRepositoryInterface,
        social_repo: SocialAccountRepositoryInterface,
    ):
        self.user_repo = user_repo
        self.social_repo = social_repo

    async def execute(self, input_data: CreateUserInput) -> CreateUserResult:
        # 1. Google 계정 이미 존재하는지 확인
        existing_social = await self.social_repo.get_by_provider(
            input_data.provider, input_data.provider_user_id
        )

        now = get_utc_datetime()

        if existing_social:
            # 이미 가입된 사용자 -> 마지막 로그인 갱신
            user = await self.user_repo.get_by_id(existing_social.user_id)
            if not user:
                # 데이터 정합성 깨짐 (소셜 계정은 있는데 유저는 없음) -> 예외 처리 필요하나 MVP에선 패스
                raise ValueError("User not found for existing social account")

            # Update last used
            # Entity는 불변이므로 copy로 업데이트 (실제론 repo update 메서드가 처리)
            # 여기서는 편의상 바로 repo 호출
            # TODO: Entity 메서드로 캡슐화 필요

            return CreateUserResult(user=user, is_new_user=False)

        # 2. 이메일로 기존 사용자 확인 (계정 연동)
        existing_user = await self.user_repo.get_by_email(input_data.email)

        if existing_user:
            # 계정 연동: 기존 유저에게 새 소셜 계정 추가
            user = existing_user
            # 프로필 업데이트 (이미지 없으면)
            if not user.profile_image_url and input_data.profile_image_url:
                user = user.model_copy(
                    update={"profile_image_url": input_data.profile_image_url}
                )
                await self.user_repo.save(user)
        else:
            # 신규 가입
            user = UserEntity(
                id=get_uuid7(),
                email=input_data.email,
                name=input_data.name or input_data.email.split("@")[0],
                profile_image_url=input_data.profile_image_url,
                user_level=UserLevel.NORMAL,
                is_active=True,
                email_verified=input_data.email_verified,
                created_at=now,
                updated_at=now,
                last_login_at=now,
            )
            user = await self.user_repo.save(user)

        # 3. 소셜 계정 생성
        social_account = SocialAccountEntity(
            id=get_uuid7(),
            user_id=user.id,
            provider=input_data.provider,
            provider_user_id=input_data.provider_user_id,
            provider_data=input_data.provider_data,
            created_at=now,
            updated_at=now,
            last_used_at=now,
        )
        await self.social_repo.save(social_account)

        return CreateUserResult(user=user, is_new_user=not existing_user)
