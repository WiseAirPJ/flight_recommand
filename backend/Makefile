# Run from backend/. All commands use the committed uv environment.
UV ?= uv
RUN = $(UV) run --locked
SOURCES = app tests conftest.py alembic
CORE_COVERAGE = app/main.py,app/api/v1/flights.py,app/api/v1/regions.py,app/config/settings.py,app/core/database.py,app/models/flight_requests.py,app/services/amadeus_service.py,app/services/exchange_rate_service.py,app/services/monthly_price_analyzer.py,app/services/monthly_search_service.py,app/services/provider_http.py,app/services/provider_source.py,app/services/price_history_service.py,app/tasks/monthly_data_collection.py,app/utils/cache_keys.py,app/utils/decorators.py,app/utils/response_enhancers.py

.PHONY: help install install-dev setup-dev dev worker beat migrate format lint test test-cov coverage-check check ci lock export-requirements pre-commit install-pre-commit typecheck security

help: ## 사용 가능한 명령
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "%-22s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## 운영 의존성만 설치
	$(UV) sync --locked --no-dev

install-dev: ## 잠금 파일 기준 개발 환경 설치
	$(UV) sync --locked

setup-dev: install-dev ## 개발 환경과 없는 경우에만 .env 준비
	@test -f .env || cp ../.env.example .env

dev: ## 개발 서버 실행
	$(RUN) uvicorn app.main:app --reload --port 8000

worker: ## 월별 수집 및 관리 큐 처리
	$(RUN) celery -A app.tasks.celery_app:celery_app worker -l info -Q monthly_analysis,daily_updates

beat: ## 수집 예약 실행
	$(RUN) celery -A app.tasks.celery_app:celery_app beat -l info

migrate: ## DB 마이그레이션 적용
	$(RUN) alembic upgrade head

format: ## 코드 형식 수정
	$(RUN) isort $(SOURCES)
	$(RUN) black $(SOURCES)

lint: ## CI와 동일한 형식 및 치명적 오류 검사
	$(RUN) black --check $(SOURCES)
	$(RUN) isort --check-only $(SOURCES)
	$(RUN) flake8 $(SOURCES) --select E9,F63,F7,F82 --show-source

test: ## 전체 테스트
	$(RUN) pytest

test-cov: ## 전체 테스트 및 커버리지 보고서
	$(RUN) pytest --cov=app --cov-report=term-missing --cov-report=xml

coverage-check: test-cov ## 핵심 경로 커버리지 80% 검사
	$(RUN) coverage report --include='$(CORE_COVERAGE)' --fail-under=80

check: ## 잠금 일치, 형식 검사, 전체 테스트, 커버리지 기준 검사
	$(UV) lock --check
	$(MAKE) lint
	$(MAKE) coverage-check

ci: check ## 로컬에서 CI 검사 실행

lock: ## 선언한 의존성 변경을 잠금 파일에 반영
	$(UV) lock

export-requirements: ## pip 전용 도구에 전달할 운영 의존성 내보내기
	@mkdir -p dist
	$(UV) export --locked --no-dev --no-emit-project --format requirements-txt --output-file dist/requirements.txt

pre-commit: ## 설정된 모든 커밋 전 검사 실행
	$(RUN) pre-commit run --all-files

install-pre-commit: ## 선택적으로 Git 훅 설치
	$(RUN) pre-commit install

typecheck: ## 선택적 기존 코드 타입 검사
	$(RUN) mypy app

security: ## 선택적 보안 코드 검사, 실패를 숨기지 않음
	$(RUN) bandit -r app
