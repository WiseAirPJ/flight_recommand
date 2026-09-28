"""Schedule monthly collection without mixing task dispatch with cache storage."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.models.flight_requests import MonthlySearchRequest
from app.services.cache_service import CacheService
from app.utils.cache_keys import monthly_search_key

logger = logging.getLogger(__name__)


class CacheRefreshService:
    def __init__(self, cache_service=None):
        self.cache = cache_service if cache_service is not None else CacheService()

    def _get_months_to_refresh(self, months_ahead=2):
        today = datetime.now().date()
        months = []
        for offset in range(months_ahead):
            year, month = divmod(today.year * 12 + today.month - 1 + offset, 12)
            months.append((year, month + 1))
        return months

    def refresh_cache(
        self,
        regions: Optional[List[str]] = None,
        force_update: bool = False,
        origin: str = "ICN",
    ) -> Dict[str, Any]:
        """캐시 데이터 갱신"""
        try:
            from app.tasks.monthly_data_collection import collect_monthly_cheapest_data

            refresh_info = {
                "started_at": datetime.now().isoformat(),
                "origin": origin,
                "regions": "all",
                "requested_regions": regions,
                "force_update": force_update,
                "tasks_created": [],
            }

            from app.services.amadeus_service import AmadeusService

            source = AmadeusService().source
            for year, month in self._get_months_to_refresh():
                cache_key = monthly_search_key(
                    MonthlySearchRequest(origin=origin, year=year, month=month),
                    source,
                )

                if force_update or not self.cache.is_cache_valid(cache_key):
                    task = collect_monthly_cheapest_data.delay(year, month, origin)
                    refresh_info["tasks_created"].append(
                        {
                            "task_id": task.id,
                            "year": year,
                            "month": month,
                            "cache_key": cache_key,
                        }
                    )
                    logger.info(f"캐시 갱신 태스크 생성: {year}-{month:02d}")

            return {
                "success": True,
                "message": f"{len(refresh_info['tasks_created'])}개 갱신 태스크 생성",
                "data": refresh_info,
            }

        except Exception as e:
            logger.error(f"캐시 갱신 실패: {str(e)}")
            return {
                "success": False,
                "message": f"캐시 갱신 실패: {str(e)}",
                "data": {},
            }

    def warmup_cache(
        self, regions: Optional[List[str]] = None, months_ahead: int = 3
    ) -> Dict[str, Any]:
        """캐시 워밍업"""
        try:
            from app.tasks.monthly_data_collection import collect_monthly_cheapest_data

            warmup_info = {
                "started_at": datetime.now().isoformat(),
                "regions": "all",
                "requested_regions": regions,
                "months_ahead": months_ahead,
                "tasks_created": [],
            }

            for target_year, target_month in self._get_months_to_refresh(months_ahead):
                for origin in settings.COLLECTION_ORIGINS:
                    task = collect_monthly_cheapest_data.delay(
                        target_year, target_month, origin
                    )
                    warmup_info["tasks_created"].append(
                        {
                            "task_id": task.id,
                            "year": target_year,
                            "month": target_month,
                            "origin": origin,
                        }
                    )

            return {
                "success": True,
                "message": f"{len(warmup_info['tasks_created'])}개 워밍업 태스크 생성",
                "data": warmup_info,
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"캐시 워밍업 실패: {str(e)}",
                "data": {},
            }
