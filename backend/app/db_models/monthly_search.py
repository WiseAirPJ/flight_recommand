"""One durable result and leased collection job per exact monthly search."""

from sqlalchemy import JSON, Column, DateTime, String

from app.core.database import Base


class MonthlySearch(Base):
    __tablename__ = "monthly_searches"
    key = Column(String(200), primary_key=True)
    request = Column(JSON, nullable=False)
    source = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False)
    token = Column(String(32), nullable=False)
    lease_until = Column(DateTime, nullable=False)  # UTC, also retry cooldown
    result = Column(JSON, nullable=True)
    completed_at = Column(DateTime, nullable=True)  # UTC
    checkpoint = Column(JSON, nullable=False)
    error = Column(String(200), nullable=True)
