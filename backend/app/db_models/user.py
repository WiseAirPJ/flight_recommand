"""사용자 모델"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship

from app.db_models.base import Base


class User(Base):
    """
    사용자 모델

    속성:
        email: 이메일 (로그인 ID)
        username: 사용자명
        hashed_password: 해시된 비밀번호
        full_name: 전체 이름
        is_active: 활성 상태
        is_superuser: 관리자 여부
        email_verified: 이메일 인증 여부
        last_login: 마지막 로그인 시간
    """

    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=True)

    # 상태 필드
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)

    # 로그인 정보
    last_login = Column(DateTime, nullable=True)

    # 관계 (다른 모델과의 연결)
    preferences = relationship(
        "UserPreference", back_populates="user", cascade="all, delete-orphan"
    )
    searches = relationship(
        "FlightSearch", back_populates="user", cascade="all, delete-orphan"
    )
    recommendations = relationship(
        "Recommendation", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"

    def to_dict(self):
        """비밀번호를 제외한 사용자 정보 반환"""
        data = super().to_dict()
        data.pop("hashed_password", None)  # 비밀번호는 절대 반환하지 않음
        return data
