# AI Saga 게임 가이드

이 문서는 현재 백엔드 구현 기준으로 게임 진행 규칙과 클라이언트가
알아야 하는 응답 계약을 정리한 문서입니다. 제품 기획서가 아니라
"지금 서버가 실제로 어떻게 동작하는가"에 초점을 둡니다.

## 1. 핵심 흐름

AI Saga의 기본 플레이 루프는 아래 순서로 진행됩니다.

1. 시나리오 목록 조회
2. 캐릭터 생성
3. 게임 세션 시작
4. 액션 제출과 AI 응답 수신
5. 세션/메시지 히스토리 조회
6. 엔딩 확정과 XP 정산

대표 엔드포인트는 아래와 같습니다.

- `GET /api/v1/game/scenarios/`
- `POST /api/v1/game/characters/`
- `POST /api/v1/game/sessions/`
- `POST /api/v1/game/sessions/{session_id}/actions/`
- `GET /api/v1/game/sessions/{session_id}/messages/`
- `POST /api/v1/game/sessions/{session_id}/messages/{message_id}/illustration/`

## 2. 시작 전 준비

### 시나리오

시나리오는 다음 정보를 제공합니다.

- 이름, 설명, 장르, 난이도
- `max_turns` 메타데이터
- 태그, 썸네일, hook, 추천 플레이어
- `world_setting`, `initial_location`

주의할 점은 현재 구현에서 세션 시작 시 기본 턴 수가 시나리오의
`max_turns`를 직접 따르지 않는다는 점입니다. 세션 기본값은
`settings.game_max_turns`이며 기본 설정은 `30`입니다.

### 캐릭터 생성

캐릭터 생성 요청은 이름, 시나리오 ID, 프로필을 받습니다.

```json
{
  "name": "레아",
  "scenario_id": "uuid",
  "profile": {
    "age": 24,
    "gender": "여성",
    "appearance": "짧은 은발과 검은 전투 코트",
    "goal": "사라진 언니를 찾는다"
  }
}
```

캐릭터 생성 시 유저의 영구 게임 레벨이 캐릭터 시작 레벨로 복사됩니다.

- 시작 레벨: `user.game_level`
- 시작 HP: `100 + (game_level - 1) * 10`

캐릭터 프로필은 프롬프트 입력에도 사용됩니다.

## 3. 세션 시작

세션 시작 요청은 캐릭터 ID, 시나리오 ID, 선택적 `max_turns`를
받습니다.

```json
{
  "character_id": "uuid",
  "scenario_id": "uuid",
  "max_turns": 30
}
```

규칙은 다음과 같습니다.

- `max_turns`는 생략 가능
- 생략 시 기본값은 `settings.game_max_turns`
- 요청 시 허용 범위는 `1~100`
- 동일 캐릭터에 이미 활성 세션이 있으면 `409`
- `Idempotency-Key` 헤더는 선택 사항
- 같은 `Idempotency-Key`에 다른 요청 본문을 보내면 `409`

응답에는 세션 정보와 선택적으로 초기 이미지 URL이 포함될 수 있습니다.

```json
{
  "id": "uuid",
  "character_id": "uuid",
  "scenario_id": "uuid",
  "current_location": "하늘빛 마을 - 모험가 길드 앞",
  "game_state": {},
  "status": "active",
  "turn_count": 0,
  "max_turns": 30,
  "ending_type": null,
  "started_at": "2026-03-13T00:00:00Z",
  "last_activity_at": "2026-03-13T00:00:00Z",
  "image_url": null
}
```

## 4. 턴 진행과 액션 처리

액션 제출 엔드포인트는 아래입니다.

- `POST /api/v1/game/sessions/{session_id}/actions/`

요청 본문:

```json
{
  "action": "문을 조심스럽게 열어본다",
  "action_type": "exploration"
}
```

처리 규칙은 다음과 같습니다.

- `Idempotency-Key` 헤더가 필수
- 세션 단위 Redis 락 사용
- 세션 소유권과 상태를 먼저 검증
- 턴 수를 먼저 1 증가
- 사용자 입력 임베딩을 생성해 메시지로 저장
- 최근 메시지와 유사 메시지를 합쳐 LLM 컨텍스트 구성
- 마지막 턴이면 일반 응답 대신 엔딩 응답 반환

### 컨텍스트 구성

현재 하이브리드 RAG 설정은 아래 값을 사용합니다.

- 최근 메시지: 최대 `10`
- 유사 메시지 최종 선택: 최대 `2`
- 거리 임계값: `0.3`
- 가중치: similarity `0.7`, recency `0.3`

메시지 임베딩은 Gemini 임베딩을 사용하고, DB에는 `pgvector(768)`로
저장됩니다.

## 5. 액션 타입과 주사위 판정

서버는 입력 텍스트를 보고 액션 타입을 다시 추론합니다.
클라이언트가 보낸 `action_type`은 힌트일 뿐이며 최종 판정 권한은
서버에 있습니다.

현재 액션 타입은 다음과 같습니다.

- `combat`
- `social`
- `skill`
- `movement`
- `observation`
- `rest`
- `exploration`

이 중 주사위 판정이 필요한 타입은 아래 네 가지입니다.

- `combat`
- `social`
- `skill`
- `exploration`

`movement`, `observation`, `rest`는 기본적으로 주사위 없이 처리됩니다.
예를 들어 무기를 꺼내는 준비 동작은 전투가 아니라 `observation`으로
분류됩니다.

### d20 규칙

- 기본 굴림: `1d20`
- 수정치: `(레벨 - 1) // 4 + 2`
- 성공 조건: `total >= dc`
- 크리티컬: `roll == 20`
- 펌블: `roll == 1`

난이도별 DC는 현재 아래 값입니다.

| 난이도 | DC |
| --- | --- |
| `easy` | 10 |
| `normal` | 13 |
| `hard` | 16 |
| `nightmare` | 19 |

레벨별 데미지 주사위는 아래와 같습니다.

| 레벨 | 주사위 |
| --- | --- |
| 1~2 | 1d4 |
| 3~4 | 1d6 |
| 5~6 | 1d8 |
| 7~8 | 1d10 |
| 9+ | 1d12 |

추가 규칙:

- 크리티컬이면 데미지 주사위 개수 2배
- 펌블이면 `1d4` 자해
- 서버는 펌블 자해를 LLM 응답보다 우선 적용
- 주사위 실패 시 `location`, `items_gained`는 차단
- 주사위 실패 시에도 `hp_change`, `items_lost`,
  `experience_gained`, `npcs_met`, `discoveries`는 유지 가능

## 6. 액션 응답 계약

일반 턴 응답은 `GameActionResponse`입니다.

```json
{
  "message": {
    "id": "uuid",
    "role": "assistant",
    "content": "...원본 LLM 응답...",
    "parsed_response": {
      "before_narrative": "당신은 검을 고쳐 쥐고 한 걸음 앞으로 나섭니다.",
      "narrative": "문은 오래된 쇠소리를 내며 반쯤만 열립니다.",
      "options": [
        {
          "label": "문틈으로 안을 살핀다",
          "action_type": "observation",
          "requires_dice": false
        }
      ],
      "dice_applied": true,
      "state_changes": {
        "hp_change": 0,
        "experience_gained": 10,
        "items_gained": [],
        "items_lost": [],
        "location": null,
        "npcs_met": [],
        "discoveries": ["문 안쪽에서 새어 나오는 푸른 빛"]
      }
    },
    "image_url": null,
    "created_at": "2026-03-13T00:00:00Z"
  },
  "narrative": "문은 오래된 쇠소리를 내며 반쯤만 열립니다.",
  "before_roll_narrative": "당신은 검을 고쳐 쥐고 한 걸음 앞으로 나섭니다.",
  "options": [
    {
      "label": "문틈으로 안을 살핀다",
      "action_type": "observation",
      "requires_dice": false
    }
  ],
  "turn_count": 1,
  "max_turns": 30,
  "is_ending": false,
  "state_changes": null,
  "image_url": null,
  "dice_result": {
    "roll": 14,
    "modifier": 2,
    "total": 16,
    "dc": 13,
    "is_success": true,
    "is_critical": false,
    "is_fumble": false,
    "check_type": "exploration",
    "damage": null,
    "display_text": "🎲 1d20+2 = 16 vs DC 13 → 성공!"
  },
  "xp_gained": null,
  "leveled_up": null,
  "new_game_level": null
}
```

클라이언트가 특히 신경 써야 할 필드는 아래입니다.

- `before_roll_narrative`
  주사위 연출 전 먼저 보여줄 문장. 없을 수도 있음
- `options`
  문자열이 아니라 정규화된 객체 배열
- `options[].action_type`
  다음 행동 버튼 라벨용 힌트
- `options[].requires_dice`
  프론트에서 연출을 준비할 때 참고하는 값
- `dice_result`
  서버가 실제로 계산한 판정 결과
- `is_ending`
  남은 턴이 1 이하일 때 `true`

주의할 점:

- `message.content`는 원본 LLM 응답
- `narrative`는 파싱된 최종 내러티브
- 메시지 히스토리에는 `message.content`와 `parsed_response`가 함께 저장됨

## 7. 엔딩과 XP

엔딩은 두 경로에서 발생합니다.

1. 턴 수가 최대치에 도달한 경우
2. 캐릭터 HP가 0 이하가 된 경우

최대 턴 도달 시:

- 최근 메시지 최대 10개를 바탕으로 LLM이 엔딩 생성
- 엔딩 타입은 `victory`, `defeat`, `neutral`
- 세션 상태는 `completed`

사망 시:

- 엔딩 타입은 항상 `defeat`
- 기존 내러티브 뒤에 사망 문구를 덧붙여 종료

XP 계산식은 현재 아래와 같습니다.

| 엔딩 | 계산 |
| --- | --- |
| `victory` | `200 + turn_count * 10` |
| `defeat` | `50 + turn_count * 5` |
| `neutral` | `100 + turn_count * 7` |

난이도 `hard`, `nightmare`는 최종 XP에 `1.5배`를 적용합니다.

유저 레벨업 규칙:

- 다음 게임 레벨 필요 XP: `current_game_level * 300`

캐릭터 세션 내 레벨업 규칙:

- 다음 레벨 필요 XP: `current_level * 100`
- 레벨업 시 최대 HP 증가: `10 * 현재 레벨`
- 레벨업 시 HP는 최대치로 즉시 회복

엔딩 응답 예시는 아래 형태입니다.

```json
{
  "session_id": "uuid",
  "ending_type": "victory",
  "narrative": "당신은 마침내 왕국을 위협하던 봉인의 핵을 파괴했다...",
  "total_turns": 30,
  "character_name": "레아",
  "scenario_name": "용사의 여정",
  "is_ending": true,
  "xp_gained": 450,
  "new_game_level": 2,
  "leveled_up": true,
  "levels_gained": 1
}
```

## 8. 세션과 메시지 조회

### 세션 목록

- `GET /api/v1/game/sessions/`
- cursor pagination 사용
- 응답 래퍼: `items`, `next_cursor`, `has_more`
- 상태 필터: `active|paused|completed|ended`

### 세션 단건

- `GET /api/v1/game/sessions/{session_id}/`
- `game_state`에서 `discoveries`, `visited_locations`는 제거된 형태로
  반환됨

### 메시지 히스토리

- `GET /api/v1/game/sessions/{session_id}/messages/`
- cursor pagination 사용
- 최신 메시지는 캐시 우회
- 과거 cursor 페이지는 Redis 캐시 가능

공개 API에는 현재 pause/resume 엔드포인트가 없습니다. 도메인 모델에는
`paused` 상태가 존재하지만, 외부 클라이언트가 직접 세션을 일시정지/
재개하는 라우트는 아직 구현되어 있지 않습니다.

## 9. 이미지 생성

이미지 관련 동작은 두 경로가 있습니다.

1. 세션 시작 시 초기 이미지 자동 생성 시도
2. 특정 AI 메시지에 대한 온디맨드 생성

온디맨드 엔드포인트:

- `POST /api/v1/game/sessions/{session_id}/messages/{message_id}/illustration/`

현재 규칙:

- `IMAGE_GENERATION_ENABLED=false`이면 `400`
- 요청한 메시지는 해당 유저 세션에 속해야 함
- AI 응답 메시지에만 생성 가능
- 이미 `image_url`이 있으면 재생성 없이 기존 URL 반환
- local 환경에서 기능이 켜져 있으면 dummy URL 반환
- local 외 환경에서는 Imagen 생성 후 R2 업로드 URL 반환 시도

대표 오류:

| 상태 코드 | 의미 |
| --- | --- |
| `400` | 기능 비활성화, 세션 불일치, USER 메시지 대상 |
| `403` | 타인 세션 접근 |
| `404` | 세션 또는 메시지 없음 |
| `500` | 이미지 생성 실패 |

## 10. 현재 미구현 또는 부분 구현 사항

아래 항목은 문서에서 제공 기능처럼 다루지 않아야 합니다.

- WebSocket 실시간 플레이 API
- 공개 pause/resume API
- 이벤트/Kafka 기반 멀티플레이 흐름
- 매 턴 자동 이미지 생성

`app/game/presentation/websocket/`과 `app/game/events/` 패키지는
현재 자리만 있고 실질적인 공개 기능은 연결되어 있지 않습니다.
