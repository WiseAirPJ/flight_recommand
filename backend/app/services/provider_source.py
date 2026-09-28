"""Provider identity without constructing an SDK client or opening connections."""

from app.config.settings import settings


def configured_source(active=None):
    if active is None:
        active = settings.USE_REAL_AMADEUS
    if active:
        return (
            "amadeus" if settings.AMADEUS_HOSTNAME == "production" else "amadeus_test"
        )
    return "demo" if settings.ENABLE_DUMMY_FALLBACK else "unavailable"
