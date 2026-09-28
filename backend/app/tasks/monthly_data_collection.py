"""Every worker task is registered on one Celery application."""

from datetime import date, timedelta

from app.config.settings import settings
from app.services.monthly_data_collection_service import MonthlyDataCollectionService
from app.tasks.celery_app import celery_app


@celery_app.task(
    autoretry_for=(RuntimeError,), retry_backoff=60, retry_kwargs={"max_retries": 3}
)
def collect_monthly_cheapest_data(year, month, origin="ICN"):
    result = MonthlyDataCollectionService().collect_monthly_data_sync(
        year, month, origin
    )
    if not result["success"] or result["data"].get("partial"):
        raise RuntimeError(result["message"])
    return result


def _enqueue(year, month):
    return [
        collect_monthly_cheapest_data.delay(year, month, origin).id
        for origin in settings.COLLECTION_ORIGINS
    ]


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
    return MonthlyDataCollectionService().cleanup_expired_cache()


@celery_app.task
def update_cache_statistics():
    return MonthlyDataCollectionService().get_collection_statistics()


def is_month_data_available(year, month, origin="ICN"):
    return MonthlyDataCollectionService().is_month_data_available(year, month, origin)


def trigger_month_collection_if_needed(year, month, origin="ICN"):
    if is_month_data_available(year, month, origin):
        return "already_exists"
    return collect_monthly_cheapest_data.delay(year, month, origin).id
