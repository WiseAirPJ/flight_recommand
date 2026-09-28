"""항공권 검색 이력 모델"""

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db_models.base import Base


class FlightSearch(Base):
    """
    항공권 검색 이력 모델

    사용자의 검색 조건과 결과를 저장하여 분석 및 추천에 활용

    속성:
        user_id: 사용자 ID (외래키)
        departure_airport: 출발 공항
        arrival_airport: 도착 공항
        departure_date: 출발 날짜
        return_date: 귀국 날짜 (편도인 경우 null)
        passengers: 승객 수
        cabin_class: 좌석 등급
        max_price: 최대 가격 (선택)
        results_count: 검색 결과 수
        search_params: 검색 파라미터 (JSON)
    """

    __tablename__ = "flight_searches"

    # 사용자 관계
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 검색 조건
    departure_airport = Column(String(10), nullable=False)
    arrival_airport = Column(String(10), nullable=False)
    departure_date = Column(DateTime, nullable=False)
    return_date = Column(DateTime, nullable=True, comment="편도인 경우 null")

    # 추가 조건
    passengers = Column(Integer, default=1, nullable=False)
    cabin_class = Column(String(20), default="economy", nullable=False)
    max_price = Column(Integer, nullable=True, comment="최대 가격 필터 (원화)")

    # 검색 결과
    results_count = Column(Integer, default=0, nullable=False)
    search_params = Column(JSON, nullable=True, comment="전체 검색 파라미터")

    # 관계
    user = relationship("User", back_populates="searches")

    def __repr__(self):
        return (
            f"<FlightSearch(id={self.id}, user_id={self.user_id}, "
            f"{self.departure_airport}->{self.arrival_airport}, "
            f"{self.departure_date.strftime('%Y-%m-%d')})>"
        )

    @property
    def is_round_trip(self) -> bool:
        """왕복 여부"""
        return self.return_date is not None

    @property
    def route(self) -> str:
        """노선 문자열"""
        return f"{self.departure_airport}-{self.arrival_airport}"
