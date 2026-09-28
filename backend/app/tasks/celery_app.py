import logging

from celery import Celery
from celery.schedules import crontab

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Celery 인스턴스 생성
celery_app = Celery(
    "flight_analyzer",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.monthly_data_collection",  # 월별 데이터 수집 태스크
        # 'app.tasks.daily_data_collection',   # 향후 추가할 태스크들
        # 'app.tasks.notification_tasks',
    ],
)

# Celery 설정
celery_app.conf.update(
    # 타임존 설정
    timezone="Asia/Seoul",
    enable_utc=True,
    # 작업 설정
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    result_expires=3600,  # 결과 1시간 후 만료
    # 워커 설정
    worker_prefetch_multiplier=1,  # 한 번에 하나씩 처리
    task_acks_late=True,  # 작업 완료 후 ACK
    worker_max_tasks_per_child=1000,  # 워커 재시작 주기
    # 큐 설정
    task_routes={
        "app.tasks.monthly_data_collection.*": {"queue": "monthly_analysis"},
        "app.tasks.daily_data_collection.*": {"queue": "daily_updates"},
    },
    # 재시도 설정
    task_default_retry_delay=60,  # 기본 재시도 간격 60초
    task_max_retries=3,  # 최대 재시도 3회
)

# 스케줄 작업 설정 (Celery Beat)
celery_app.conf.beat_schedule = {
    # 매일 새벽 3시 - 이번 달 데이터 수집
    "collect-current-month-data": {
        "task": "app.tasks.monthly_data_collection.collect_current_month_data",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "monthly_analysis"},
    },
    # 매주 일요일 새벽 4시 - 다음 달 데이터 수집
    "collect-next-month-data": {
        "task": "app.tasks.monthly_data_collection.collect_next_month_data",
        "schedule": crontab(hour=4, minute=0, day_of_week=0),
        "options": {"queue": "monthly_analysis"},
    },
    # 매월 1일 새벽 2시 - 인기 월 데이터 수집
    "collect-popular-months-data": {
        "task": "app.tasks.monthly_data_collection.collect_popular_months_data",
        "schedule": crontab(hour=2, minute=0, day_of_month=1),
        "options": {"queue": "monthly_analysis"},
    },
    # 매일 새벽 1시 - 만료된 캐시 정리
    "cleanup-expired-cache": {
        "task": "app.tasks.monthly_data_collection.cleanup_expired_cache",
        "schedule": crontab(hour=1, minute=0),
        "options": {"queue": "daily_updates"},
    },
    # 매시간 - 캐시 통계 업데이트
    "update-cache-statistics": {
        "task": "app.tasks.monthly_data_collection.update_cache_statistics",
        "schedule": crontab(minute=0),
        "options": {"queue": "daily_updates"},
    },
}


# 개발/테스트용 즉시 실행 스케줄 (주석 해제하여 사용)
# celery_app.conf.beat_schedule.update({
#     # 5분마다 테스트용 데이터 수집
#     'test-collect-current-month': {
#         'task': 'app.tasks.monthly_data_collection.collect_current_month_data',
#         'schedule': crontab(minute='*/5'),  # 5분마다
#         'options': {'queue': 'monthly_analysis'}
#     },
# })


# Celery 워커 시작 시 실행할 설정
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Celery 시작 시 추가 설정"""
    logger.info("Celery 스케줄러가 시작되었습니다.")
    logger.info("등록된 스케줄 작업:")
    for name, task in celery_app.conf.beat_schedule.items():
        logger.info(f"  - {name}: {task['task']}")


# 작업 실행 전 로깅
@celery_app.task(bind=True)
def debug_task(self):
    """디버그용 태스크"""
    logger.debug(f"Request: {self.request!r}")
    return "Debug task completed"


if __name__ == "__main__":
    celery_app.start()
