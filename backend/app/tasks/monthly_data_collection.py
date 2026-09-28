import logging
from datetime import date
from typing import Any, Dict, List

from celery import Celery
from celery.schedules import crontab

from app.config.settings import settings
from app.services.cache_service import CacheService
from app.services.monthly_data_collection_service import MonthlyDataCollectionService

# Celery 앱 설정
celery_app = Celery(
    "monthly_flight_analyzer",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# 서비스 인스턴스
cache_service = CacheService()
collection_service = MonthlyDataCollectionService(cache_service)

logger = logging.getLogger(__name__)


# 메인 데이터 수집 태스크


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3})
def collect_monthly_cheapest_data(self, year: int, month: int, origin: str = "ICN"):
    """
    특정 월의 지역별 최저가 데이터 수집

    Args:
        year: 대상 연도
        month: 대상 월
        origin: 출발지 공항 코드
    """
    try:
        logger.info(f"월별 데이터 수집 작업 시작: {year}년 {month}월, 출발지: {origin}")

        # 서비스를 통한 데이터 수집
        result = collection_service.collect_monthly_data_sync(
            year=year, month=month, origin=origin
        )

        if result["success"]:
            # 작업 상태 업데이트
            self.update_state(
                state="SUCCESS",
                meta={
                    "year": year,
                    "month": month,
                    "origin": origin,
                    "regions_collected": result.get("regions_collected", 0),
                    "cache_saved": result.get("cache_saved", False),
                    "collected_at": result.get("collected_at"),
                },
            )

            logger.info(f"월별 데이터 수집 작업 완료: {year}-{month:02d} from {origin}")
            return result["message"]

        else:
            raise Exception(result.get("message", "Unknown error"))

    except Exception as e:
        logger.error(f"월별 데이터 수집 작업 실패: {str(e)}")

        # 실패 시 상태 업데이트
        self.update_state(
            state="FAILURE", meta={"error": str(e), "year": year, "month": month}
        )

        # 30분 후 재시도
        raise self.retry(countdown=1800, max_retries=3)


# 자동 스케줄링 태스크


@celery_app.task
def collect_current_month_data():
    """
    이번 달 데이터 수집 (메인 화면용)
    매일 새벽 3시에 실행
    """
    today = date.today()
    return collect_monthly_cheapest_data.delay(
        year=today.year, month=today.month, origin="ICN"
    )


@celery_app.task
def collect_next_month_data():
    """
    다음 달 데이터 수집 (미리 준비)
    매주 일요일 새벽 4시에 실행
    """
    today = date.today()
    next_month = today.month + 1 if today.month < 12 else 1
    next_year = today.year if today.month < 12 else today.year + 1

    return collect_monthly_cheapest_data.delay(
        year=next_year, month=next_month, origin="ICN"
    )


@celery_app.task
def collect_popular_months_data():
    """
    인기 여행 월 데이터 미리 수집
    매월 1일 새벽 2시에 실행
    """
    today = date.today()
    current_year = today.year

    # 인기 여행 월 (봄, 가을)
    popular_months = [3, 4, 5, 10, 11]

    tasks = []
    for month in popular_months:
        # 현재 월 이후의 인기 월만 수집
        if month >= today.month:
            task = collect_monthly_cheapest_data.delay(
                year=current_year, month=month, origin="ICN"
            )
            tasks.append(task.id)
        elif month < today.month:
            # 내년 동일 월
            task = collect_monthly_cheapest_data.delay(
                year=current_year + 1, month=month, origin="ICN"
            )
            tasks.append(task.id)

    logger.info(f"인기 월 데이터 수집 시작: {len(tasks)}개 작업")
    return tasks


# 캐시 관리 태스크


@celery_app.task
def cleanup_expired_cache():
    """
    만료된 캐시 데이터 정리
    매일 새벽 1시에 실행
    """
    try:
        logger.info("만료된 캐시 정리 작업 시작")

        # 서비스를 통한 캐시 정리
        result = collection_service.cleanup_expired_cache()

        if result["success"]:
            logger.info(f"캐시 정리 작업 완료: {result['cleaned_count']}개 정리")
            return result["message"]
        else:
            logger.error(f"캐시 정리 작업 실패: {result['message']}")
            return result["message"]

    except Exception as e:
        logger.error(f"캐시 정리 작업 예외 발생: {str(e)}")
        return f"Cache cleanup failed: {str(e)}"


@celery_app.task
def update_cache_statistics():
    """
    캐시 사용 통계 업데이트
    매시간 실행
    """
    try:
        logger.info("캐시 통계 업데이트 작업 시작")

        # 서비스를 통한 통계 조회
        stats = collection_service.get_collection_statistics()

        if stats["success"]:
            # 통계 정보를 캐시에 저장
            cache_service.set_cache("cache_statistics", stats, 3600)  # 1시간 캐시
            logger.info(f"캐시 통계 업데이트 완료: {stats['total_cached_months']}개 항목")
        else:
            logger.error(f"캐시 통계 조회 실패: {stats.get('error', 'Unknown error')}")

        return stats

    except Exception as e:
        logger.error(f"캐시 통계 업데이트 작업 예외 발생: {str(e)}")
        return {"error": str(e)}


# 수동 실행 태스크


@celery_app.task
def force_collect_month_data(year: int, month: int, origin: str = "ICN"):
    """
    특정 월 데이터 강제 수집 (관리자용)
    """
    try:
        logger.info(f"강제 데이터 수집 작업 시작: {year}년 {month}월")

        # 서비스를 통한 강제 갱신
        result = collection_service.force_refresh_month_data(year, month, origin)

        if result["success"]:
            logger.info(f"강제 데이터 수집 완료: {year}년 {month}월")
        else:
            logger.error(f"강제 데이터 수집 실패: {result['message']}")

        return result

    except Exception as e:
        logger.error(f"강제 데이터 수집 작업 예외 발생: {str(e)}")
        return {"success": False, "message": f"강제 수집 작업 실패: {str(e)}", "error": str(e)}


@celery_app.task
def collect_multi_origin_data(year: int, month: int, origins: List[str] = None):
    """
    여러 출발지에 대한 데이터 수집
    """
    try:
        if origins is None:
            origins = ["ICN"]  # 현재는 ICN만 지원

        logger.info(f"다중 출발지 데이터 수집 작업 시작: {len(origins)}개 출발지")

        tasks = []
        for origin in origins:
            task = collect_monthly_cheapest_data.delay(year, month, origin)
            tasks.append(task.id)

        logger.info(f"다중 출발지 수집 작업 생성 완료: {len(tasks)}개 작업")
        return {
            "success": True,
            "message": f"{len(tasks)}개 수집 작업 생성 완료",
            "task_ids": tasks,
            "origins": origins,
        }

    except Exception as e:
        logger.error(f"다중 출발지 수집 작업 예외 발생: {str(e)}")
        return {
            "success": False,
            "message": f"다중 출발지 수집 작업 실패: {str(e)}",
            "error": str(e),
            "task_ids": [],
        }


# Celery Beat 스케줄 설정

celery_app.conf.beat_schedule = {
    # 매일 새벽 3시 - 이번 달 데이터 수집
    "collect-current-month": {
        "task": "app.tasks.monthly_data_collection.collect_current_month_data",
        "schedule": crontab(hour=3, minute=0),
    },
    # 매주 일요일 새벽 4시 - 다음 달 데이터 수집
    "collect-next-month": {
        "task": "app.tasks.monthly_data_collection.collect_next_month_data",
        "schedule": crontab(hour=4, minute=0, day_of_week=0),
    },
    # 매월 1일 새벽 2시 - 인기 월 데이터 수집
    "collect-popular-months": {
        "task": "app.tasks.monthly_data_collection.collect_popular_months_data",
        "schedule": crontab(hour=2, minute=0, day_of_month=1),
    },
    # 매일 새벽 1시 - 만료된 캐시 정리
    "cleanup-expired-cache": {
        "task": "app.tasks.monthly_data_collection.cleanup_expired_cache",
        "schedule": crontab(hour=1, minute=0),
    },
    # 매시간 - 캐시 통계 업데이트
    "update-cache-stats": {
        "task": "app.tasks.monthly_data_collection.update_cache_statistics",
        "schedule": crontab(minute=0),
    },
}

celery_app.conf.timezone = "Asia/Seoul"


# 헬퍼 함수


def get_cached_monthly_data(
    year: int, month: int, origin: str = "ICN"
) -> Dict[str, Any]:
    """
    캐시된 월별 데이터 조회

    Returns:
        캐시된 데이터 또는 None
    """
    return collection_service.get_cached_monthly_data(year, month, origin)


def is_month_data_available(year: int, month: int, origin: str = "ICN") -> bool:
    """
    해당 월 데이터가 캐시에 있는지 확인
    """
    return collection_service.is_month_data_available(year, month, origin)


def trigger_month_collection_if_needed(
    year: int, month: int, origin: str = "ICN"
) -> str:
    """
    필요시 월별 데이터 수집 트리거

    Returns:
        작업 ID 또는 "already_exists"
    """
    if not is_month_data_available(year, month, origin):
        task = collect_monthly_cheapest_data.delay(year, month, origin)
        return task.id

    return "already_exists"
