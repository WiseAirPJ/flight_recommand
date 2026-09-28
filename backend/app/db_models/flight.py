"""항공권 모델"""

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db_models.base import Base


class Flight(Base):
    """
    항공권 모델

    Amadeus API에서 가져온 항공권 정보를 저장

    속성:
        amadeus_id: Amadeus API의 고유 ID
        airline_code: 항공사 코드 (예: NH, JL)
        airline_name: 항공사 이름 (예: ANA, JAL)
        flight_number: 항공편 번호
        departure_airport: 출발 공항 코드 (예: ICN)
        arrival_airport: 도착 공항 코드 (예: NRT, HND)
        departure_time: 출발 시간
        arrival_time: 도착 시간
        duration: 비행 시간 (분)
        stops: 경유 횟수
        price_krw: 가격 (원화)
        price_jpy: 가격 (엔화)
        cabin_class: 좌석 등급 (economy, business, first)
        available_seats: 남은 좌석 수
        is_direct: 직항 여부
        baggage_allowance: 수하물 허용량
        raw_data: API 원본 데이터 (JSON)
    """

    __tablename__ = "flights"

    # Amadeus API 정보
    amadeus_id = Column(String(255), unique=True, index=True, nullable=True)

    # 항공사 정보
    airline_code = Column(String(10), index=True, nullable=False)
    airline_name = Column(String(100), nullable=False)
    flight_number = Column(String(20), nullable=False)

    # 출발/도착 정보
    departure_airport = Column(String(10), index=True, nullable=False)
    arrival_airport = Column(String(10), index=True, nullable=False)
    departure_time = Column(DateTime, index=True, nullable=False)
    arrival_time = Column(DateTime, nullable=False)

    # 비행 정보
    duration = Column(Integer, nullable=False, comment="비행 시간 (분)")
    stops = Column(Integer, default=0, nullable=False, comment="경유 횟수")
    is_direct = Column(Boolean, default=True, nullable=False)

    # 가격 정보
    price_krw = Column(Float, index=True, nullable=False, comment="가격 (원화)")
    price_jpy = Column(Float, nullable=True, comment="가격 (엔화)")

    # 좌석 정보
    cabin_class = Column(
        String(20),
        default="economy",
        nullable=False,
        comment="economy, premium_economy, business, first",
    )
    available_seats = Column(Integer, nullable=True)
    baggage_allowance = Column(String(100), nullable=True, comment="20kg, 2PC 등")

    # 추가 정보
    raw_data = Column(JSON, nullable=True, comment="Amadeus API 원본 데이터")

    # 관계
    price_history = relationship(
        "PriceHistory", back_populates="flight", cascade="all, delete-orphan"
    )
    recommendations = relationship(
        "Recommendation", back_populates="flight", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"<Flight(id={self.id}, {self.airline_code}{self.flight_number}, "
            f"{self.departure_airport}->{self.arrival_airport}, "
            f"{self.price_krw}원)>"
        )

    @property
    def duration_hours(self) -> float:
        """비행 시간을 시간 단위로 반환"""
        return round(self.duration / 60, 1)

    @property
    def route(self) -> str:
        """노선 문자열 반환"""
        return f"{self.departure_airport}-{self.arrival_airport}"
