"""Persist provider observations, never demo or test-environment prices."""

import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.db_models.price_observation import PriceObservation


class PriceHistoryService:
    def __init__(self, session_factory=None):
        self.session_factory = session_factory or SessionLocal

    def record_offers(
        self,
        offers,
        *,
        origin,
        destination,
        departure_date,
        return_date,
        adults,
        currency,
        source,
        non_stop=False,
        observed_at=None,
    ):
        if source != "amadeus":
            return 0
        timestamp = observed_at or datetime.now(timezone.utc)
        observations = []
        for offer in offers:
            price = offer.get("price", {})
            try:
                amount = Decimal(str(price["total"]))
            except KeyError, InvalidOperation:
                continue
            if (
                not amount.is_finite()
                or amount <= 0
                or price.get("currency") != currency
            ):
                continue
            itineraries = offer.get("itineraries", [])
            observations.append(
                PriceObservation(
                    observation_key=hashlib.sha256(
                        json.dumps(
                            [
                                timestamp.isoformat(),
                                origin,
                                destination,
                                departure_date,
                                return_date,
                                adults,
                                currency,
                                source,
                                non_stop,
                                offer,
                            ],
                            sort_keys=True,
                            default=str,
                        ).encode()
                    ).hexdigest(),
                    observed_at=timestamp,
                    origin=origin,
                    destination=destination,
                    departure_date=date.fromisoformat(departure_date),
                    return_date=(
                        date.fromisoformat(return_date) if return_date else None
                    ),
                    adults=adults,
                    currency=currency,
                    total_price=amount,
                    source=source,
                    offer_id=offer.get("id"),
                    search_conditions={
                        "non_stop": non_stop,
                        "cabin": "ECONOMY",
                        "trip_type": "round-trip" if return_date else "one-way",
                    },
                    fare_conditions={
                        "price": price,
                        "original_price": offer.get("original_price", price),
                        "exchange_rate": offer.get("exchange_rate"),
                        "itineraries": itineraries,
                        "traveler_pricings": offer.get("travelerPricings", []),
                        "baggage_policy": "provider_terms",
                    },
                )
            )
        if observations:
            with self.session_factory() as session:
                for observation in observations:
                    try:
                        with session.begin_nested():
                            session.add(observation)
                            session.flush()
                    except IntegrityError:
                        existing = session.scalar(
                            select(PriceObservation.id).where(
                                PriceObservation.observation_key
                                == observation.observation_key
                            )
                        )
                        if existing is None:
                            raise
                session.commit()
        return len(observations)
