# 일본 항공권 지도

출발공항과 여행 월을 선택하면 조회한 날짜 중 일본 지역별 최저 왕복 운임을 보여주는 서비스입니다. 이 저장소의 현재 구현 범위는 **백엔드 API**입니다. 지도 화면과 예약 연결은 후속 구현 대상입니다.

## 실행

Python 3.12를 사용합니다. 저장소 루트에서:

```sh
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp ../.env.example .env
uvicorn app.main:app --reload
```

문서는 `http://localhost:8000/docs`, 상태 확인은 `/health`입니다. 기본값은 외부 항공권 API를 호출하지 않으며, 가격 검색은 공급자 미설정으로 503을 반환합니다. 로컬 예시 화면 개발에는 `.env`에서 `ENABLE_DUMMY_FALLBACK=true`를 설정하세요. 예시 응답은 `is_demo=true`이고 가격 이력에는 저장되지 않습니다.

실제 공급자 연결에는 `USE_REAL_AMADEUS=true`와 Amadeus 자격 증명이 필요합니다. `AMADEUS_HOSTNAME=test`의 데이터도 실제 운임 이력에서 제외됩니다. 운영 공급자 관측값 저장은 `AMADEUS_HOSTNAME=production`에서만 이루어집니다. KRW 표시에는 한국수출입은행 환율 키도 필요합니다. 환율을 얻지 못하면 외화를 원화로 바꿔 표시하지 않고 조회 실패를 반환합니다. 원화는 JPY 운임을 환산한 **참고 가격**이며 원본 운임과 환율 기준일도 보존합니다.

## 화면에서 사용할 API

| 용도 | API |
| --- | --- |
| 국내 출발공항 선택 | `GET /api/v1/regions/departure-airports` |
| 일본 지역·지도 좌표 | `GET /api/v1/regions/` |
| 선택한 월의 지도 가격 | `GET /api/v1/regions/lowest-prices?origin=PUS&year=2027&month=1&adults=1&duration_days=4&currency=KRW` |
| 지역별 상위 날짜 후보 | `GET /api/v1/regions/monthly-analysis/2027/1?origin=PUS` |
| 상세 왕복·편도 검색 | `POST /api/v1/flights/search` |
| 편도 전용 검색 | `POST /api/v1/flights/search-oneway` |
| 3박 4일 등 기간 검색 | `POST /api/v1/flights/search-by-duration` |
| 기준일 전후 최저가 | `POST /api/v1/flights/cheapest-dates` |

예시 날짜는 현재 이후로 바꿔 사용하세요. `POST /api/v1/regions/monthly-analysis`는 `year`, `month`, `origin`, `adults`, `duration_days`, `currency`, `non_stop`을 받습니다. 새 계약은 `duration_days`를 사용하며 기존 GET 월별 API의 `duration`은 호환 별칭으로 유지합니다. 두 값이 다르면 422를 반환합니다.

가격은 **입력한 성인 전체의 왕복 합계**입니다. `duration_days=4`는 출발일부터 귀국일까지 4일(3박)입니다. 수하물 추가요금을 임의로 더하지 않으며 제공된 항공사 운임 조건을 확인해야 합니다.

기본 월별 검색은 3일 간격으로 출발일을 조회하고 CTS/NRT/HND/KIX/NGO/FUK/OKA를 비교합니다. 모든 일본 공항·날짜·항공사를 포괄하는 최저가가 아닙니다. 화면에는 “조회한 날짜 중 최저가”로 표시하고, `meta.sampled_dates`, `searched_airports`, `source`, `partial`, `failed_searches`, 가격의 `observed_at`을 사용하세요. 결과가 없는 지역은 가격 없음으로 표시합니다. 나리타보다 하네다가 저렴하면 하네다 결과를 표시합니다. 출발공항 목록은 운항 노선을 보장하지 않습니다.

## 구조와 실행 흐름

```text
backend/app/main.py                      앱 시작·라우터·오류 처리·관리자 보호
  api/v1/regions.py                      지도·월별 검색 입력
    services/monthly_price_analyzer.py   날짜와 공항별 검색, 최저가 선택
      services/amadeus_service.py       개별·월별 검색 공통 공급자 경로
        services/exchange_rate_service.py   통화 환산
        services/price_history_service.py   실제 관측값 저장
  models/                               API 입력·응답 모델
  db_models/                            SQLAlchemy 저장 모델
  core/database.py                      공통 연결·세션
  tasks/celery_app.py                    유일한 Celery 앱
  tasks/monthly_data_collection.py       같은 월별 분석기를 사용하는 수집 작업
backend/alembic/                        DB 변경 이력
```

`app/config/settings.py`가 유일한 설정 소스입니다. `app/core/config.py`는 기존 인프라 코드용 재노출입니다. Redis가 없으면 같은 API 프로세스 안에서만 메모리 캐시를 공유합니다. 검색 캐시에는 출발·도착공항, 날짜, 인원, 통화, 직항 조건, 공급자 구분이 반영됩니다.

`price_observations`는 조회 시각, 여행 날짜, 출발·도착공항, 인원, 통화, 총운임, 원본 운임·환율, 수하물 관련 공급자 조건을 저장합니다. **작년 최저 월 통계나 예측을 제공하는 단계는 아닙니다.** 충분한 실제 관측과 비교 기준이 확보된 후 별도 집계가 필요합니다. 사용자·추천·기존 가격 테이블은 인프라 브랜치에서 보존했지만 현재 검색 경로는 관측 테이블을 사용합니다.

## 데이터베이스와 자동 수집

개발 환경에서는 시작 시 SQLite 테이블을 생성합니다. 운영 환경에서는 `INIT_DB_ON_STARTUP=false`로 설정하고 새 데이터베이스에 다음을 실행합니다:

```sh
alembic upgrade head
```

이미 테이블을 가진 DB에는 백업과 스키마 비교 없이 초기 마이그레이션을 적용하거나 stamp하지 마세요. 이번 초기 마이그레이션은 새 DB 기준입니다. PostgreSQL은 `DATABASE_URL=postgresql+psycopg2://...`로 설정합니다.

API와 worker에 동일한 DB·Redis·검색 설정을 제공한 뒤 별도 터미널에서 실행합니다:

```sh
celery -A app.tasks.celery_app:celery_app worker -l info -Q monthly_analysis,daily_updates
celery -A app.tasks.celery_app:celery_app beat -l info
```

예약 수집은 `COLLECTION_ORIGINS`의 모든 출발공항을 대상으로 합니다. 8개 출발공항 × 7개 도착공항 × 월별 약 10~11개 날짜만으로도 월 한 번 조회에 수백 회 호출이 발생합니다. 공급자 요금·쿼터에 맞게 공항 목록과 샘플 간격을 설정한 뒤 수집기를 실행하세요. 메모리 캐시는 worker와 API 사이에 공유되지 않습니다.

`/api/v1/cache/*`는 `ADMIN_API_KEY`를 설정해야 활성화되고 `X-Admin-Key` 헤더를 요구합니다. 갱신 작업은 현재 모든 일본 지역을 대상으로 합니다. 운영 환경은 별도의 지속적인 `SECRET_KEY`도 필요합니다.

LLM·예측 코드는 보존하지만 `ENABLE_EXPERIMENTAL_FEATURES=false`가 기본값입니다. 켜더라도 관리자 인증이 필요합니다. 기존 알림·예측의 메모리 기반 구현은 사용자용 운영 기능으로 검증되지 않았습니다. 계정 인증·예약·실제 알림 발송도 이번 범위에 포함하지 않습니다.

## 검증

```sh
pytest
black --check app tests conftest.py alembic
isort --check-only app tests conftest.py alembic
flake8 app tests conftest.py alembic --select E9,F63,F7,F82 --show-source
pytest --cov=app --cov-report=term-missing
```

CI는 모든 테스트를 실행하고 전체 코드 커버리지를 보고합니다. 통합한 검색·환율·월별 분석·저장·수집 경로에는 80% 커버리지 기준을 실제로 적용합니다. 기존에는 전체 80% 설정이 있었지만 CI에서 pytest 자체를 실행하지 않았습니다. 아직 검증이 부족한 실험·관리 기능까지 전체 80%를 달성했다고 주장하지 않습니다.

외부 공급자는 테스트에서 대체하고 DB는 격리된 SQLite를 사용합니다. 실제 Amadeus/환율 응답, PostgreSQL 서버, Redis/Celery 다중 프로세스 운영은 별도 통합 환경 검증이 필요합니다.

## 브랜치 전략

새 기능은 `feat/`, 구조 정리는 `refactor/`, 오류 수정은 `fix/`, 설정·유지보수는 `chore/`를 사용합니다. 현재 통합 브랜치는 `refactor/flight-search-integration`입니다. 기능 브랜치의 이력을 보존해 통합하며, `main` 반영은 검토 후 진행합니다.
