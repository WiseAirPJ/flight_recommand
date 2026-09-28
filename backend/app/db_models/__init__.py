"""데이터베이스 모델"""

from app.db_models.base import Base
from app.db_models.flight import Flight
from app.db_models.flight_search import FlightSearch
from app.db_models.price_history import PriceHistory
from app.db_models.price_observation import PriceObservation
from app.db_models.recommendation import Recommendation
from app.db_models.user import User
from app.db_models.user_preference import UserPreference

__all__ = [
    "Base",
    "User",
    "Flight",
    "FlightSearch",
    "Recommendation",
    "UserPreference",
    "PriceHistory",
    "PriceObservation",
]
