"""Update User Profile Use Case."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.auth.application.ports import UserRepositoryInterface
from app.auth.domain.entities import UserEntity
from app.common.exception import BadRequest, NotFound


class UpdateUserProfileInput(BaseModel):
    name: Optional[str] = None
    profile_image_url: Optional[str] = None


class UpdateUserProfileUseCase:
    """사용자 프로필 업데이트 유스케이스."""

    def __init__(self, user_repo: UserRepositoryInterface):
        self._user_repo = user_repo

    async def execute(
        self, user_id: UUID, input_data: UpdateUserProfileInput
    ) -> UserEntity:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFound(message="User not found")

        update_data = {}
        if input_data.name is not None:
            if not input_data.name.strip():
                raise BadRequest(message="Name cannot be empty")
            update_data["name"] = input_data.name.strip()

        if input_data.profile_image_url is not None:
            update_data["profile_image_url"] = input_data.profile_image_url

        if not update_data:
            return user

        updated_user = user.model_copy(update=update_data)
        return await self._user_repo.save(updated_user)
