"""Handle OAuth Callback Use Case."""

from pydantic import BaseModel

from app.auth.application.ports import (
    AuthCacheInterface,
    OAuthProviderInterface,
    SocialAccountRepositoryInterface,
    TokenServiceInterface,
    UserRepositoryInterface,
)
from app.auth.domain.entities import SocialAccountEntity, UserEntity
from app.auth.domain.value_objects import AuthProvider, UserLevel
from app.common.exception import BadRequest
from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7


class OAuthCallbackInput(BaseModel):
    code: str
    state: str
    provider: AuthProvider


class OAuthCallbackResult(BaseModel):
    user: UserEntity
    access_token: str
    refresh_token: str
    expires_in: int
    is_new_user: bool


class HandleOAuthCallbackUseCase:
    """OAuth 콜백 처리 및 로그인/회원가입 유스케이스."""

    def __init__(
        self,
        user_repo: UserRepositoryInterface,
        social_repo: SocialAccountRepositoryInterface,
        oauth_provider: OAuthProviderInterface,
        token_service: TokenServiceInterface,
        cache: AuthCacheInterface,
    ):
        self._user_repo = user_repo
        self._social_repo = social_repo
        self._oauth_provider = oauth_provider
        self._token_service = token_service
        self._cache = cache

    async def execute(
        self, input_data: OAuthCallbackInput
    ) -> OAuthCallbackResult:
        # 1. State 검증
        if not await self._oauth_provider.verify_state(input_data.state):
            raise BadRequest(message="Invalid state parameter")

        # 2. 토큰 교환
        oauth_tokens = await self._oauth_provider.exchange_code_for_tokens(
            input_data.code
        )
        access_token = oauth_tokens["access_token"]
        refresh_token = oauth_tokens.get("refresh_token")

        # 3. 사용자 정보 획득
        user_info = await self._oauth_provider.get_user_info(access_token)
        email = user_info["email"]
        provider_user_id = user_info.get("id") or user_info.get("sub")

        # 4. 사용자 식별 및 생성 (CreateUserUseCase 로직 통합)
        existing_social = await self._social_repo.get_by_provider(
            input_data.provider, provider_user_id
        )

        now = get_utc_datetime()
        is_new_user = False

        if existing_social:
            user = await self._user_repo.get_by_id(existing_social.user_id)
            if not user:
                raise ValueError("User not found for existing social account")
        else:
            existing_user = await self._user_repo.get_by_email(email)
            if existing_user:
                user = existing_user
                # Update profile if missing
                if not user.profile_image_url and user_info.get("picture"):
                    user = user.model_copy(
                        update={"profile_image_url": user_info.get("picture")}
                    )
                    await self._user_repo.save(user)
            else:
                is_new_user = True
                user = UserEntity(
                    id=get_uuid7(),
                    email=email,
                    name=user_info.get("name") or email.split("@")[0],
                    profile_image_url=user_info.get("picture"),
                    user_level=UserLevel.NORMAL,
                    is_active=True,
                    email_verified=user_info.get("verified_email", False),
                    created_at=now,
                    updated_at=now,
                    last_login_at=now,
                )
                user = await self._user_repo.save(user)

            # 소셜 계정 연결
            social_account = SocialAccountEntity(
                id=get_uuid7(),
                user_id=user.id,
                provider=input_data.provider,
                provider_user_id=provider_user_id,
                provider_data=user_info,
                created_at=now,
                updated_at=now,
                last_used_at=now,
            )
            await self._social_repo.save(social_account)

        # 5. 마지막 로그인 갱신
        user = user.model_copy(update={"last_login_at": now})
        await self._user_repo.save(user)

        # 5.5 Google 토큰 캐시 저장
        if input_data.provider == AuthProvider.GOOGLE:
            expires_in = oauth_tokens.get("expires_in", 3600)
            await self._cache.set_google_access_token(
                user.id, access_token, expire=expires_in
            )
            if refresh_token:
                await self._cache.set_google_refresh_token(
                    user.id, refresh_token
                )

        # 6. JWT 토큰 생성
        jwt_access = self._token_service.create_access_token(
            user_id=user.id, email=user.email, user_level=user.user_level.value
        )
        jwt_refresh = self._token_service.create_refresh_token(user_id=user.id)

        # 7. 세션 저장
        await self._cache.set_jwt_session(
            user_id=user.id,
            session_data={
                "email": user.email,
                "user_level": user.user_level.value,
            },
            expire=jwt_access["expires_in"],
        )

        return OAuthCallbackResult(
            user=user,
            access_token=jwt_access["access_token"],
            refresh_token=jwt_refresh["refresh_token"],
            expires_in=jwt_access["expires_in"],
            is_new_user=is_new_user,
        )
