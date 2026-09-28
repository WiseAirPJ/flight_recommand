"""베이스 모델 - 모든 모델의 공통 필드"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.ext.declarative import declared_attr

from app.core.database import Base as SQLAlchemyBase


class Base(SQLAlchemyBase):
    """
    모든 모델의 베이스 클래스

    공통 필드:
    - id: 기본 키
    - created_at: 생성 시간
    - updated_at: 수정 시간
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    @declared_attr
    def __tablename__(cls) -> str:
        """테이블 이름 자동 생성 (클래스명의 스네이크 케이스)"""
        import re

        name = cls.__name__
        return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

    def to_dict(self):
        """모델을 딕셔너리로 변환"""
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

    def __repr__(self):
        """모델의 문자열 표현"""
        return f"<{self.__class__.__name__}(id={self.id})>"
