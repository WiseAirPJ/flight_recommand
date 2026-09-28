"""Immutable observed fares with the conditions needed for later comparisons."""

from sqlalchemy import JSON, Column, Date, DateTime, Index, Integer, Numeric, String

from app.core.database import Base


class PriceObservation(Base):
    __tablename__ = "price_observations"
    id = Column(Integer, primary_key=True)
    observation_key = Column(String(64), nullable=True)
    observed_at = Column(DateTime(timezone=True), nullable=False)
    origin = Column(String(3), nullable=False)
    destination = Column(String(3), nullable=False)
    departure_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=True)
    adults = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False)
    total_price = Column(Numeric(14, 2), nullable=False)
    source = Column(String(30), nullable=False)
    offer_id = Column(String(200), nullable=True)
    search_conditions = Column(JSON, nullable=False)
    fare_conditions = Column(JSON, nullable=False)
    __table_args__ = (
        Index("ix_observation_key", "observation_key", unique=True),
        Index(
            "ix_observation_route_departure", "origin", "destination", "departure_date"
        ),
        Index("ix_observation_observed_at", "observed_at"),
    )
