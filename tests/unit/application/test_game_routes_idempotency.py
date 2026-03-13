from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.common.utils.datetime import get_utc_datetime
from app.common.utils.id_generator import get_uuid7
from app.game.presentation.routes.game_routes import (
    create_character,
    generate_illustration,
    start_game,
    submit_action,
)
from app.game.presentation.routes.schemas.request import (
    CreateCharacterRequest,
    GameActionRequest,
    StartGameRequest,
)
from app.game.presentation.routes.schemas.response import (
    GameActionResponse,
    GameMessageResponse,
    GameSessionResponse,
)


@asynccontextmanager
async def _noop_lock():
    yield


@pytest.mark.asyncio
async def test_submit_action_requires_idempotency_key():
    session_id = get_uuid7()

    with pytest.raises(HTTPException) as exc_info:
        await submit_action(
            session_id=session_id,
            request=GameActionRequest(action="행동"),
            use_case=AsyncMock(),
            cache_service=AsyncMock(),
            response=SimpleNamespace(headers={}),
            idempotency_key=None,
            current_user=SimpleNamespace(id=get_uuid7()),
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_submit_action_uses_session_scoped_lock_key():
    session_id = get_uuid7()
    user_id = get_uuid7()
    lock_mock = Mock(return_value=_noop_lock())
    cache_service = SimpleNamespace(lock=lock_mock)

    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = SimpleNamespace(
        is_cached=False,
        response=GameActionResponse(
            message=GameMessageResponse(
                id=get_uuid7(),
                role="assistant",
                content="결과",
                created_at=get_utc_datetime(),
            ),
            narrative="결과",
            options=["다음"],
            turn_count=1,
            max_turns=10,
        ),
    )

    await submit_action(
        session_id=session_id,
        request=GameActionRequest(action="행동"),
        use_case=mock_use_case,
        cache_service=cache_service,  # type: ignore[arg-type]
        response=SimpleNamespace(headers={}),
        idempotency_key="same-key",
        current_user=SimpleNamespace(id=user_id),
    )

    lock_mock.assert_called_once_with(
        f"game:action:{session_id}", ttl_ms=20000
    )


@pytest.mark.asyncio
async def test_generate_illustration_uses_message_scoped_lock_key():
    session_id = get_uuid7()
    message_id = get_uuid7()
    user_id = get_uuid7()
    lock_mock = Mock(return_value=_noop_lock())
    cache_service = SimpleNamespace(lock=lock_mock)

    use_case = AsyncMock()
    use_case.execute.return_value = SimpleNamespace(
        message_id=message_id,
        image_url="https://example.com/image.png",
    )

    await generate_illustration(
        session_id=session_id,
        message_id=message_id,
        use_case=use_case,
        cache_service=cache_service,  # type: ignore[arg-type]
        current_user=SimpleNamespace(id=user_id),
    )

    lock_mock.assert_called_once_with(
        f"game:illustration:{message_id}",
        ttl_ms=20000,
    )


@pytest.mark.asyncio
async def test_start_game_idempotency_replay_returns_cached_response():
    user_id = get_uuid7()
    cache_service = AsyncMock()
    use_case = AsyncMock()

    request = StartGameRequest(
        character_id=get_uuid7(),
        scenario_id=get_uuid7(),
        max_turns=30,
    )
    expected = GameSessionResponse(
        id=get_uuid7(),
        character_id=request.character_id,
        scenario_id=request.scenario_id,
        current_location="시작 지점",
        game_state={},
        status="active",
        turn_count=0,
        max_turns=30,
        ending_type=None,
        started_at=get_utc_datetime(),
        last_activity_at=get_utc_datetime(),
        image_url=None,
    )

    import hashlib
    import json

    payload_hash = hashlib.sha256(
        json.dumps(
            {
                "character_id": str(request.character_id),
                "scenario_id": str(request.scenario_id),
                "max_turns": request.max_turns,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    cache_service.get.return_value = json.dumps(
        {
            "payload_hash": payload_hash,
            "response": expected.model_dump(mode="json"),
        }
    )

    response = await start_game(
        request=request,
        use_case=use_case,
        cache_service=cache_service,
        idempotency_key="idempo-1",
        current_user=SimpleNamespace(id=user_id),
    )

    assert response.id == expected.id
    use_case.execute.assert_not_called()


@pytest.mark.asyncio
async def test_start_game_idempotency_uses_character_scoped_lock_key():
    user_id = get_uuid7()
    request = StartGameRequest(
        character_id=get_uuid7(),
        scenario_id=get_uuid7(),
        max_turns=20,
    )
    lock_mock = Mock(return_value=_noop_lock())
    cache_service = AsyncMock()
    cache_service.lock = lock_mock
    cache_service.get.return_value = None
    use_case = AsyncMock()
    use_case.execute.return_value = GameSessionResponse(
        id=get_uuid7(),
        character_id=request.character_id,
        scenario_id=request.scenario_id,
        current_location="시작 지점",
        game_state={},
        status="active",
        turn_count=0,
        max_turns=request.max_turns,
        ending_type=None,
        started_at=get_utc_datetime(),
        last_activity_at=get_utc_datetime(),
        image_url=None,
    )

    await start_game(
        request=request,
        use_case=use_case,
        cache_service=cache_service,
        idempotency_key="idempo-lock",
        current_user=SimpleNamespace(id=user_id),
    )

    lock_mock.assert_called_once_with(
        f"game:start:character:{request.character_id}",
        ttl_ms=20000,
    )


@pytest.mark.asyncio
async def test_start_game_without_idempotency_also_uses_character_scoped_lock_key():
    user_id = get_uuid7()
    request = StartGameRequest(
        character_id=get_uuid7(),
        scenario_id=get_uuid7(),
        max_turns=20,
    )
    lock_mock = Mock(return_value=_noop_lock())
    cache_service = AsyncMock()
    cache_service.lock = lock_mock
    use_case = AsyncMock()
    use_case.execute.return_value = GameSessionResponse(
        id=get_uuid7(),
        character_id=request.character_id,
        scenario_id=request.scenario_id,
        current_location="시작 지점",
        game_state={},
        status="active",
        turn_count=0,
        max_turns=request.max_turns,
        ending_type=None,
        started_at=get_utc_datetime(),
        last_activity_at=get_utc_datetime(),
        image_url=None,
    )

    await start_game(
        request=request,
        use_case=use_case,
        cache_service=cache_service,
        idempotency_key=None,
        current_user=SimpleNamespace(id=user_id),
    )

    lock_mock.assert_called_once_with(
        f"game:start:character:{request.character_id}",
        ttl_ms=20000,
    )


@pytest.mark.asyncio
async def test_start_game_idempotency_conflict_for_different_payload():
    from app.common.exception import Conflict

    user_id = get_uuid7()
    cache_service = AsyncMock()
    use_case = AsyncMock()

    request = StartGameRequest(
        character_id=get_uuid7(),
        scenario_id=get_uuid7(),
        max_turns=10,
    )
    cache_service.get.return_value = (
        '{"payload_hash":"different","response":{"id":"x"}}'
    )

    with pytest.raises(Conflict):
        await start_game(
            request=request,
            use_case=use_case,
            cache_service=cache_service,
            idempotency_key="idempo-1",
            current_user=SimpleNamespace(id=user_id),
        )


@pytest.mark.asyncio
async def test_start_game_maps_active_session_error_to_409():
    user_id = get_uuid7()
    cache_service = AsyncMock()
    cache_service.get.return_value = None
    cache_service.lock = Mock(return_value=_noop_lock())
    use_case = AsyncMock()
    use_case.execute.side_effect = ValueError(
        "Character already has an active session"
    )

    request = StartGameRequest(
        character_id=get_uuid7(),
        scenario_id=get_uuid7(),
        max_turns=10,
    )

    with pytest.raises(HTTPException) as exc_info:
        await start_game(
            request=request,
            use_case=use_case,
            cache_service=cache_service,
            idempotency_key=None,
            current_user=SimpleNamespace(id=user_id),
        )

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_create_character_maps_invalid_scenario_to_404():
    use_case = AsyncMock()
    use_case.execute.side_effect = ValueError("Scenario not found or inactive")

    with pytest.raises(HTTPException) as exc_info:
        await create_character(
            request=CreateCharacterRequest(
                name="Hero",
                scenario_id=get_uuid7(),
                profile={
                    "age": 28,
                    "gender": "남성",
                    "appearance": "짙은 코트를 걸친 사내",
                },
            ),
            use_case=use_case,
            current_user=SimpleNamespace(id=get_uuid7()),
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_character_forwards_structured_profile_fields():
    use_case = AsyncMock()
    current_user = SimpleNamespace(id=get_uuid7())
    request = CreateCharacterRequest(
        name="실비아",
        scenario_id=get_uuid7(),
        profile={
            "age": 27,
            "gender": "여성",
            "appearance": "검은 단발과 오래된 흉터",
            "goal": "실종된 형을 찾는 것",
        },
    )

    await create_character(
        request=request,
        use_case=use_case,
        current_user=current_user,
    )

    input_data = use_case.execute.call_args.args[1]
    assert input_data.profile.age == 27
    assert input_data.profile.gender == "여성"
    assert input_data.profile.goal == "실종된 형을 찾는 것"
    assert input_data.profile.appearance == "검은 단발과 오래된 흉터"


def test_create_character_request_rejects_unknown_gender():
    with pytest.raises(ValidationError):
        CreateCharacterRequest(
            name="실비아",
            scenario_id=get_uuid7(),
            profile={
                "age": 27,
                "gender": "논바이너리",
                "appearance": "검은 단발과 오래된 흉터",
            },
        )
