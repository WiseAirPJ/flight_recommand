# Makefile for Flight Analyzer Backend
# 개발 및 배포 작업을 자동화하는 명령어들

.PHONY: help install install-dev clean format lint test test-cov test-fast
.PHONY: dev worker beat monitor docker-build docker-run pre-commit security
.PHONY: docs check typecheck update-deps release

# 기본 Python 인터프리터
PYTHON := python
PIP := pip
PYTEST := pytest

# 색상 정의
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
PURPLE := \033[0;35m
CYAN := \033[0;36m
WHITE := \033[0;37m
RESET := \033[0m

# 기본 타겟
help: ## 📋 사용 가능한 명령어 목록 표시
	@echo "$(CYAN)Flight Analyzer Backend - 사용 가능한 명령어:$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "$(BLUE)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)사용 예시:$(RESET)"
	@echo "  make install-dev  # 개발 환경 설치"
	@echo "  make dev          # 개발 서버 시작"
	@echo "  make test         # 테스트 실행"
	@echo "  make lint         # 코드 품질 검사"

# 설치 관련
install: ## 📦 운영 의존성 설치
	@echo "$(GREEN)📦 운영 의존성 설치 중...$(RESET)"
	$(PIP) install -r requirements.txt

install-dev: ## 🔧 개발 의존성 설치
	@echo "$(GREEN)🔧 개발 의존성 설치 중...$(RESET)"
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e .
	@echo "$(GREEN)✅ 개발 환경 설치 완료!$(RESET)"

install-pre-commit: ## 🪝 Pre-commit 훅 설치
	@echo "$(GREEN)🪝 Pre-commit 훅 설치 중...$(RESET)"
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "$(GREEN)✅ Pre-commit 훅 설치 완료!$(RESET)"

# 개발 서버
dev: ## 🚀 개발 서버 시작 (자동 리로드)
	@echo "$(GREEN)🚀 개발 서버 시작 중...$(RESET)"
	uvicorn app.main:app --reload --port 8000 --log-level debug

dev-prod: ## 🏭 운영 모드로 개발 서버 시작
	@echo "$(GREEN)🏭 운영 모드 개발 서버 시작 중...$(RESET)"
	uvicorn app.main:app --port 8000 --workers 4

# Celery 관련
worker: ## 👷 Celery Worker 시작
	@echo "$(GREEN)👷 Celery Worker 시작 중...$(RESET)"
	celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4

beat: ## ⏰ Celery Beat 스케줄러 시작
	@echo "$(GREEN)⏰ Celery Beat 시작 중...$(RESET)"
	celery -A app.tasks.celery_app beat --loglevel=info

monitor: ## 📊 Celery Flower 모니터링 시작
	@echo "$(GREEN)📊 Celery Flower 모니터링 시작 중...$(RESET)"
	celery -A app.tasks.celery_app flower --port=5555

# 코드 품질
format: ## 🎨 코드 포맷팅 (Black + isort)
	@echo "$(GREEN)🎨 코드 포맷팅 중...$(RESET)"
	black app/ tests/ --line-length 88
	isort app/ tests/ --profile black
	@echo "$(GREEN)✅ 코드 포맷팅 완료!$(RESET)"

lint: ## 🔍 코드 품질 검사 (Flake8 + MyPy + Pylint)
	@echo "$(GREEN)🔍 코드 품질 검사 중...$(RESET)"
	@echo "$(BLUE)1/4 Flake8 검사...$(RESET)"
	flake8 app/ tests/ --max-line-length=88 --extend-ignore=E203,W503
	@echo "$(BLUE)2/4 MyPy 타입 검사...$(RESET)"
	mypy app/ --ignore-missing-imports
	@echo "$(BLUE)3/4 Pylint 검사...$(RESET)"
	pylint app/ --disable=C0114,C0115,C0116,R0903
	@echo "$(BLUE)4/4 Pydocstyle 검사...$(RESET)"
	pydocstyle app/ --convention=google --add-ignore=D100,D101,D102,D103,D104,D105
	@echo "$(GREEN)✅ 코드 품질 검사 완료!$(RESET)"

typecheck: ## 🏷️ 타입 검사만 실행
	@echo "$(GREEN)🏷️ 타입 검사 중...$(RESET)"
	mypy app/ --ignore-missing-imports
	@echo "$(GREEN)✅ 타입 검사 완료!$(RESET)"

security: ## 🛡️ 보안 검사 (Bandit + 비밀정보 검사)
	@echo "$(GREEN)🛡️ 보안 검사 중...$(RESET)"
	@echo "$(BLUE)1/2 Bandit 보안 검사...$(RESET)"
	bandit -r app/ -f json -o bandit-report.json || true
	@echo "$(BLUE)2/2 비밀정보 검사...$(RESET)"
	detect-secrets scan --baseline .secrets.baseline
	@echo "$(GREEN)✅ 보안 검사 완료!$(RESET)"

# 테스트
test: ## 🧪 전체 테스트 실행
	@echo "$(GREEN)🧪 전체 테스트 실행 중...$(RESET)"
	$(PYTEST) -v --tb=short

test-cov: ## 📊 커버리지 포함 테스트 실행
	@echo "$(GREEN)📊 커버리지 테스트 실행 중...$(RESET)"
	$(PYTEST) --cov=app --cov-report=html --cov-report=term-missing --cov-report=xml
	@echo "$(GREEN)✅ 커버리지 리포트: htmlcov/index.html$(RESET)"

test-fast: ## ⚡ 빠른 테스트 (병렬 실행)
	@echo "$(GREEN)⚡ 빠른 테스트 실행 중...$(RESET)"
	$(PYTEST) -n auto --tb=short

test-unit: ## 🔬 단위 테스트만 실행
	@echo "$(GREEN)🔬 단위 테스트 실행 중...$(RESET)"
	$(PYTEST) -m "unit" -v

test-integration: ## 🔗 통합 테스트만 실행
	@echo "$(GREEN)🔗 통합 테스트 실행 중...$(RESET)"
	$(PYTEST) -m "integration" -v

test-api: ## 📡 API 테스트만 실행
	@echo "$(GREEN)📡 API 테스트 실행 중...$(RESET)"
	$(PYTEST) -m "api" -v

test-smoke: ## 💨 스모크 테스트 실행
	@echo "$(GREEN)💨 스모크 테스트 실행 중...$(RESET)"
	$(PYTEST) -m "smoke" -v

# Pre-commit 관련
pre-commit: ## 🪝 Pre-commit 훅 수동 실행
	@echo "$(GREEN)🪝 Pre-commit 훅 실행 중...$(RESET)"
	pre-commit run --all-files

pre-commit-update: ## 🔄 Pre-commit 훅 업데이트
	@echo "$(GREEN)🔄 Pre-commit 훅 업데이트 중...$(RESET)"
	pre-commit autoupdate

# 정리
clean: ## 🧹 임시 파일 및 캐시 정리
	@echo "$(GREEN)🧹 정리 중...$(RESET)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.orig" -delete
	find . -type f -name ".coverage" -delete
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf bandit-report.json
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	@echo "$(GREEN)✅ 정리 완료!$(RESET)"

clean-all: clean ## 🧹 모든 파일 정리 (venv 포함)
	@echo "$(YELLOW)⚠️  가상환경도 삭제하시겠습니까? [y/N]$(RESET)"
	@read -p "" confirm && [ "$$confirm" = "y" ] && rm -rf venv/ .venv/ || true

# 검사 종합
check: format lint typecheck security test ## ✅ 전체 코드 품질 검사 (포맷팅 + 린팅 + 타입체크 + 보안 + 테스트)
	@echo "$(GREEN)✅ 모든 검사 완료!$(RESET)"

quick-check: format lint test-fast ## ⚡ 빠른 검사 (포맷팅 + 린팅 + 빠른 테스트)
	@echo "$(GREEN)⚡ 빠른 검사 완료!$(RESET)"

# Docker 관련
docker-build: ## 🐳 Docker 이미지 빌드
	@echo "$(GREEN)🐳 Docker 이미지 빌드 중...$(RESET)"
	docker build -t flight-analyzer:latest .

docker-run: ## 🐳 Docker 컨테이너 실행
	@echo "$(GREEN)🐳 Docker 컨테이너 실행 중...$(RESET)"
	docker run -p 8000:8000 --env-file .env flight-analyzer:latest

docker-compose-up: ## 🐳 Docker Compose로 전체 스택 시작
	@echo "$(GREEN)🐳 Docker Compose 스택 시작 중...$(RESET)"
	docker-compose up -d

docker-compose-down: ## 🐳 Docker Compose 스택 종료
	@echo "$(GREEN)🐳 Docker Compose 스택 종료 중...$(RESET)"
	docker-compose down

# 문서화
docs: ## 📚 API 문서 생성
	@echo "$(GREEN)📚 API 문서 생성 중...$(RESET)"
	@echo "$(BLUE)API 문서: http://localhost:8000/docs$(RESET)"
	@echo "$(BLUE)ReDoc: http://localhost:8000/redoc$(RESET)"

# 의존성 관리
update-deps: ## 📋 의존성 업데이트
	@echo "$(GREEN)📋 의존성 업데이트 중...$(RESET)"
	$(PIP) list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 $(PIP) install -U
	$(PIP) freeze > requirements.txt

freeze: ## 🧊 현재 의존성 고정
	@echo "$(GREEN)🧊 의존성 고정 중...$(RESET)"
	$(PIP) freeze > requirements.txt
	@echo "$(GREEN)✅ requirements.txt 업데이트 완료!$(RESET)"

# 배포 관련
release: ## 🚀 릴리스 준비 (태그 생성)
	@echo "$(GREEN)🚀 릴리스 준비 중...$(RESET)"
	@echo "$(YELLOW)현재 버전을 확인하세요:$(RESET)"
	@grep version pyproject.toml
	@echo "$(YELLOW)새 버전을 입력하세요:$(RESET)"
	@read -p "Version (e.g., 0.3.0): " version && \
	cz bump --increment $$version && \
	git push && git push --tags

# 개발 환경 초기 설정
setup-dev: install-dev install-pre-commit ## 🛠️ 개발 환경 완전 설정
	@echo "$(GREEN)🛠️ 개발 환경 설정 중...$(RESET)"
	@echo "$(BLUE)SECRET_KEY 생성...$(RESET)"
	$(PYTHON) generate_secret_key.py
	@if [ ! -f .env ]; then \
		echo "$(BLUE).env 파일 생성...$(RESET)"; \
		cp .env.example .env; \
		echo "$(YELLOW)⚠️  .env 파일을 편집하여 실제 값으로 수정하세요!$(RESET)"; \
	fi
	@echo "$(GREEN)✅ 개발 환경 설정 완료!$(RESET)"
	@echo ""
	@echo "$(CYAN)다음 단계:$(RESET)"
	@echo "1. .env 파일 편집 (Amadeus API 키 등)"
	@echo "2. Redis 서버 시작: brew services start redis"
	@echo "3. 개발 서버 시작: make dev"

# 상태 확인
status: ## 📊 프로젝트 상태 확인
	@echo "$(CYAN)📊 프로젝트 상태:$(RESET)"
	@echo ""
	@echo "$(BLUE)Python 버전:$(RESET)"
	@$(PYTHON) --version
	@echo ""
	@echo "$(BLUE)가상환경:$(RESET)"
	@which python
	@echo ""
	@echo "$(BLUE)설치된 패키지:$(RESET)"
	@$(PIP) list | head -10
	@echo "... (총 $(shell $(PIP) list | wc -l) 개 패키지)"
	@echo ""
	@echo "$(BLUE)Git 상태:$(RESET)"
	@git status --porcelain | wc -l | awk '{print $$1 " 개의 변경된 파일"}'
	@echo ""
	@echo "$(BLUE)테스트 상태:$(RESET)"
	@$(PYTEST) --collect-only -q 2>/dev/null | tail -1 || echo "테스트 실행 불가"

# 로그 확인
logs: ## 📜 애플리케이션 로그 확인
	@echo "$(GREEN)📜 로그 확인 중...$(RESET)"
	@if [ -f logs/app.log ]; then \
		tail -f logs/app.log; \
	else \
		echo "$(YELLOW)로그 파일이 없습니다. 서버를 먼저 시작하세요.$(RESET)"; \
	fi

# 성능 테스트
benchmark: ## ⚡ API 성능 테스트
	@echo "$(GREEN)⚡ API 성능 테스트 중...$(RESET)"
	@echo "$(BLUE)서버가 실행 중인지 확인 중...$(RESET)"
	@curl -s http://localhost:8000/health > /dev/null && \
		echo "$(GREEN)✅ 서버 실행 중$(RESET)" || \
		(echo "$(RED)❌ 서버가 실행되지 않음. 'make dev'로 서버를 시작하세요.$(RESET)" && exit 1)
	@echo "$(BLUE)성능 테스트 실행...$(RESET)"
	@$(PYTHON) test_api_endpoints.py

# CI 에뮬레이션
ci: clean check ## 🔄 CI 환경 에뮬레이션 (정리 + 전체 검사)
	@echo "$(GREEN)🔄 CI 환경 에뮬레이션 완료!$(RESET)"

# 빠른 CI 체크
ci-quick: clean quick-check ## ⚡ 빠른 CI 체크
	@echo "$(GREEN)⚡ 빠른 CI 체크 완료!$(RESET)"
