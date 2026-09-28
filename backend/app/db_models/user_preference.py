"""사용자 선호도 모델"""

from sqlalchemy import JSON, Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db_models.base import Base


class UserPreference(Base):
    """
    사용자 선호도 모델

    사용자의 항공권 선택 선호도를 저장하여 맞춤 추천에 활용

    속성:
        user_id: 사용자 ID (일대일 관계)
        preferred_airlines: 선호 항공사 (리스트)
        avoided_airlines: 기피 항공사 (리스트)
        preferred_cabin_class: 선호 좌석 등급
        max_stops: 최대 허용 경유 횟수
        preferred_departure_time: 선호 출발 시간대 (morning, afternoon, evening, night)
        price_priority: 가격 우선순위 (0-10, 높을수록 가격 중시)
        time_priority: 시간 우선순위 (0-10, 높을수록 시간 중시)
        comfort_priority: 편의성 우선순위 (0-10, 높을수록 편의성 중시)
        notification_enabled: 알림 설정
        price_alert_threshold: 가격 알림 임계값 (%)
        settings: 기타 설정 (JSON)
    """

    __tablename__ = "user_preferences"

    # 사용자 관계 (일대일)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # 항공사 선호도
    preferred_airlines = Column(
        JSON, nullable=True, comment="선호 항공사 코드 리스트 ['NH', 'JL']"
    )
    avoided_airlines = Column(JSON, nullable=True, comment="기피 항공사 코드 리스트")

    # 비행 선호도
    preferred_cabin_class = Column(String(20), default="economy", nullable=False)
    max_stops = Column(
        Integer, default=1, nullable=False, comment="최대 허용 경유 횟수"
    )
    preferred_departure_time = Column(
        String(20),
        nullable=True,
        comment="morning, afternoon, evening, night",
    )

    # 우선순위 (0-10 점수)
    price_priority = Column(
        Integer, default=7, nullable=False, comment="가격 우선순위 (0-10)"
    )
    time_priority = Column(
        Integer, default=5, nullable=False, comment="시간 우선순위 (0-10)"
    )
    comfort_priority = Column(
        Integer, default=5, nullable=False, comment="편의성 우선순위 (0-10)"
    )

    # 알림 설정
    notification_enabled = Column(Boolean, default=True, nullable=False)
    price_alert_threshold = Column(
        Float, default=10.0, nullable=False, comment="가격 하락 알림 임계값 (%)"
    )

    # 기타 설정
    settings = Column(JSON, nullable=True, comment="추가 사용자 설정")

    # 관계
    user = relationship("User", back_populates="preferences")

    def __repr__(self):
        return (
            f"<UserPreference(id={self.id}, user_id={self.user_id}, "
            f"price_priority={self.price_priority})>"
        )

    @property
    def priority_weights(self) -> dict:
        """우선순위를 가중치로 변환 (합계 1.0)"""
        total = self.price_priority + self.time_priority + self.comfort_priority
        if total == 0:
            return {"price": 0.33, "time": 0.33, "comfort": 0.34}

        return {
            "price": round(self.price_priority / total, 2),
            "time": round(self.time_priority / total, 2),
            "comfort": round(self.comfort_priority / total, 2),
        }
