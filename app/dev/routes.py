"""Development-only routes for testing."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.container import AuthContainer
from app.auth.infrastructure.persistence.models.user_models import User
from app.common.storage.postgres import postgres_storage
from app.common.utils.id_generator import get_uuid7
from app.game.domain.value_objects import ScenarioDifficulty, ScenarioGenre
from app.game.infrastructure.persistence.models.game_models import Scenario
from config.settings import settings

dev_router = APIRouter(
    prefix="/api/v1/dev",
    tags=["dev"],
)


class DevTokenRequest(BaseModel):
    """Request for development token."""

    email: str = "dev@test.com"
    name: str = "Dev User"


class DevTokenResponse(BaseModel):
    """Response with development token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    message: str = "DEV ONLY - Do not use in production"


@dev_router.post("/token", response_model=DevTokenResponse)
async def get_dev_token(
    request: DevTokenRequest = DevTokenRequest(),
    db: AsyncSession = Depends(postgres_storage.write_db),
):
    """
    Generate a development JWT token for testing.

    ⚠️ WARNING: This endpoint is for development/testing only.
    It will NOT work in production environment.
    """
    # Block in production
    if settings.is_prod():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is disabled in production",
        )

    # Get or create dev user
    result = await db.execute(
        select(User).where(User.email == request.email.lower())
    )
    user = result.scalar_one_or_none()

    if not user:
        # Create dev user
        user = User(
            id=get_uuid7(),
            email=request.email.lower(),
            name=request.name,
            email_verified=True,
            is_active=True,
            user_level=100,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Generate JWT token
    # Generate JWT token
    container = AuthContainer(db)
    token_service = container.token_service()

    token_data = token_service.create_access_token(
        user_id=user.id,
        email=user.email,
        user_level=user.user_level,
    )

    return DevTokenResponse(
        access_token=token_data["access_token"],
        token_type=token_data["token_type"],
        expires_in=token_data["expires_in"],
        user_id=str(user.id),
    )


@dev_router.get("/health")
async def dev_health():
    """Development health check with extra info."""
    if settings.is_prod():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is disabled in production",
        )

    return {
        "status": "healthy",
        "environment": settings.environment,
        "debug": settings.debug,
    }


class SeedScenariosResponse(BaseModel):
    """Response for scenario seeding."""

    message: str
    scenarios_created: int


@dev_router.post("/seed-scenarios", response_model=SeedScenariosResponse)
async def seed_scenarios(
    db: AsyncSession = Depends(postgres_storage.write_db),
):
    """
    Seed test scenarios for development.

    ⚠️ WARNING: This endpoint is for development/testing only.
    """
    if settings.is_prod():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is disabled in production",
        )

    # Check if scenarios already exist
    result = await db.execute(select(Scenario).limit(1))
    if result.scalar_one_or_none():
        return SeedScenariosResponse(
            message="Scenarios already exist",
            scenarios_created=0,
        )

    # Create test scenarios
    scenarios = [
        Scenario(
            name="용사의 여정",
            description="마왕을 물리치기 위해 모험을 떠나는 전통 판타지 모험",
            world_setting="""당신은 평화로운 마을 '하늘빛 마을'에서 태어난 젊은 모험가입니다.
최근 마왕의 군대가 왕국을 위협하고 있으며, 국왕은 용감한 모험가를 찾고 있습니다.
이 세계에는 마법, 검술, 다양한 종족(인간, 엘프, 드워프, 수인족)이 존재합니다.
모험가 길드, 마법사 탑, 대장간 등 다양한 시설이 있으며,
몬스터를 처치하고 퀘스트를 완수하여 명성과 보상을 얻을 수 있습니다.""",
            initial_location="하늘빛 마을 - 모험가 길드 앞",
            genre=ScenarioGenre.FANTASY.value,
            difficulty=ScenarioDifficulty.NORMAL.value,
            is_active=True,
        ),
        Scenario(
            name="사이버펑크 2087",
            description="네온 불빛 가득한 미래 도시에서 펼쳐지는 해커의 이야기",
            world_setting="""2087년, 거대 기업들이 지배하는 네오 서울.
당신은 뒷골목에서 살아가는 프리랜서 해커입니다.
신체 개조(사이버웨어)가 일반화되어 있고, AI와 인간의 경계가 모호해지고 있습니다.
경찰은 부패했고, 기업 보안팀이 진정한 권력을 쥐고 있습니다.
데이터가 가장 큰 화폐이며, 정보가 곧 생명입니다.""",
            initial_location="네오 서울 - 뒷골목 아지트",
            genre=ScenarioGenre.CYBERPUNK.value,
            difficulty=ScenarioDifficulty.HARD.value,
            is_active=True,
        ),
        Scenario(
            name="좀비 아포칼립스",
            description="좀비가 창궐한 세상에서 생존하라",
            world_setting="""좀비 바이러스가 창궐한 지 1년.
대부분의 도시는 폐허가 되었고, 생존자들은 소규모 그룹으로 나뉘어 살아가고 있습니다.
당신은 서울 외곽의 한 폐건물에서 혼자 살아남은 생존자입니다.
자원은 부족하고, 다른 생존자가 항상 우호적이지는 않습니다.
좀비는 소리에 반응하며, 밤에 더 활발해집니다.""",
            initial_location="서울 외곽 - 폐건물 2층",
            genre=ScenarioGenre.SURVIVAL.value,
            difficulty=ScenarioDifficulty.HARD.value,
            is_active=True,
        ),
    ]

    for scenario in scenarios:
        scenario.id = get_uuid7()
        db.add(scenario)
        await db.flush()  # Force individual insert

    await db.commit()

    return SeedScenariosResponse(
        message="Test scenarios created successfully",
        scenarios_created=len(scenarios),
    )
