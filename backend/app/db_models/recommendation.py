"""AI 추천 모델"""

from sqlalchemy import JSON, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db_models.base import Base


class Recommendation(Base):
    """
    AI 항공권 추천 모델

    Azure OpenAI 또는 Anthropic API를 사용한 AI 분석 결과 저장

    속성:
        user_id: 사용자 ID
        flight_id: 추천 항공권 ID
        score: 추천 점수 (0-100)
        rank: 추천 순위
        reason: 추천 이유 (AI 생성)
        value_score: 가성비 점수
        time_score: 시간 효율성 점수
        comfort_score: 편의성 점수
        price_analysis: 가격 분석 (AI 생성)
        ai_model: 사용된 AI 모델 (gpt-4.1, claude-3 등)
        ai_response: AI 원본 응답 (JSON)
    """

    __tablename__ = "recommendations"

    # 사용자 및 항공권 관계
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    flight_id = Column(Integer, ForeignKey("flights.id"), nullable=False, index=True)

    # 추천 정보
    score = Column(Float, nullable=False, comment="전체 추천 점수 (0-100)")
    rank = Column(Integer, nullable=False, index=True, comment="추천 순위")

    # AI 분석 결과
    reason = Column(Text, nullable=False, comment="추천 이유 (AI 생성)")
    price_analysis = Column(Text, nullable=True, comment="가격 분석 (AI 생성)")

    # 세부 점수
    value_score = Column(Float, nullable=True, comment="가성비 점수 (0-100)")
    time_score = Column(Float, nullable=True, comment="시간 효율성 점수 (0-100)")
    comfort_score = Column(Float, nullable=True, comment="편의성 점수 (0-100)")

    # AI 메타 정보
    ai_model = Column(
        String(50), nullable=False, comment="사용된 AI 모델 (gpt-4.1, claude-3 등)"
    )
    ai_response = Column(JSON, nullable=True, comment="AI 원본 응답")

    # 관계
    user = relationship("User", back_populates="recommendations")
    flight = relationship("Flight", back_populates="recommendations")

    def __repr__(self):
        return (
            f"<Recommendation(id={self.id}, user_id={self.user_id}, "
            f"flight_id={self.flight_id}, score={self.score}, rank={self.rank})>"
        )

    @property
    def overall_score(self) -> float:
        """
        전체 점수 계산 (세부 점수가 있는 경우)

        가성비 40%, 시간 효율성 30%, 편의성 30%
        """
        if all([self.value_score, self.time_score, self.comfort_score]):
            return round(
                self.value_score * 0.4
                + self.time_score * 0.3
                + self.comfort_score * 0.3,
                1,
            )
        return self.score
