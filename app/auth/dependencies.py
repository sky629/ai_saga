"""Auth Dependencies."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.queries.get_user import GetUserQuery
from app.auth.application.use_cases.create_user import CreateUserUseCase
from app.auth.container import AuthContainer
from app.common.storage.postgres import postgres_storage


def get_auth_container(
    db: Annotated[AsyncSession, Depends(postgres_storage.write_db)]
) -> AuthContainer:
    """Auth Container (Write DB)."""
    return AuthContainer(db)


def get_read_auth_container(
    db: Annotated[AsyncSession, Depends(postgres_storage.read_db)]
) -> AuthContainer:
    """Auth Container (Read DB)."""
    return AuthContainer(db)


# === Commands ===
def get_create_user_use_case(
    container: Annotated[AuthContainer, Depends(get_auth_container)]
) -> CreateUserUseCase:
    return container.create_user_use_case()


# === Queries ===
def get_user_query(
    container: Annotated[AuthContainer, Depends(get_read_auth_container)]
) -> GetUserQuery:
    return container.get_user_query()


# === Type Aliases ===
CreateUserDep = Annotated[CreateUserUseCase, Depends(get_create_user_use_case)]
GetUserDep = Annotated[GetUserQuery, Depends(get_user_query)]
