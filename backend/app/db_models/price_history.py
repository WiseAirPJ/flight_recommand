"""가격 이력 모델"""

from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db_models.base import Base


class PriceHistory(Base):
    """
    항공권 가격 변동 이력 모델

    동일 항공편의 가격 변동을 추적하여 가격 트렌드 분석 및 알림에 활용

    속성:
        flight_id: 항공권 ID
        price_krw: 기록된 가격 (원화)
        price_jpy: 기록된 가격 (엔화)
        available_seats: 기록 시점의 남은 좌석 수
        source: 가격 출처 (amadeus, scraper 등)
    """

    __tablename__ = "price_histories"

    # 항공권 관계
    flight_id = Column(Integer, ForeignKey("flights.id"), nullable=False, index=True)

    # 가격 정보
    price_krw = Column(Float, nullable=False, comment="가격 (원화)")
    price_jpy = Column(Float, nullable=True, comment="가격 (엔화)")

    # 추가 정보
    available_seats = Column(Integer, nullable=True, comment="남은 좌석 수")
    source = Column(String(50), default="amadeus", nullable=False, comment="가격 출처")

    # 관계
    flight = relationship("Flight", back_populates="price_history")

    def __repr__(self):
        return (
            f"<PriceHistory(id={self.id}, flight_id={self.flight_id}, "
            f"price_krw={self.price_krw}, created_at={self.created_at})>"
        )

    @property
    def price_change(self) -> float:
        """
        이전 기록 대비 가격 변동률 계산

        주의: 이 메서드는 DB 쿼리가 필요하므로 사용 시 주의
        """
        # 실제 구현 시 이전 기록을 가져와서 계산
        # 여기서는 placeholder
        return 0.0
