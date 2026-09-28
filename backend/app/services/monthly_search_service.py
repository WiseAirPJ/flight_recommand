"""Serve durable monthly results and enqueue a single leased job.

All methods are synchronous: HTTP callers offload the whole operation. Database
compare-and-swap updates coordinate API instances and Celery workers; no local
lock or memory cache is used for job ownership.
"""

import logging
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from app.config.settings import settings
from app.core.database import SessionLocal
from app.db_models.monthly_search import MonthlySearch
from app.services.provider_source import configured_source
from app.utils.cache_keys import monthly_search_key

logger = logging.getLogger(__name__)


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class LeaseLost(RuntimeError):
    pass


class MonthlySearchService:
    def __init__(self, session_factory=None, enqueue=None, clock=None, source=None):
        self.sessions = session_factory or SessionLocal
        self.enqueue = enqueue or self._enqueue
        self.clock = clock or utcnow
        self.source = source or configured_source()

    @staticmethod
    def _enqueue(key, token):
        from app.tasks.monthly_data_collection import run_monthly_search

        run_monthly_search.apply_async(args=[key, token], task_id=token, retry=False)

    def request(self, request, force_refresh=False):
        if self.source == "unavailable":
            return {
                "success": False,
                "status_code": 503,
                "message": "항공권 검색 공급자가 설정되지 않았습니다.",
            }
        # A sampling-policy change must not reuse an incompatible checkpoint.
        key = f"{monthly_search_key(request, self.source)}:step{settings.MONTHLY_SAMPLE_STEP}"
        now, token = self.clock(), uuid4().hex
        queued = False
        with self.sessions() as session:
            row = session.get(MonthlySearch, key)
            if row is None:
                row = MonthlySearch(
                    key=key,
                    request=request.model_dump(mode="json"),
                    source=self.source,
                    status="pending",
                    token=token,
                    lease_until=now
                    + timedelta(seconds=settings.MONTHLY_JOB_LEASE_SECONDS),
                    checkpoint={},
                )
                session.add(row)
                try:
                    session.commit()
                    queued = True
                except IntegrityError:
                    session.rollback()
                    row = session.get(MonthlySearch, key)
            fresh = self._is_fresh(row)
            if not queued and (force_refresh or not fresh) and row.lease_until <= now:
                # Only the owner of this version can claim it. A concurrent caller
                # will observe its pending token and return the same job.
                old_token = row.token
                resume = (
                    row.status != "ready"
                    and row.checkpoint.get("day") == date.today().isoformat()
                )
                claimed = session.execute(
                    update(MonthlySearch)
                    .where(
                        MonthlySearch.key == key,
                        MonthlySearch.token == old_token,
                        MonthlySearch.lease_until <= now,
                    )
                    .values(
                        status="pending",
                        token=token,
                        error=None,
                        lease_until=now
                        + timedelta(seconds=settings.MONTHLY_JOB_LEASE_SECONDS),
                        checkpoint=row.checkpoint if resume else {},
                    )
                ).rowcount
                session.commit()
                queued = bool(claimed)
        if queued:
            try:
                self.enqueue(key, token)
            except Exception:
                logger.exception("Monthly collection dispatch failed")
                self.fail(key, token, "수집 작업을 예약하지 못했습니다.")
        with self.sessions() as session:
            row = session.get(MonthlySearch, key)
            result = self._response(row)
            result["enqueued"] = queued and row.status != "failed"
            return result

    def _is_fresh(self, row):
        now = self.clock()
        return (
            row.result is not None
            and row.completed_at is not None
            and row.completed_at.date() == now.date()
            and (now - row.completed_at).total_seconds() < settings.MONTHLY_CACHE_TTL
        )

    def _response(self, row):
        now = self.clock()
        available = (
            row.result is not None
            and row.completed_at is not None
            and (now - row.completed_at).total_seconds() <= settings.MONTHLY_STALE_TTL
        )
        fresh = available and self._is_fresh(row)
        if available:
            result = deepcopy(row.result)
            # A previous day's cheapest departure must not remain bookable on the map.
            for region_id, region in list(result["data"]["regions"].items()):
                options = [
                    o
                    for o in region["all_options"]
                    if o["departure_date"] > date.today().isoformat()
                ]
                if not options:
                    del result["data"]["regions"][region_id]
                else:
                    region["all_options"] = options[:5]
                    prices = [option["price"] for option in options]
                    region["price_statistics"] = {
                        "min_price": min(prices),
                        "max_price": max(prices),
                        "avg_price": round(sum(prices) / len(prices), 2),
                        "price_samples": len(prices),
                    }
                    region["cheapest_option"] = options[0]
                    region["airport"] = options[0]["airport"]
            result["data"]["total_regions"] = len(result["data"]["regions"])
        else:
            result = {
                "success": True,
                "message": "가격을 수집하고 있습니다. 잠시 후 다시 조회해 주세요.",
                "data": {
                    **row.request,
                    "regions": {},
                    "total_regions": 0,
                    "source": row.source,
                    "is_demo": row.source == "demo",
                    "searched_at": None,
                    "coverage": "sampled_dates",
                    "cache_saved": False,
                },
            }
        if available and not fresh:
            result["message"] = (
                "이전에 조회한 가격입니다. 갱신 상태와 가격 조회 시각을 확인하세요."
            )
        result["data"].update(
            from_cache=available,
            stale=bool(available and not fresh),
            status="ready" if fresh else ("stale" if available else row.status),
            refresh_status=row.status,
            job_id=row.token,
            refresh_error=row.error,
        )
        result["status_code"] = (
            200 if available else (503 if row.status == "failed" else 202)
        )
        result["success"] = available or row.status != "failed"
        if row.status == "failed" and not available:
            result["message"] = row.error
        return result

    def claim(self, key, token):
        now = self.clock()
        with self.sessions() as session:
            claimed = session.execute(
                update(MonthlySearch)
                .where(
                    MonthlySearch.key == key,
                    MonthlySearch.token == token,
                    MonthlySearch.status == "pending",
                    MonthlySearch.lease_until > now,
                )
                .values(
                    status="running",
                    lease_until=now
                    + timedelta(seconds=settings.MONTHLY_JOB_LEASE_SECONDS),
                )
            ).rowcount
            session.commit()
            if not claimed:
                return None
            row = session.get(MonthlySearch, key)
            return row.request, row.source, deepcopy(row.checkpoint)

    def checkpoint(self, key, token, progress):
        self._owned_update(key, token, checkpoint=progress)

    def heartbeat(self, key, token):
        self._owned_update(key, token)

    def complete(self, key, token, result):
        self._owned_update(
            key,
            token,
            result=result,
            completed_at=self.clock(),
            status="ready",
            checkpoint={},
            error=None,
            lease_until=self.clock(),
        )

    def retry(self, key, token, delay):
        # A redelivery of the previous attempt must not claim its successor.
        next_token = uuid4().hex
        self._owned_update(
            key,
            token,
            token=next_token,
            status="pending",
            error="일부 검색 또는 이력 저장을 재시도합니다.",
            lease_until=self.clock()
            + timedelta(seconds=delay + settings.MONTHLY_JOB_LEASE_SECONDS),
        )
        return next_token

    def _owned_update(self, key, owner_token, **values):
        now = self.clock()
        values.setdefault(
            "lease_until", now + timedelta(seconds=settings.MONTHLY_JOB_LEASE_SECONDS)
        )
        with self.sessions() as session:
            count = session.execute(
                update(MonthlySearch)
                .where(
                    MonthlySearch.key == key,
                    MonthlySearch.token == owner_token,
                    MonthlySearch.status == "running",
                    MonthlySearch.lease_until > now,
                )
                .values(**values)
            ).rowcount
            session.commit()
            if not count:
                raise LeaseLost("Collection ownership expired or changed")

    def fail(self, key, token, message):
        with self.sessions() as session:
            session.execute(
                update(MonthlySearch)
                .where(
                    MonthlySearch.key == key,
                    MonthlySearch.token == token,
                    MonthlySearch.status.in_(["pending", "running"]),
                )
                .values(
                    status="failed",
                    error=message,
                    lease_until=self.clock() + timedelta(seconds=60),
                )
            )
            session.commit()
