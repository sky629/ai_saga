"""Game Queries - Read-only operations (CQRS Query side).

Command와 분리된 읽기 전용 쿼리입니다.
상태를 변경하지 않고 데이터만 조회합니다.
"""

from .get_scenarios import GetScenariosQuery
from .get_user_sessions import GetUserSessionsQuery
from .get_session_history import GetSessionHistoryQuery

__all__ = [
    "GetScenariosQuery",
    "GetUserSessionsQuery",
    "GetSessionHistoryQuery",
]
