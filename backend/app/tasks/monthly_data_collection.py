"""All monthly collection entry points share durable job deduplication."""

import asyncio
from datetime import date, timedelta

from app.config.settings import settings
from app.models.flight_requests import MonthlySearchRequest
from app.services.cache_admin_service import CacheAdminService
from app.services.monthly_price_analyzer import MonthlyPriceAnalyzer
from app.services.monthly_search_service import LeaseLost, MonthlySearchService
from app.services.provider_source import configured_source
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3)
def run_monthly_search(self, key, token):
    store = MonthlySearchService()
    claimed = store.claim(key, token)
    if claimed is None:
        return {"status": "superseded"}
    payload, source, progress = claimed
    try:
        if source != configured_source():
            raise ValueError("Worker and API provider settings differ")
        request = MonthlySearchRequest(**payload)
        analyzer = MonthlyPriceAnalyzer()

        async def collect():
            async def save(checkpoint):
                await asyncio.to_thread(store.checkpoint, key, token, checkpoint)

            async def heartbeat():
                await asyncio.to_thread(store.heartbeat, key, token)

            return await analyzer.get_monthly_cheapest_dates(
                request.year,
                request.month,
                origin=request.origin,
                trip_duration=request.duration_days,
                adults=request.adults,
                currency=request.currency,
                non_stop=request.non_stop,
                force_refresh=True,
                progress=progress,
                save_progress=save,
                heartbeat=heartbeat,
            )

        result = asyncio.run(collect())
        if not result["success"] or result["data"].get("partial"):
            raise RuntimeError("Search or observation persistence incomplete")
        result["data"]["cache_saved"] = True  # durable result, independent of Redis TTL
        store.complete(key, token, result)
        return {"status": "ready", "job_id": token}
    except LeaseLost:
        return {"status": "superseded"}
    except Exception as exc:
        if self.request.retries >= self.max_retries or isinstance(exc, ValueError):
            store.fail(key, token, "수집에 실패했습니다. 잠시 후 다시 조회해 주세요.")
            raise
        delay = 60 * (2**self.request.retries)
        try:
            store.retry(key, token, delay)
        except LeaseLost:
            return {"status": "superseded"}
        raise self.retry(exc=exc, countdown=delay)


@celery_app.task
def collect_monthly_cheapest_data(year, month, origin="ICN"):
    """Compatibility task: schedule through the same deduplicated job path."""
    request = MonthlySearchRequest(year=year, month=month, origin=origin)
    return MonthlySearchService().request(request, force_refresh=True)


def _enqueue(year, month):
    store = MonthlySearchService()
    results = [
        store.request(
            MonthlySearchRequest(year=year, month=month, origin=origin),
            force_refresh=True,
        )
        for origin in settings.COLLECTION_ORIGINS
    ]
    return [result.get("data", {}).get("job_id") for result in results]


@celery_app.task
def collect_current_month_data():
    today = date.today()
    return _enqueue(today.year, today.month)


@celery_app.task
def collect_next_month_data():
    day = (date.today().replace(day=1) + timedelta(days=32)).replace(day=1)
    return _enqueue(day.year, day.month)


@celery_app.task
def collect_popular_months_data():
    today = date.today()
    return [
        task_id
        for month in [3, 4, 5, 10, 11]
        for task_id in _enqueue(today.year + (month < today.month), month)
    ]


@celery_app.task
def cleanup_expired_cache():
    return CacheAdminService().cleanup_expired_cache()


@celery_app.task
def update_cache_statistics():
    return CacheAdminService().get_cache_statistics()


def trigger_month_collection_if_needed(year, month, origin="ICN"):
    result = MonthlySearchService().request(
        MonthlySearchRequest(year=year, month=month, origin=origin)
    )
    return result.get("data", {}).get("job_id")
