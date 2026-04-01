"""Progression 게임 타입 상태 관리 서비스."""

from __future__ import annotations

import copy
import re
from typing import Any


class ProgressionStateService:
    """개월 기반 성장형 게임 상태를 관리한다."""

    ESCAPE_THRESHOLD = 120

    @staticmethod
    def build_initial_state(max_turns: int) -> dict[str, Any]:
        """신규 progression 세션의 초기 상태를 구성한다."""
        return {
            "hp": 100,
            "max_hp": 100,
            "internal_power": 5,
            "external_power": 10,
            "manuals": [],
            "traits": [],
            "title_candidates": [],
            "remaining_turns": max_turns,
        }

    @classmethod
    def build_status_panel(
        cls,
        state: dict[str, Any],
        turn_count: int,
        max_turns: int,
    ) -> dict[str, Any]:
        """현재 상태를 UI 친화적인 상태창 데이터로 변환한다."""
        manuals = state.get("manuals", [])
        total_mastery = sum(
            int(manual.get("mastery", 0))
            for manual in manuals
            if isinstance(manual, dict)
        )
        remaining_turns = max(0, max_turns - turn_count)
        total_power = (
            int(state.get("internal_power", 0))
            + int(state.get("external_power", 0))
            + total_mastery
        )

        return {
            "hp": int(state.get("hp", 100)),
            "max_hp": int(state.get("max_hp", 100)),
            "internal_power": int(state.get("internal_power", 0)),
            "external_power": int(state.get("external_power", 0)),
            "manuals": manuals,
            "remaining_turns": remaining_turns,
            "elapsed_turns": turn_count,
            "escape_status": cls._build_escape_status(total_power),
        }

    @classmethod
    def apply_state_changes(
        cls,
        current_state: dict[str, Any],
        parsed_response: dict[str, Any],
        turn_count: int,
        max_turns: int,
    ) -> dict[str, Any]:
        """LLM이 제안한 월간 변화량을 현재 상태에 반영한다."""
        new_state = dict(current_state)
        changes = parsed_response.get("state_changes", {})
        max_hp = int(new_state.get("max_hp", 100))
        hp = int(new_state.get("hp", 100)) + cls._bounded_int(
            changes.get("hp_change", 0), minimum=-40, maximum=20
        )
        new_state["hp"] = max(0, min(max_hp, hp))
        new_state["max_hp"] = max_hp

        new_state["internal_power"] = max(
            0,
            int(new_state.get("internal_power", 0))
            + cls._bounded_int(
                changes.get("internal_power_delta", 0),
                minimum=-5,
                maximum=25,
            ),
        )
        new_state["external_power"] = max(
            0,
            int(new_state.get("external_power", 0))
            + cls._bounded_int(
                changes.get("external_power_delta", 0),
                minimum=-5,
                maximum=25,
            ),
        )

        manuals = cls._normalize_manuals(new_state.get("manuals", []))
        manuals = cls._apply_manual_gains(
            manuals, changes.get("manuals_gained", [])
        )
        manuals = cls._apply_manual_mastery_updates(
            manuals, changes.get("manual_mastery_updates", [])
        )
        new_state["manuals"] = manuals

        traits = list(new_state.get("traits", []))
        for trait in changes.get("traits_gained", []):
            if isinstance(trait, str) and trait not in traits:
                traits.append(trait)
        new_state["traits"] = traits

        titles = list(new_state.get("title_candidates", []))
        for title in changes.get("title_candidates", []):
            if isinstance(title, str) and title not in titles:
                titles.append(title)
        new_state["title_candidates"] = titles
        new_state["remaining_turns"] = max(0, max_turns - turn_count)
        return new_state

    @classmethod
    def enrich_llm_response(
        cls,
        parsed_response: dict[str, Any],
        narrative: str,
        current_state: dict[str, Any],
        player_action: str = "",
    ) -> dict[str, Any]:
        """LLM이 누락한 progression 구조 정보를 서술에서 보정한다."""
        enriched = copy.deepcopy(parsed_response)
        state_changes = enriched.get("state_changes")
        if not isinstance(state_changes, dict):
            state_changes = {}
        enriched["state_changes"] = state_changes

        manuals = cls._normalize_manuals(current_state.get("manuals", []))
        existing_names = {manual["name"] for manual in manuals}

        normalized_gains = cls._normalize_manual_gains(
            state_changes.get("manuals_gained")
        )
        if normalized_gains:
            state_changes["manuals_gained"] = normalized_gains
        else:
            gained = cls._infer_manual_gains(narrative, existing_names)
            if gained:
                state_changes["manuals_gained"] = gained

        normalized_updates = cls._normalize_manual_mastery_updates(
            state_changes.get("manual_mastery_updates"), existing_names
        )
        if normalized_updates:
            state_changes["manual_mastery_updates"] = normalized_updates
        else:
            mastery_updates = cls._infer_manual_mastery_updates(
                narrative=narrative,
                player_action=player_action,
                manuals=manuals,
            )
            if mastery_updates:
                state_changes["manual_mastery_updates"] = mastery_updates

        return enriched

    @classmethod
    def build_achievement_board(
        cls,
        state: dict[str, Any],
        character_name: str,
        scenario_name: str,
        turn_count: int,
        max_turns: int,
    ) -> dict[str, Any]:
        """최종 엔딩용 업적 보드 데이터를 생성한다."""
        status_panel = cls.build_status_panel(state, turn_count, max_turns)
        manuals = status_panel["manuals"]
        total_mastery = sum(
            int(manual.get("mastery", 0))
            for manual in manuals
            if isinstance(manual, dict)
        )
        total_score = (
            status_panel["internal_power"]
            + status_panel["external_power"]
            + total_mastery
        )
        escaped = total_score >= cls.ESCAPE_THRESHOLD
        title = cls._resolve_title(total_score, escaped)
        return {
            "character_name": character_name,
            "scenario_name": scenario_name,
            "title": title,
            "escaped": escaped,
            "total_score": total_score,
            "hp": status_panel["hp"],
            "max_hp": status_panel["max_hp"],
            "internal_power": status_panel["internal_power"],
            "external_power": status_panel["external_power"],
            "manuals": manuals,
            "remaining_turns": status_panel["remaining_turns"],
            "summary": cls._build_board_summary(
                title=title,
                escaped=escaped,
                internal_power=status_panel["internal_power"],
                external_power=status_panel["external_power"],
                manuals=manuals,
            ),
        }

    @classmethod
    def build_final_image_prompt(
        cls, achievement_board: dict[str, Any]
    ) -> str:
        """최종 업적 보드용 이미지 생성 프롬프트를 만든다."""
        manuals = achievement_board.get("manuals", [])
        manual_names = ", ".join(
            manual.get("name", "")
            for manual in manuals
            if isinstance(manual, dict) and manual.get("name")
        )
        return (
            "Create a vertical wuxia achievement-board illustration. "
            "Use a Chinese martial arts animation atmosphere with a refined "
            "Japanese-anime-like protagonist. Show a powerful survivor "
            f"named {achievement_board['character_name']} standing in a "
            "mystic cave exit, with layered aura effects, ornamental stat "
            "panels, and trophy-card composition. "
            f"Internal power {achievement_board['internal_power']}, "
            f"external power {achievement_board['external_power']}, "
            f"title {achievement_board['title']}. "
            f"Featured manuals: {manual_names or 'none'}. "
            "Use dramatic lighting, premium collectible-card framing, and "
            "a polished endgame achievement mood."
        )

    @classmethod
    def _build_escape_status(cls, total_power: int) -> str:
        if total_power >= cls.ESCAPE_THRESHOLD:
            return "이제 동굴을 돌파할 수 있는 경지가 눈앞에 있습니다."
        if total_power >= cls.ESCAPE_THRESHOLD - 30:
            return "탈출의 가능성이 보이지만, 아직 한 수가 부족합니다."
        return "이 동굴은 현재 플레이어의 수준으로는 탈출할 수 없습니다."

    @staticmethod
    def _bounded_int(value: Any, minimum: int, maximum: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return 0
        return max(minimum, min(maximum, number))

    @classmethod
    def _normalize_manuals(cls, manuals: Any) -> list[dict[str, Any]]:
        if not isinstance(manuals, list):
            return []
        normalized: list[dict[str, Any]] = []
        for manual in manuals:
            if not isinstance(manual, dict):
                continue
            name = str(manual.get("name", "")).strip()
            if not name:
                continue
            normalized.append(
                {
                    "name": name,
                    "category": str(manual.get("category", "unknown")),
                    "mastery": cls._bounded_int(
                        manual.get("mastery", 0), 0, 100
                    ),
                    "aura": str(manual.get("aura", "neutral")),
                }
            )
        return normalized

    @classmethod
    def _apply_manual_gains(
        cls,
        manuals: list[dict[str, Any]],
        manuals_gained: Any,
    ) -> list[dict[str, Any]]:
        if not isinstance(manuals_gained, list):
            return manuals
        by_name = {manual["name"]: dict(manual) for manual in manuals}
        for gained in manuals_gained[:2]:
            if not isinstance(gained, dict):
                continue
            name = str(gained.get("name", "")).strip()
            if not name:
                continue
            by_name[name] = {
                "name": name,
                "category": str(gained.get("category", "unknown")),
                "mastery": cls._bounded_int(gained.get("mastery", 0), 0, 30),
                "aura": str(gained.get("aura", "neutral")),
            }
        return list(by_name.values())

    @classmethod
    def _apply_manual_mastery_updates(
        cls,
        manuals: list[dict[str, Any]],
        updates: Any,
    ) -> list[dict[str, Any]]:
        if not isinstance(updates, list):
            return manuals
        by_name = {manual["name"]: dict(manual) for manual in manuals}
        for update in updates[:5]:
            if not isinstance(update, dict):
                continue
            name = str(update.get("name", "")).strip()
            if not name or name not in by_name:
                continue
            delta = cls._bounded_int(update.get("mastery_delta", 0), 0, 35)
            if delta <= 0:
                continue
            by_name[name]["mastery"] = max(
                0,
                min(100, int(by_name[name].get("mastery", 0)) + delta),
            )
        return list(by_name.values())

    @classmethod
    def _normalize_manual_gains(
        cls, manuals_gained: Any
    ) -> list[dict[str, Any]]:
        if not isinstance(manuals_gained, list):
            return []
        normalized: list[dict[str, Any]] = []
        for gained in manuals_gained[:2]:
            if not isinstance(gained, dict):
                continue
            name = str(gained.get("name", "")).strip()
            if not name:
                continue
            normalized.append(
                {
                    "name": name,
                    "category": str(gained.get("category", "unknown")),
                    "mastery": cls._bounded_int(
                        gained.get("mastery", 0), 0, 30
                    )
                    or 5,
                    "aura": str(gained.get("aura", "neutral")),
                }
            )
        return normalized

    @classmethod
    def _normalize_manual_mastery_updates(
        cls,
        updates: Any,
        existing_names: set[str],
    ) -> list[dict[str, Any]]:
        if not isinstance(updates, list):
            return []
        normalized: list[dict[str, Any]] = []
        for update in updates[:5]:
            if not isinstance(update, dict):
                continue
            name = str(update.get("name", "")).strip()
            if not name or name not in existing_names:
                continue
            mastery_delta = cls._bounded_int(
                update.get("mastery_delta", 0), 0, 35
            )
            if mastery_delta <= 0:
                continue
            normalized.append({"name": name, "mastery_delta": mastery_delta})
        return normalized

    @classmethod
    def _infer_manual_gains(
        cls,
        narrative: str,
        existing_names: set[str],
    ) -> list[dict[str, Any]]:
        lowered = narrative.lower()
        if not any(
            keyword in lowered
            for keyword in (
                "기연",
                "비급",
                "발견",
                "획득",
                "손에 넣",
                "드러냈",
            )
        ):
            return []

        manual_names = cls._extract_manual_names(narrative)
        inferred: list[dict[str, Any]] = []
        for name in manual_names:
            if name in existing_names:
                continue
            inferred.append(
                {
                    "name": name,
                    "category": cls._infer_manual_category(name),
                    "mastery": cls._extract_manual_mastery(narrative) or 5,
                    "aura": "neutral",
                }
            )
        return inferred[:2]

    @classmethod
    def _infer_manual_mastery_updates(
        cls,
        narrative: str,
        player_action: str,
        manuals: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        combined_text = f"{player_action}\n{narrative}"
        lowered = combined_text.lower()
        if not any(
            keyword in lowered
            for keyword in ("수련", "연마", "숙련", "구결", "좌선", "깨달")
        ):
            return []

        updates: list[dict[str, Any]] = []
        for manual in manuals:
            name = manual["name"]
            if not cls._matches_manual_training_intent(
                manual=manual,
                combined_text=combined_text,
            ):
                continue
            explicit_mastery = cls._extract_manual_mastery(combined_text, name)
            current_mastery = int(manual.get("mastery", 0))
            if (
                explicit_mastery is not None
                and explicit_mastery > current_mastery
            ):
                delta = explicit_mastery - current_mastery
            else:
                delta = 5
            updates.append({"name": name, "mastery_delta": delta})
        if not updates and len(manuals) == 1:
            updates.append({"name": manuals[0]["name"], "mastery_delta": 5})
        return updates[:2]

    @classmethod
    def _matches_manual_training_intent(
        cls,
        manual: dict[str, Any],
        combined_text: str,
    ) -> bool:
        name = manual.get("name", "")
        category = str(manual.get("category", "unknown"))
        if name and name in combined_text:
            return True

        keyword_groups = {
            "internal": ("심법", "내공", "호흡", "좌선", "단전", "구결"),
            "movement": ("보법", "신법", "경공", "걸음", "발놀림"),
            "external": ("외공", "무공", "검법", "도법", "지법", "장법"),
        }
        for keyword in keyword_groups.get(category, ()):
            if keyword in combined_text:
                return True
        return False

    @staticmethod
    def _extract_manual_names(text: str) -> list[str]:
        pattern = re.compile(
            r"([가-힣A-Za-z0-9]+(?:심법|신공|보법|검법|도법|지법|장법|진법|검결)(?:\([^)]+\))?)"
        )
        names: list[str] = []
        for match in pattern.finditer(text):
            candidate = match.group(1).strip()
            if candidate and candidate not in names:
                names.append(candidate)
        return names

    @staticmethod
    def _infer_manual_category(name: str) -> str:
        if "심법" in name or "신공" in name:
            return "internal"
        if "보법" in name:
            return "movement"
        return "external"

    @staticmethod
    def _extract_manual_mastery(
        text: str, manual_name: str | None = None
    ) -> int | None:
        pattern_text = text
        if manual_name and manual_name in text:
            start_index = text.find(manual_name)
            pattern_text = text[start_index : start_index + 120]
        match = re.search(r"숙련도[:\s]*(\d+)%", pattern_text)
        if not match:
            return None
        return int(match.group(1))

    @classmethod
    def _resolve_title(cls, total_score: int, escaped: bool) -> str:
        if escaped and total_score >= 180:
            return "천하절정"
        if escaped:
            return "동굴파천객"
        if total_score >= 90:
            return "벽중수련객"
        return "동굴생환자"

    @staticmethod
    def _build_board_summary(
        title: str,
        escaped: bool,
        internal_power: int,
        external_power: int,
        manuals: list[dict[str, Any]],
    ) -> str:
        manual_summary = ", ".join(
            f"{manual['name']} {manual['mastery']}%"
            for manual in manuals
            if manual.get("name")
        )
        ending = "탈출 성공" if escaped else "탈출 실패"
        return (
            f"{title} | {ending} | "
            f"내공 {internal_power} | 외공 {external_power} | "
            f"비급 {manual_summary or '없음'}"
        )
