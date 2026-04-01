"""Development-only routes for testing."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.container import AuthContainer
from app.auth.infrastructure.persistence.models.user_models import User
from app.common.storage.postgres import postgres_storage
from app.common.utils.id_generator import get_uuid7
from app.game.domain.value_objects import (
    GameType,
    ScenarioDifficulty,
    ScenarioGenre,
)
from app.game.infrastructure.adapters.image_service import (
    ImageGenerationServiceAdapter,
)
from app.game.infrastructure.persistence.models.game_models import Scenario
from config.settings import settings

dev_router = APIRouter(
    prefix="/api/v1/dev",
    tags=["dev"],
)

DEFAULT_SCENARIO_THUMBNAIL_URL = (
    "https://pub-3c25697921ae4f12aac4c4cfdbb57cc4.r2.dev/dummy.png"
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


@dev_router.post("/token/", response_model=DevTokenResponse)
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


@dev_router.get("/health/")
async def dev_health():
    """Development health check with extra info."""
    if settings.is_prod():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is disabled in production",
        )

    return {
        "status": "healthy",
        "environment": settings.KANG_ENV,
        "debug": settings.debug,
    }


class SeedScenariosResponse(BaseModel):
    """Response for scenario seeding."""

    message: str
    scenarios_created: int


class DevGenerateImageRequest(BaseModel):
    """개발용 이미지 생성 요청."""

    prompt: str
    session_id: str | None = None
    user_id: str | None = None


class DevGenerateImageResponse(BaseModel):
    """개발용 이미지 생성 응답."""

    image_url: str
    prompt: str
    session_id: str
    user_id: str


@dev_router.post("/seed-scenarios/", response_model=SeedScenariosResponse)
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
            description=(
                "붕괴 직전의 왕국을 배경으로, 변방 마을의 신참 모험가가 "
                "마왕군의 침공과 고대 유적의 비밀 사이에서 자신의 운명을 "
                "선택해 나가는 정통 판타지 장편 모험입니다."
            ),
            tags=["판타지", "모험", "왕국", "유적"],
            hook="북부 요새가 무너진 밤, 당신의 이름이 처음으로 예언서에 기록된다.",
            recommended_for=(
                "정통 판타지, 성장형 모험, 왕국과 유적의 비밀을 "
                "파헤치는 서사를 좋아하는 플레이어"
            ),
            thumbnail_url=DEFAULT_SCENARIO_THUMBNAIL_URL,
            world_setting="""에르다니아 왕국은 오랫동안 인간, 엘프, 드워프, 수인족이 불안한 평화를 유지해 온 땅입니다.
왕도는 눈부시게 번영했지만 국경 지대는 이미 오래전부터 마왕군의 척후병, 도적단, 타락한 마법사, 굶주린 괴수들에 시달리고 있습니다.
최근 북부 요새가 함락되고 봉화대의 불빛이 하나씩 꺼지면서, 왕국 전역에는 '이번에는 정말 끝일지도 모른다'는 공포가 퍼지고 있습니다.

당신이 출발하는 하늘빛 마을은 겉보기에는 평온한 시골이지만, 상단의 밀수, 실종된 순례자, 봉인된 고분, 사라진 성기사단의 흔적 같은 사건이 얽혀 있습니다.
모험가 길드는 의뢰를 통해 돈과 장비, 평판을 얻을 수 있는 가장 현실적인 출발점이지만, 진실에 가까워질수록 왕실, 교단, 마법사 탑, 이종족 연맹이 각자 숨기고 있는 이해관계와 마주하게 됩니다.
이 세계에서 검과 마법은 생존 수단일 뿐 아니라 정치와 신앙, 혈통의 증거이기도 하며, 한 번의 선택이 동료와 적, 도시와 왕국의 미래를 바꿀 수 있습니다.""",
            initial_location="하늘빛 마을 - 모험가 길드 앞",
            game_type=GameType.TRPG.value,
            genre=ScenarioGenre.FANTASY.value,
            difficulty=ScenarioDifficulty.NORMAL.value,
            is_active=True,
        ),
        Scenario(
            name="사이버펑크 2087",
            description=(
                "거대 기업이 법과 치안을 대체한 네오 서울에서, 뒷골목 "
                "해커가 데이터 탈취, 기억 조작, 사이버웨어 음모를 "
                "헤집으며 살아남아야 하는 느와르 사이버펑크 스릴러입니다."
            ),
            tags=["사이버펑크", "해킹", "느와르", "기업 음모"],
            hook="삭제된 기억 한 조각이, 도시 전체의 권력 구조를 뒤집을 열쇠일지도 모른다.",
            recommended_for=(
                "해킹, 잠입, 음모 추적, 어두운 미래 도시 분위기를 "
                "좋아하는 플레이어"
            ),
            thumbnail_url=DEFAULT_SCENARIO_THUMBNAIL_URL,
            world_setting="""2087년의 네오 서울은 공식적으로는 스마트 메가시티이지만, 실제로는 초거대 기업 여섯 곳이 구역별로 행정과 치안을 나눠 가진 민영 도시국가에 가깝습니다.
상층 구역의 시민은 인공 기후와 고급 사이버웨어, AI 비서, 유전자 맞춤 의료를 누리지만, 하층 구역의 사람들은 장기 대출과 데이터 담보 계약에 묶인 채 생존을 거래합니다.
경찰 조직은 기업 계약직으로 전락했고, 사건의 진실보다 어느 회사의 손해를 줄일지가 더 중요합니다.

당신은 정식 소속 없는 프리랜서 해커이자 침투 전문가로, 기업 서버를 털고, 삭제된 기억 조각을 복구하며, 때로는 사람의 감정 기록까지 거래하는 위험한 일로 생계를 이어갑니다.
이 세계에서 가장 비싼 자산은 금이나 무기가 아니라 '검증된 정보'이며, 한 번 유출된 데이터는 사람의 신분, 인간관계, 범죄 기록, 생체 인증, 나아가 인격 자체를 무너뜨릴 수 있습니다.
AI와 인간의 경계는 이미 흐려졌고, 도시 전체가 거대한 감시 장치가 된 지금, 당신이 믿을 수 있는 것은 암호화된 백도어와 몇 안 되는 동료, 그리고 아직 팔아넘기지 않은 자신의 기억뿐입니다.""",
            initial_location="네오 서울 - 뒷골목 아지트",
            game_type=GameType.TRPG.value,
            genre=ScenarioGenre.CYBERPUNK.value,
            difficulty=ScenarioDifficulty.HARD.value,
            is_active=True,
        ),
        Scenario(
            name="좀비 아포칼립스",
            description=(
                "문명이 무너진 지 1년이 지난 폐허의 서울에서, 식량과 "
                "은신처, 믿을 수 있는 사람을 찾아야 하는 처절한 "
                "생존형 좀비 아포칼립스 시나리오입니다."
            ),
            tags=["좀비", "아포칼립스", "생존", "서울"],
            hook="당신이 들은 구조 신호는 마지막 희망일 수도, 가장 정교한 함정일 수도 있다.",
            recommended_for=(
                "자원 관리, 긴장감 있는 생존극, 인간 군상의 어두운 선택을 "
                "좋아하는 플레이어"
            ),
            thumbnail_url=DEFAULT_SCENARIO_THUMBNAIL_URL,
            world_setting="""원인을 알 수 없는 감염 사태가 전국을 휩쓴 뒤 정확히 1년이 지났습니다.
정부는 붕괴했고, 군 통제선은 대부분 무너졌으며, 방송국의 긴급 신호는 이제 잡음 섞인 반복 메시지만 남겨둔 채 사라졌습니다.
서울 도심은 이미 수차례 약탈과 화재를 겪어 구역마다 전혀 다른 생존 규칙이 형성됐고, 생존자들은 학교, 아파트, 지하철, 물류 창고 같은 장소를 임시 거점으로 삼고 있습니다.

당신이 머무는 서울 외곽의 폐건물은 당장 비를 피할 수 있는 정도의 피난처일 뿐입니다.
식수는 늘 부족하고, 통조림 하나를 두고도 사람이 서로 칼을 겨눌 수 있으며, 발전기 소음과 불빛은 곧 감염체와 약탈자를 동시에 불러오는 신호가 됩니다.
이 세계의 좀비는 소리와 움직임, 피 냄새에 민감하며 밤이 되면 더 사나워집니다.
하지만 진짜 위협은 감염체만이 아닙니다. 폐허 속 공동체마다 각자의 규칙과 공포, 죄책감이 쌓여 있고, 누구를 구할지 누구를 버릴지에 따라 당신이 끝까지 인간으로 남을 수 있는지도 결정됩니다.""",
            initial_location="서울 외곽 - 폐건물 2층",
            game_type=GameType.TRPG.value,
            genre=ScenarioGenre.SURVIVAL.value,
            difficulty=ScenarioDifficulty.HARD.value,
            is_active=True,
        ),
        Scenario(
            name="기연 일지",
            description=(
                "절벽 아래 신비한 동굴에서 12개월 동안 기연을 찾고 "
                "무공을 연마하며, 월별 선택과 상태 누적으로 탈출과 "
                "명성을 동시에 노리는 성장형 무협 수련기입니다."
            ),
            tags=["무협", "수련", "기연", "동굴", "성장"],
            hook=(
                "절벽 아래로 추락한 당신 앞에, 고수의 흔적이 남은 "
                "동굴이 1년의 운명을 펼쳐 보인다."
            ),
            recommended_for=(
                "월 단위 성장, 상태창 누적, 무공 수련, 최종 업적 보드 "
                "수집형 플레이를 좋아하는 유저"
            ),
            thumbnail_url=DEFAULT_SCENARIO_THUMBNAIL_URL,
            world_setting="""깊은 절벽 아래에는 오래전 천하를 떨친 절대고수가 마지막 수행을 남긴 거대한 천연 동굴이 숨어 있습니다.
동굴 내부에는 청색 광맥, 지하 수로, 폭포수, 약초와 영과, 그리고 주인을 잃은 무림비급이 흩어져 있습니다.
하지만 이곳은 축복과 감옥이 동시에 깃든 장소입니다. 식량과 공기는 1년을 버티기 어려울 만큼 제한적이며, 살아남으려면 매달 수련과 탐색의 방향을 냉정하게 선택해야 합니다.

당신은 우연인지 운명인지 모를 추락 끝에 이 동굴에 떨어졌고, 지금부터 12개월 안에 몸과 기운, 무공의 깊이를 끌어올려 탈출할 자격을 증명해야 합니다.
매달의 선택은 내공과 외공, 체력, 비급 숙련도, 그리고 동굴이 허락하는 기연의 흐름을 바꿉니다.
강해지지 못하면 이곳은 무덤이 되지만, 충분한 깨달음을 쌓는다면 이 동굴은 당신에게 강호를 뒤흔들 명함 한 장을 남겨 줄 것입니다.""",
            initial_location="절벽 아래 - 청색광이 감도는 거대 동굴",
            game_type=GameType.PROGRESSION.value,
            genre=ScenarioGenre.HISTORICAL.value,
            difficulty=ScenarioDifficulty.NORMAL.value,
            max_turns=12,
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


@dev_router.post(
    "/generate-image/",
    response_model=DevGenerateImageResponse,
)
async def generate_dev_image(
    request: DevGenerateImageRequest,
):
    """개발용 커스텀 프롬프트 이미지 생성."""
    if settings.is_prod():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is disabled in production",
        )

    session_id = request.session_id or str(get_uuid7())
    user_id = request.user_id or str(get_uuid7())

    image_service = ImageGenerationServiceAdapter()
    image_url = await image_service.generate_image(
        prompt=request.prompt,
        session_id=session_id,
        user_id=user_id,
    )

    if image_url is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Image generation failed",
        )

    return DevGenerateImageResponse(
        image_url=image_url,
        prompt=request.prompt,
        session_id=session_id,
        user_id=user_id,
    )
