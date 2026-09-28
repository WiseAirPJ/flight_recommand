# 🔧 개발자 가이드

이 문서는 프로젝트의 개발 환경 설정과 개발 워크플로우에 대한 자세한 정보를 제공합니다.

## 📋 목차

- [🏁 빠른 개발 환경 설정](#-빠른-개발-환경-설정)
- [🏗️ 프로젝트 구조](#️-프로젝트-구조)
- [⚙️ 개발 도구 설정](#️-개발-도구-설정)
- [🧪 테스트 가이드](#-테스트-가이드)
- [🔄 개발 워크플로우](#-개발-워크플로우)
- [🐛 디버깅](#-디버깅)
- [📝 코딩 컨벤션](#-코딩-컨벤션)

## 🏁 빠른 개발 환경 설정

### 1. 필수 도구 설치

```bash
# Python 3.12+ 설치 확인
python --version

# Redis 설치 (macOS)
brew install redis

# Redis 설치 (Ubuntu)
sudo apt-get install redis-server

# Redis 서비스 시작
brew services start redis  # macOS
sudo systemctl start redis-server  # Ubuntu
```

### 2. 개발 환경 구성

```bash
# 저장소 클론
git clone https://github.com/your-username/flight_recommand.git
cd flight_recommand/backend

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 또는 venv\Scripts\activate  # Windows

# 개발 의존성 설치
pip install -r requirements-dev.txt
```

### 3. 환경변수 설정

```bash
# .env 파일 생성
cp .env .env

# .env 파일 예시
cat > .env << 'EOF'
# 기본 설정
DEBUG=True
ENVIRONMENT=development

# Amadeus API (필수)
AMADEUS_CLIENT_ID=your_amadeus_client_id
AMADEUS_CLIENT_SECRET=your_amadeus_client_secret

# LLM API (Phase 2)
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# 환율 API (Phase 2)
KOREAEXIM_API_KEY=your_koreaexim_api_key

# Redis (선택사항, 기본값 사용 가능)
REDIS_HOST=localhost
REDIS_PORT=6379
EOF
```

### 4. 개발 서버 시작

```bash
# FastAPI 개발 서버 시작 (자동 리로드)
uvicorn app.main:app --reload --port 8000

# Celery Worker 시작 (별도 터미널)
celery -A app.tasks.celery_app worker --loglevel=info

# Celery Beat 시작 (별도 터미널, 선택사항)
celery -A app.tasks.celery_app beat --loglevel=info
```

## 🏗️ 프로젝트 구조

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 앱 진입점
│   ├── api/                    # API 라우터
│   │   └── v1/
│   │       ├── flights.py      # 항공편 API
│   │       ├── regions.py      # 지역 API
│   │       ├── llm.py          # LLM 분석 API
│   │       ├── cache.py        # 캐시 API
│   │       └── utils.py        # 유틸리티 API
│   ├── config/
│   │   └── settings.py         # 설정 관리
│   ├── models/                 # Pydantic 모델
│   │   ├── flight.py           # 항공편 모델
│   │   ├── region.py           # 지역 모델
│   │   └── response.py         # 응답 모델
│   ├── services/               # 비즈니스 로직
│   │   ├── amadeus_service.py  # Amadeus API 연동
│   │   ├── cache_service.py    # 캐시 관리
│   │   ├── region_service.py   # 지역 데이터 관리
│   │   ├── llm/                # LLM 서비스
│   │   │   └── llm_service.py  # AI 분석 서비스
│   │   ├── exchange_rate_service.py  # 환율 변환 서비스
│   │   └── monthly_price_analyzer.py # 월별 가격 분석
│   ├── tasks/                  # Celery 태스크
│   │   ├── celery_app.py       # Celery 설정
│   │   └── monthly_data_collection.py
│   └── utils/                  # 유틸리티
│       ├── validators.py       # 데이터 검증
│       ├── decorators.py       # 데코레이터
│       └── cache_keys.py       # 캐시 키 관리
├── tests/                      # 테스트 코드
├── logs/                       # 로그 파일
├── requirements.txt            # 운영 의존성
├── requirements-dev.txt        # 개발 의존성
└── conftest.py                 # pytest 설정
```

### 주요 파일 설명

- **`app/main.py`**: FastAPI 애플리케이션의 진입점
- **`app/config/settings.py`**: 환경변수와 설정 관리
- **`app/services/`**: 외부 API 연동 및 비즈니스 로직
  - **`llm/`**: LLM 서비스 (OpenAI, Anthropic 지원)
  - **`exchange_rate_service.py`**: 환율 변환 서비스 (한국수출입은행)
  - **`monthly_price_analyzer.py`**: 월별 가격 분석 및 데이터 수집
- **`app/utils/decorators.py`**: 캐싱, 예외처리 등의 데코레이터
- **`tests/`**: 단위 테스트 및 통합 테스트

## ⚙️ 개발 도구 설정

### VS Code 설정

`.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.linting.flake8Enabled": true,
    "editor.formatOnSave": true,
    "python.sortImports.args": ["--profile", "black"]
}
```

### Pre-commit 훅 설정

```bash
# pre-commit 설치
pip install pre-commit

# 훅 설치
pre-commit install

# 수동 실행
pre-commit run --all-files
```

`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

### Makefile (개발 명령어 단축)

```makefile
.PHONY: install dev test lint format clean

install:
	pip install -r requirements-dev.txt

dev:
	uvicorn app.main:app --reload --port 8000

worker:
	celery -A app.tasks.celery_app worker --loglevel=info

beat:
	celery -A app.tasks.celery_app beat --loglevel=info

test:
	pytest -v

test-cov:
	pytest --cov=app --cov-report=html

lint:
	flake8 app/ tests/
	pylint app/
	mypy app/

format:
	black app/ tests/
	isort app/ tests/

clean:
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
```

## 🧪 테스트 가이드

### 테스트 유형

1. **단위 테스트**: 개별 함수/클래스 테스트
2. **통합 테스트**: API 엔드포인트 테스트
3. **E2E 테스트**: 전체 워크플로우 테스트

### 테스트 실행

```bash
# 전체 테스트
pytest

# 특정 파일 테스트
pytest tests/test_flights_api.py

# 특정 테스트 메서드
pytest tests/test_flights_api.py::TestFlightsAPI::test_search_flights_success

# 마크된 테스트만 실행
pytest -m "slow"

# 커버리지 포함
pytest --cov=app --cov-report=html

# 병렬 실행
pytest -n auto
```

### 테스트 작성 가이드

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.main import app

client = TestClient(app)

class TestFlightsAPI:
    """항공편 API 테스트 클래스"""

    @pytest.fixture
    def mock_amadeus_service(self):
        """Mock Amadeus 서비스"""
        with patch('app.api.v1.flights.get_amadeus_service') as mock:
            service = Mock()
            service.search_flight_offers.return_value = {
                "success": True,
                "data": [{"id": "1", "price": {"total": "300000"}}]
            }
            mock.return_value = service
            yield service

    def test_search_flights_success(self, mock_amadeus_service):
        """항공편 검색 성공 테스트"""
        request_data = {
            "origin": "ICN",
            "destination": "NRT",
            "departure_date": "2025-08-15",
            "adults": 1
        }

        response = client.post("/api/v1/flights/search", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) > 0
```

### Mock 사용 예시

```python
# 외부 API Mock
@patch('app.services.amadeus_service.Client')
def test_amadeus_api_call(mock_client):
    mock_client.return_value.shopping.flight_offers_search.get.return_value.data = []

    service = AmadeusService()
    result = service.search_flight_offers(...)

    assert result["success"] is True

# Async 함수 Mock
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_async_function():
    mock_service = Mock()
    mock_service.async_method = AsyncMock(return_value={"result": "success"})

    result = await mock_service.async_method()
    assert result["result"] == "success"
```

## 🔄 개발 워크플로우

### 1. 기능 개발 프로세스

```bash
# 1. 새 기능 브랜치 생성
git checkout -b feature/new-awesome-feature

# 2. 개발 진행
# - 코드 작성
# - 테스트 작성
# - 문서 업데이트

# 3. 테스트 실행
pytest
make lint

# 4. 커밋
git add .
git commit -m "feat: add awesome new feature"

# 5. 푸시 및 PR 생성
git push origin feature/new-awesome-feature
```

### 2. 커밋 메시지 컨벤션

```
feat: 새로운 기능 추가
fix: 버그 수정
docs: 문서 업데이트
style: 코드 포맷팅
refactor: 코드 리팩토링
test: 테스트 추가/수정
chore: 빌드/설정 변경
```

### 3. 코드 리뷰 체크리스트

- [ ] 기능이 요구사항을 만족하는가?
- [ ] 테스트가 충분히 작성되었는가?
- [ ] 에러 처리가 적절한가?
- [ ] 성능상 문제는 없는가?
- [ ] 보안상 문제는 없는가?
- [ ] 문서가 업데이트되었는가?

## 🐛 디버깅

### 로그 설정

```python
import logging

# 개발환경 로그 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 사용 예시
logger.debug("디버그 메시지")
logger.info("정보 메시지")
logger.warning("경고 메시지")
logger.error("에러 메시지")
```

### 디버깅 도구

#### 1. FastAPI 디버그 모드

```python
# settings.py
DEBUG = True

# main.py
app = FastAPI(debug=True)
```

#### 2. 브레이크포인트 사용

```python
# Python 3.7+
breakpoint()

# 이전 버전
import pdb; pdb.set_trace()
```

#### 3. 성능 프로파일링

```python
import cProfile
import pstats

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()

    # 측정할 코드
    result = expensive_function()

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative').print_stats(10)

    return result
```

### 일반적인 문제 해결

#### Redis 연결 오류
```bash
# Redis 서비스 상태 확인
redis-cli ping

# Redis 로그 확인
tail -f /var/log/redis/redis-server.log
```

#### Amadeus API 오류
```python
# API 키 유효성 확인
def test_amadeus_auth():
    try:
        client = Client(
            client_id=settings.AMADEUS_CLIENT_ID,
            client_secret=settings.AMADEUS_CLIENT_SECRET
        )
        response = client.reference_data.locations.get(keyword='LON')
        print("API 연결 성공")
    except Exception as e:
        print(f"API 연결 실패: {e}")
```

## 📝 코딩 컨벤션

### Python 스타일 가이드

- **PEP 8** 준수
- **Black** 포맷터 사용
- **isort**로 import 정렬
- **Type hints** 필수 사용

### 함수/클래스 명명 규칙

```python
# 클래스: PascalCase
class FlightSearchService:
    pass

# 함수/변수: snake_case
def search_flight_offers():
    flight_data = {}
    return flight_data

# 상수: UPPER_CASE
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30
```

### 문서화

```python
def search_flights(
    origin: str,
    destination: str,
    departure_date: str
) -> Dict[str, Any]:
    """
    항공편 검색

    Args:
        origin: 출발지 IATA 코드 (예: "ICN")
        destination: 도착지 IATA 코드 (예: "NRT")
        departure_date: 출발 날짜 (YYYY-MM-DD 형식)

    Returns:
        Dict[str, Any]: 검색 결과
        {
            "success": bool,
            "data": List[Dict],
            "message": str
        }

    Raises:
        ValueError: 잘못된 IATA 코드
        HTTPException: API 호출 실패

    Examples:
        >>> result = search_flights("ICN", "NRT", "2025-08-15")
        >>> print(result["success"])
        True
    """
    pass
```

### 에러 처리

```python
from typing import Union
from fastapi import HTTPException

def safe_api_call() -> Union[Dict[str, Any], None]:
    """안전한 API 호출 패턴"""
    try:
        result = external_api_call()
        return result
    except requests.exceptions.Timeout:
        logger.warning("API 호출 타임아웃")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"API 호출 실패: {e}")
        raise HTTPException(
            status_code=503,
            detail="외부 서비스 일시 장애"
        )
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail="서버 내부 오류"
        )
```

---
