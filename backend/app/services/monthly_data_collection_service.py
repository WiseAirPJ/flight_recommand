"""Worker adapter around the canonical monthly analyzer."""

import asyncio

from app.config.settings import settings
from app.core.database import init_db
from app.models.flight_requests import MonthlySearchRequest
from app.services.cache_admin_service import CacheAdminService
from app.services.cache_service import CacheService
from app.services.monthly_price_analyzer import MonthlyPriceAnalyzer
from app.utils.cache_keys import monthly_search_key


class MonthlyDataCollectionService:
    def __init__(self, cache_service=None, analyzer=None):
        self.cache_service = cache_service or CacheService()
        self.analyzer = analyzer or MonthlyPriceAnalyzer(
            cache_service=self.cache_service
        )

    async def collect_monthly_data(self, year, month, origin="ICN"):
        if settings.INIT_DB_ON_STARTUP:
            init_db()
        result = await self.analyzer.get_monthly_cheapest_dates(
            year, month, origin=origin, force_refresh=True
        )
        return {
            **result,
            "regions_collected": result["data"].get("total_regions", 0),
            "cache_saved": result["data"].get("cache_saved", False),
            "collected_at": result["data"].get("searched_at"),
        }

    def collect_monthly_data_sync(self, year, month, origin="ICN"):
        return asyncio.run(self.collect_monthly_data(year, month, origin))

    def is_month_data_available(self, year, month, origin="ICN"):
        request = MonthlySearchRequest(year=year, month=month, origin=origin)
        return self.cache_service.is_cache_valid(
            monthly_search_key(request, self.analyzer.amadeus_service.source)
        )

    def cleanup_expired_cache(self):
        return CacheAdminService(self.cache_service).cleanup_expired_cache()

    def get_collection_statistics(self):
        return CacheAdminService(self.cache_service).get_cache_statistics()
