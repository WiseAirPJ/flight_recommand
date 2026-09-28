# 항공권 추천 시스템 데이터베이스 정의서

## 개요
이 문서는 **지능형 일본 항공권 분석기** 프로젝트의 데이터 구조 및 데이터베이스 아키텍처를 정의합니다.

**프로젝트 정보:**
- 프로젝트명: flight-analyzer
- 버전: 0.2.0
- Python 버전: 3.12+
- 프레임워크: FastAPI

---

## 1. 데이터베이스 아키텍처

### 1.1 전체 구조
```
┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │      Redis      │
│  (Primary DB)   │    │    (Cache)      │
│                 │    │                 │
│ • 항공편 데이터  │    │ • 검색 결과     │
│ • 지역 정보     │    │ • 최저가 정보   │
│ • 가격 히스토리 │    │ • 세션 데이터   │
│                 │    │ • 환율 정보     │
└─────────────────┘    └─────────────────┘
```

### 1.2 기술 스택
- **주 데이터베이스**: PostgreSQL (psycopg2-binary)
- **캐시 시스템**: Redis
- **ORM**: SQLAlchemy 2.0+
- **마이그레이션**: Alembic
- **비동기 처리**: Celery

---

## 2. PostgreSQL 데이터베이스 구조

### 2.1 데이터베이스 설정
```python
# 연결 설정 (settings.py)
DATABASE_URL: Optional[str]           # 기본 데이터베이스 URL
DATABASE_ECHO: bool = False          # SQL 쿼리 로그 출력

# Azure PostgreSQL 설정
AZURE_DB_HOST: Optional[str]         # Azure DB 호스트
AZURE_DB_NAME: Optional[str]         # 데이터베이스 명
AZURE_DB_USER: Optional[str]         # 사용자명
AZURE_DB_PASSWORD: Optional[str]     # 비밀번호
AZURE_DB_PORT: Optional[str]         # 포트 (기본값: 5432)
AZURE_DB_SSLMODE: Optional[str]      # SSL 모드
```

### 2.2 데이터 모델

#### 2.2.1 항공편 구간 정보 (FlightSegment)
```python
class FlightSegment(BaseModel):
    departure: Dict[str, Any]         # 출발 정보
    arrival: Dict[str, Any]           # 도착 정보
    carrier_code: str                 # 항공사 코드
    flight_number: str                # 항공편 번호
    duration: Optional[str]           # 비행 시간
```

**필드 상세:**
- `departure`: 출발 공항, 시간 정보
- `arrival`: 도착 공항, 시간 정보
- `carrier_code`: IATA 항공사 코드 (예: "KE", "OZ")
- `flight_number`: 항공편 식별번호
- `duration`: ISO 8601 형식 또는 시간 문자열

#### 2.2.2 항공편 일정 (FlightItinerary)
```python
class FlightItinerary(BaseModel):
    duration: str                     # 총 소요 시간
    segments: List[FlightSegment]     # 구간 목록
```

#### 2.2.3 항공편 가격 정보 (FlightPrice)
```python
class FlightPrice(BaseModel):
    currency: str                     # 통화 (기본값: "KRW")
    total: str                        # 총 가격
    base: Optional[str]               # 기본 요금
    fees: Optional[List[Dict]]        # 수수료 목록
```

#### 2.2.4 항공편 제안 (FlightOffer)
```python
class FlightOffer(BaseModel):
    id: str                           # 항공편 ID
    source: str                       # 데이터 소스 ("GDS", "Amadeus")
    itineraries: List[FlightItinerary] # 일정 목록
    price: FlightPrice                # 가격 정보
    traveler_pricings: Optional[List] # 승객별 가격
```

**예시 데이터:**
```json
{
  "id": "1",
  "source": "GDS",
  "price": {
    "currency": "KRW",
    "total": "280000",
    "base": "250000"
  }
}
```

#### 2.2.5 공항 정보 (Airport)
```python
class Airport(BaseModel):
    iata: str                         # IATA 코드 (3자리)
    name: str                         # 공항 이름
    city: str                         # 도시명
    is_international: bool = True     # 국제공항 여부
```

**예시 데이터:**
```json
{
  "iata": "CTS",
  "name": "신치토세공항",
  "city": "삿포로",
  "is_international": true
}
```

#### 2.2.6 지역 정보 (Region)
```python
class Region(BaseModel):
    id: str                           # 지역 ID
    name: str                         # 지역명 (한글)
    name_en: str                      # 영문명
    airports: List[Airport]           # 공항 목록
    main_airport: str                 # 주요 공항 IATA 코드
    coordinates: Optional[List[List[float]]] # 지도 폴리곤 좌표
```

**예시 데이터:**
```json
{
  "id": "hokkaido",
  "name": "홋카이도",
  "name_en": "Hokkaido",
  "main_airport": "CTS",
  "airports": [...],
  "coordinates": [[...], [...]]
}
```

#### 2.2.7 지역별 가격 정보 (RegionalPrice)
```python
class RegionalPrice(BaseModel):
    region_id: str                    # 지역 ID
    region_name: str                  # 지역명
    price: int                        # 최저가 (원)
    departure_date: str               # 출발일 (YYYY-MM-DD)
    return_date: str                  # 귀국일 (YYYY-MM-DD)
    duration_days: int                # 여행 기간
    airport: str                      # 공항 코드
    last_updated: str                 # 마지막 업데이트 (ISO 8601)
```

### 2.3 요청 모델

#### 2.3.1 기본 항공편 검색 요청 (FlightSearchRequest)
```python
class FlightSearchRequest(BaseModel):
    origin: str                       # 출발지 IATA 코드
    destination: str                  # 도착지 IATA 코드
    departure_date: str               # 출발 날짜 (YYYY-MM-DD)
    return_date: Optional[str]        # 귀국 날짜 (YYYY-MM-DD)
    adults: int = Field(1, ge=1, le=9) # 성인 승객 수
    currency: str = "KRW"             # 통화 코드
```

**유효성 검증:**
- 날짜 형식: `validate_date_format()`
- 승객 수: `validate_passenger_count()` (1~9명)

#### 2.3.2 여행 기간 기반 검색 요청 (FlightDurationSearchRequest)
```python
class FlightDurationSearchRequest(BaseModel):
    origin: str = "ICN"               # 출발지 (기본값: 인천공항)
    destination: str                  # 도착지 IATA 코드
    departure_date: str               # 출발 날짜
    duration_days: int = Field(ge=2, le=30) # 여행 기간 (2~30일)
    adults: int = Field(1, ge=1, le=9) # 성인 승객 수
    currency: str = "KRW"             # 통화 코드
```

#### 2.3.3 편도 항공편 검색 요청 (OneWayFlightSearchRequest)
```python
class OneWayFlightSearchRequest(BaseModel):
    origin: str                       # 출발지 IATA 코드
    destination: str                  # 도착지 IATA 코드
    departure_date: str               # 출발 날짜
    adults: int = Field(1, ge=1, le=9) # 성인 승객 수
    currency: str = "KRW"             # 통화 코드
```

#### 2.3.4 최저가 날짜 검색 요청 (CheapestDateRequest)
```python
class CheapestDateRequest(BaseModel):
    origin: str                       # 출발지 IATA 코드
    destination: str                  # 도착지 IATA 코드
    departure_date: str               # 기준 출발 날짜
    duration: Optional[int] = Field(ge=1, le=30) # 여행 기간
    flexibility_days: int = Field(7, ge=1, le=15) # 날짜 유연성 (±일수)
    trip_type: str = "round-trip"     # 여행 유형 ("one-way", "round-trip")
```

---

## 3. Redis 캐시 시스템

### 3.1 Redis 설정
```python
# Redis 연결 설정
REDIS_HOST: Optional[str]             # Redis 호스트
REDIS_PORT: Optional[str]             # Redis 포트 (기본값: 6379)
REDIS_USERNAME: Optional[str]         # Redis 사용자명
REDIS_PASSWORD: Optional[str]         # Redis 비밀번호

# 연결 옵션
decode_responses: bool = True         # 응답 디코딩
socket_timeout: int = 5               # 소켓 타임아웃 (초)
socket_connect_timeout: int = 5       # 연결 타임아웃 (초)
```

### 3.2 캐시 키 구조

#### 3.2.1 캐시 키 네이밍 규칙
```python
cache_keys = {
    "regional_prices": "regional_lowest_prices",
    "monthly_data": "monthly_cheapest:{origin}:{year}:{month:02d}",
    "cache_stats": "cache_statistics",
    "date_info": "date_info:{date}",
    "exchange_rate": "exchange_rate:KRW_JPY",
    "airport_search": "airport_search:{query}",
    "performance_metrics": "performance_metrics:{hour}"
}
```

#### 3.2.2 동적 캐시 키 생성 함수

**항공편 검색 키:**
```python
def flight_search_key(*args, **kwargs) -> str:
    # 형식: flight_search:{origin}:{destination}:{departure_date}:{return_date}:{adults}
    # 예시: "flight_search:ICN:CTS:2025-08-15:2025-08-18:1"
```

**기간 검색 키:**
```python
def duration_search_key(*args, **kwargs) -> str:
    # 형식: duration_search:{origin}:{destination}:{departure_date}:{duration_days}:{adults}
    # 예시: "duration_search:ICN:CTS:2025-08-15:3:1"
```

**최저가 날짜 키:**
```python
def cheapest_dates_key(*args, **kwargs) -> str:
    # 형식: cheapest_dates:{origin}:{destination}:{departure_date}:{duration}:{flexibility_days}
    # 예시: "cheapest_dates:ICN:CTS:2025-08-15:3:7"
```

**공항 정보 키:**
```python
def airport_info_key(*args, **kwargs) -> str:
    # 형식: airport_info:{iata_code}
    # 예시: "airport_info:CTS"
```

**인기 경로 키:**
```python
def popular_routes_key(*args, **kwargs) -> str:
    # 형식: popular_routes:{origin}:{limit}
    # 예시: "popular_routes:ICN:10"
```

### 3.3 캐시 데이터 모델

#### 3.3.1 캐시 키 정보 (CacheKey)
```python
class CacheKey(BaseModel):
    key: str                          # 캐시 키
    ttl: int                          # TTL (초, -1은 영구)
    type: str                         # 데이터 타입
    size_bytes: Optional[int]         # 크기 (바이트)
```

#### 3.3.2 캐시 상태 (CacheStatus)
```python
class CacheStatus(BaseModel):
    cache_type: str                   # 캐시 타입 ("redis", "memory")
    status: str                       # 상태 ("healthy", "degraded", "error")
    total_keys: int                   # 전체 키 수
    active_keys: int                  # 활성 키 수
    expired_keys: int                 # 만료된 키 수
    memory_usage: Dict[str, Any]      # 메모리 사용량
    last_updated: str                 # 마지막 업데이트
```

**예시 데이터:**
```json
{
  "cache_type": "redis",
  "status": "healthy",
  "total_keys": 150,
  "active_keys": 142,
  "expired_keys": 8,
  "memory_usage": {
    "used_memory_human": "2.5MB",
    "mem_fragmentation_ratio": 1.1
  },
  "last_updated": "2025-07-04T10:00:00Z"
}
```

#### 3.3.3 캐시 통계 (CacheStatistics)
```python
class CacheStatistics(BaseModel):
    cache_hit_rate: float             # 캐시 히트율 (%)
    total_requests: int               # 총 요청 수
    cache_hits: int                   # 캐시 히트 수
    cache_misses: int                 # 캐시 미스 수
    avg_response_time: Optional[float] # 평균 응답 시간 (ms)
```

**예시 데이터:**
```json
{
  "cache_hit_rate": 85.6,
  "total_requests": 1250,
  "cache_hits": 1070,
  "cache_misses": 180,
  "avg_response_time": 45.2
}
```

### 3.4 캐시 서비스 기능

#### 3.4.1 CacheService 클래스 주요 메서드

**상태 관리:**
- `get_cache_status()`: 캐시 시스템 전반 상태 조회
- `get_cache_statistics()`: 캐시 사용 통계 조회
- `health_check()`: 캐시 서비스 헬스 체크

**데이터 관리:**
- `refresh_cache()`: 캐시 데이터 갱신
- `cleanup_expired_cache()`: 만료된 캐시 데이터 정리
- `warmup_cache()`: 캐시 워밍업

**키 관리:**
- `get_cache_keys()`: 캐시 키 목록 조회
- `delete_cache_key()`: 특정 캐시 키 삭제
- `clear_cache_pattern()`: 패턴에 맞는 캐시 삭제

**메모리 관리:**
- `get_memory_usage()`: 메모리 사용량 상세 조회
- `get_performance_metrics()`: 성능 지표 조회

#### 3.4.2 폴백 메모리 캐시
Redis 연결이 실패할 경우 메모리 캐시로 자동 전환:
```python
# 폴백 시스템
self._memory_cache = {}               # 대체 메모리 캐시
self.is_connected = False             # 연결 상태
```

**메모리 캐시 제한:**
- 최대 키 개수: 1,000개
- 만료 시간 체크: 자동
- LRU 방식 제거: 오래된 키부터 삭제

### 3.5 캐시 TTL 설정

#### 3.5.1 기본 TTL 정책
```python
EFFICIENCY_SCORE_CACHE_TTL: int = 3600  # 효율성 점수 (1시간)

# 동적 TTL
# - 항공편 검색: 1시간 (3600초)
# - 지역별 최저가: 6시간 (21600초)
# - 월간 데이터: 24시간 (86400초)
# - 환율 정보: 1시간 (3600초)
# - 공항 검색: 24시간 (86400초)
```

#### 3.5.2 캐시 갱신 전략
- **스케줄 기반**: Celery 태스크로 주기적 갱신
- **온디맨드**: 요청 시점에 만료된 캐시 갱신
- **워밍업**: 서비스 시작 시 자주 사용되는 데이터 미리 로드

---

## 4. 백그라운드 작업 (Celery)

### 4.1 Celery 설정
```python
# Celery 브로커 및 결과 백엔드
CELERY_BROKER_URL: Optional[str]      # Celery 브로커 URL (Redis)
CELERY_RESULT_BACKEND: Optional[str]  # Celery 결과 백엔드 (Redis)
```

### 4.2 주요 태스크

#### 4.2.1 월간 최저가 데이터 수집
```python
@celery_app.task
def collect_monthly_cheapest_data(year: int, month: int, origin: str = "ICN"):
    # 지정된 년월의 모든 지역 최저가 데이터 수집
    # 캐시 키: monthly_cheapest:{origin}:{year}:{month:02d}
```

**기능:**
- Amadeus API 호출하여 항공편 데이터 수집
- 각 지역별 최저가 계산 및 캐싱
- 실패 시 재시도 메커니즘
- 진행 상황 로깅

---

## 5. 데이터 유효성 검증

### 5.1 유효성 검증 함수

#### 5.1.1 날짜 검증
```python
def validate_date_format(date_str: str) -> str:
    # YYYY-MM-DD 형식 검증
    # 미래 날짜인지 확인
    # 유효한 날짜인지 확인
```

#### 5.1.2 승객 수 검증
```python
def validate_passenger_count(count: int) -> int:
    # 1~9명 범위 확인
    # 정수 타입 확인
```

#### 5.1.3 여행 기간 검증
```python
def validate_duration(days: int, min_days: int = 2) -> int:
    # 최소/최대 기간 확인 (2~30일)
    # 정수 타입 확인
```

### 5.2 Pydantic 필드 검증

모든 데이터 모델에서 `field_validator` 데코레이터 사용:
- 자동 타입 변환
- 범위 검증 (`ge`, `le`)
- 길이 검증 (`min_length`)
- 커스텀 검증 로직

---

## 6. 환경 설정 및 보안

### 6.1 보안 설정
```python
SECRET_KEY: str                       # JWT 토큰 서명 키 (최소 32자)
ALGORITHM: str = "HS256"              # 암호화 알고리즘
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 # 액세스 토큰 만료 시간
```

### 6.2 외부 API 설정

#### 6.2.1 Amadeus API
```python
AMADEUS_CLIENT_ID: Optional[str]      # Amadeus 클라이언트 ID
AMADEUS_CLIENT_SECRET: Optional[str]  # Amadeus 클라이언트 시크릿
AMADEUS_BASE_URL: str                 # API 기본 URL
AMADEUS_HOSTNAME: str                 # 호스트명
USE_REAL_AMADEUS: bool = False        # 실제 API 사용 여부
ENABLE_DUMMY_FALLBACK: bool = True    # 더미 데이터 폴백
```

#### 6.2.2 LLM 서비스 설정
```python
# OpenAI
OPENAI_API_KEY: Optional[str]

# Azure OpenAI
AZURE_OPENAI_API_KEY: Optional[str]
AZURE_OPENAI_ENDPOINT: Optional[str]
AZURE_OPENAI_DEPLOYMENT_NAME: str

# Anthropic
ANTHROPIC_API_KEY: Optional[str]

# 공통 설정
LLM_PROVIDER: str = "openai"          # 제공자 선택
LLM_MODEL: str = "gpt-4o-mini"        # 사용 모델
LLM_MAX_TOKENS: int = 4000            # 최대 토큰
LLM_TEMPERATURE: float = 0.7          # 창의성 설정
```

#### 6.2.3 환율 API
```python
KOREAEXIM_API_KEY: Optional[str]      # 한국수출입은행 API 키
KOREAEXIM_BASE_URL: str               # API 기본 URL
```

### 6.3 CORS 설정
```python
ALLOWED_ORIGINS: List[str] = [
    "http://localhost:3000",          # 개발 환경
    "http://localhost:8000"           # API 서버
]
```

---

## 7. 모니터링 및 로깅

### 7.1 로깅 설정
```python
LOG_LEVEL: str = "INFO"               # 로그 레벨
```

### 7.2 성능 모니터링

#### 7.2.1 캐시 성능 지표
- 히트율 (Hit Rate)
- 평균 응답 시간
- 메모리 사용량
- 연결된 클라이언트 수

#### 7.2.2 최적화 권장사항
- 메모리 단편화 > 1.5: Redis 재시작 권장
- 캐시 키 > 10,000개: TTL 단축 권장
- 메모리 사용량 > 1GB: 캐시 정책 검토
- 히트율 < 80%: 캐시 전략 검토

---

## 8. 운영 가이드

### 8.1 배포 환경 설정

#### 8.1.1 필수 환경 변수
```bash
# 데이터베이스
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_password

# API 키
AMADEUS_CLIENT_ID=your_client_id
AMADEUS_CLIENT_SECRET=your_client_secret
OPENAI_API_KEY=your_openai_key

# 보안
SECRET_KEY=your_32_char_secret_key
```

#### 8.1.2 Docker 환경
```yaml
# docker-compose.yml 예시
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: flight_analyzer
      POSTGRES_USER: app_user
      POSTGRES_PASSWORD: app_password

  redis:
    image: redis:7
    command: redis-server --requirepass your_password

  celery:
    build: .
    command: celery -A app.tasks.celery_app worker --loglevel=info
```

### 8.2 유지보수

#### 8.2.1 정기 작업
- **일간**: 만료된 캐시 정리
- **주간**: 데이터베이스 백업 및 최적화
- **월간**: 사용하지 않는 데이터 아카이빙

#### 8.2.2 모니터링 체크포인트
- Redis 연결 상태
- PostgreSQL 연결 상태
- Celery 워커 상태
- API 응답 시간
- 캐시 히트율

---

## 9. 버전 히스토리

### v0.2.0 (현재)
- PostgreSQL + Redis 아키텍처 구성
- Amadeus API 통합
- LLM 서비스 통합
- 캐시 시스템 구현
- Celery 백그라운드 태스크

### 향후 계획
- 데이터베이스 샤딩
- 읽기 전용 복제본 추가
- 캐시 클러스터링
- 실시간 데이터 파이프라인
