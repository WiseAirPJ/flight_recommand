"""Admin collection requests use the same leased jobs as map queries and Beat."""

from datetime import datetime

from app.config.settings import settings
from app.models.flight_requests import MonthlySearchRequest
from app.services.monthly_search_service import MonthlySearchService


class CacheRefreshService:
    def __init__(self, search_service=None):
        self.search = search_service or MonthlySearchService()

    def _get_months_to_refresh(self, months_ahead=2):
        today = datetime.now().date()
        return [
            (ordinal // 12, ordinal % 12 + 1)
            for ordinal in range(
                today.year * 12 + today.month - 1,
                today.year * 12 + today.month - 1 + months_ahead,
            )
        ]

    def _schedule(self, origins, months, force_update, regions):
        tasks, failures = [], []
        for year, month in months:
            for origin in origins:
                result = self.search.request(
                    MonthlySearchRequest(year=year, month=month, origin=origin),
                    force_refresh=force_update,
                )
                if (
                    not result["success"]
                    or result.get("data", {}).get("refresh_status") == "failed"
                ):
                    failures.append({"year": year, "month": month, "origin": origin})
                elif result.get("enqueued"):
                    tasks.append(
                        {
                            "task_id": result["data"]["job_id"],
                            "year": year,
                            "month": month,
                            "origin": origin,
                        }
                    )
        return {
            "success": not failures,
            "message": f"{len(tasks)}개 수집 태스크 생성",
            "data": {
                "started_at": datetime.now().isoformat(),
                "regions": "all",
                "requested_regions": regions,
                "tasks_created": tasks,
                "failed_requests": failures,
            },
        }

    def refresh_cache(self, regions=None, force_update=False, origin="ICN"):
        result = self._schedule(
            [origin], self._get_months_to_refresh(), force_update, regions
        )
        result["data"].update(origin=origin, force_update=force_update)
        return result

    def warmup_cache(self, regions=None, months_ahead=3):
        result = self._schedule(
            settings.COLLECTION_ORIGINS,
            self._get_months_to_refresh(months_ahead),
            True,
            regions,
        )
        result["data"]["months_ahead"] = months_ahead
        return result
