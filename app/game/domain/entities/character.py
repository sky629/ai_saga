"""Character Domain Entity."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CharacterProfile(BaseModel):
    """캐릭터 온보딩 프로필."""

    model_config = {"frozen": True}

    age: int = Field(ge=0)
    gender: Literal["남성", "여성", "비공개"]
    appearance: str = Field(min_length=1, max_length=300)
    goal: Optional[str] = Field(default=None, max_length=300)

    def build_summary(self, name: str) -> str:
        """프롬프트와 호환용 설명에 사용할 요약 문자열 생성."""
        parts = [
            f"이름: {name}.",
            f"나이: {self.age}세.",
            f"성별: {self.gender}.",
            f"외형: {self.appearance}.",
        ]
        if self.goal:
            parts.append(f"목표: {self.goal}.")
        return " ".join(parts)


class CharacterStats(BaseModel):
    """캐릭터 스탯 Value Object."""

    model_config = {"frozen": True}

    hp: int = Field(ge=0, default=100)
    max_hp: int = Field(gt=0, default=100)
    level: int = Field(ge=1, default=1)
    experience: int = Field(ge=0, default=0)
    current_experience: int = Field(ge=0, default=0)

    def take_damage(self, amount: int) -> "CharacterStats":
        """데미지를 받은 새 스탯 반환."""
        new_hp = max(0, self.hp - amount)
        return self.model_copy(update={"hp": new_hp})

    def heal(self, amount: int) -> "CharacterStats":
        """회복한 새 스탯 반환."""
        new_hp = min(self.max_hp, self.hp + amount)
        return self.model_copy(update={"hp": new_hp})

    def level_up(self) -> "CharacterStats":
        """레벨업한 새 스탯 반환 (레벨에 비례한 스탯 상승)."""
        hp_increase = 10 * self.level
        return self.model_copy(
            update={
                "level": self.level + 1,
                "max_hp": self.max_hp + hp_increase,
                "hp": self.max_hp + hp_increase,  # Full heal on level up
            }
        )

    def experience_for_next_level(self) -> int:
        """다음 레벨까지 필요한 경험치 계산.

        Returns:
            필요 경험치 (level * 100)
        """
        return self.level * 100

    def gain_experience(self, amount: int) -> "CharacterStats":
        """경험치 획득 및 자동 레벨업.

        Args:
            amount: 획득할 경험치량

        Returns:
            업데이트된 새 스탯 (레벨업 포함)
        """
        new_exp = self.experience + amount
        new_current_exp = self.current_experience + amount
        new_stats = self.model_copy(
            update={
                "experience": new_exp,
                "current_experience": new_current_exp,
            }
        )

        # 자동 레벨업 (여러 레벨 가능)
        while (
            new_stats.current_experience
            >= new_stats.experience_for_next_level()
        ):
            new_stats = new_stats._level_up_once()

        return new_stats

    def _level_up_once(self) -> "CharacterStats":
        """한 레벨 상승 (내부 메서드).

        Returns:
            레벨업된 새 스탯
        """
        required_exp = self.experience_for_next_level()
        remaining_exp = self.current_experience - required_exp
        hp_increase = 10 * self.level

        return self.model_copy(
            update={
                "level": self.level + 1,
                "max_hp": self.max_hp + hp_increase,
                "hp": self.max_hp + hp_increase,  # Full heal on level up
                "current_experience": remaining_exp,
            }
        )

    @property
    def is_alive(self) -> bool:
        """생존 상태 확인."""
        return self.hp > 0


class CharacterEntity(BaseModel):
    """캐릭터 도메인 엔티티.

    플레이어 캐릭터의 핵심 속성과 비즈니스 로직을 포함합니다.
    """

    model_config = {"frozen": True}

    id: UUID
    user_id: UUID
    scenario_id: UUID
    name: str = Field(min_length=1, max_length=100)
    profile: Optional[CharacterProfile] = None
    stats: CharacterStats = Field(default_factory=CharacterStats)
    inventory: list = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime

    # === Domain Methods ===

    def update_stats(self, new_stats: CharacterStats) -> "CharacterEntity":
        """스탯을 업데이트한 새 인스턴스 반환."""
        return self.model_copy(update={"stats": new_stats})

    def add_to_inventory(self, item: str) -> "CharacterEntity":
        """인벤토리에 아이템 추가."""
        new_inventory = [*self.inventory, item]
        return self.model_copy(update={"inventory": new_inventory})

    def remove_from_inventory(self, item: str) -> "CharacterEntity":
        """인벤토리에서 아이템 제거."""
        if item not in self.inventory:
            raise ValueError(f"Item {item} not in inventory")
        new_inventory = [i for i in self.inventory if i != item]
        return self.model_copy(update={"inventory": new_inventory})

    def deactivate(self) -> "CharacterEntity":
        """캐릭터 비활성화 (소프트 삭제)."""
        return self.model_copy(update={"is_active": False})

    # === Domain Properties ===

    @property
    def is_alive(self) -> bool:
        """캐릭터 생존 상태."""
        return self.stats.is_alive and self.is_active

    @property
    def prompt_profile(self) -> str:
        """프롬프트용 캐릭터 프로필 요약."""
        if not self.profile:
            return ""
        return self.profile.build_summary(self.name)
