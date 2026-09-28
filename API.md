# 📡 API 문서

지능형 일본 항공권 분석기 REST API 상세 문서입니다.

## 🎯 현재 상태: 48개 엔드포인트 완전 구현 ✅

**2025년 7월 6일 기준: 모든 API 엔드포인트 완성 및 테스트 검증 완료**

---

## 📋 목차

- [🔗 기본 정보](#-기본-정보)
- [🛡️ 인증](#️-인증)
- [📍 시스템 API](#-시스템-api)
- [🗾 지역 관리 API](#-지역-관리-api)
- [✈️ 항공편 검색 API](#️-항공편-검색-api)
- [📊 월별 분석 API](#-월별-분석-api)
- [🛠️ 유틸리티 API](#️-유틸리티-api)
- [📅 날짜 관리 API](#-날짜-관리-api)
- [💾 캐시 관리 API](#-캐시-관리-api)
- [📊 응답 형식](#-응답-형식)
- [❌ 에러 코드](#-에러-코드)
- [🔍 API 사용 예시](#-api-사용-예시)
- [🚀 성능 정보](#-성능-정보)

## 🔗 기본 정보

- **Base URL**: `http://localhost:8000` (개발), `https://api.yourdomain.com` (운영)
- **API Version**: v1
- **Content-Type**: `application/json`
- **Character Encoding**: UTF-8
- **Framework**: FastAPI 0.115
- **Python Version**: 3.12
- **총 엔드포인트**: 48개

### 대화형 API 문서

- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI JSON**: `/openapi.json`

### 📊 API 완성도

| 카테고리 | 엔드포인트 수 | 완성도 | 설명 |
|---------|-------------|-------|------|
| 시스템 API | 3개 | ✅ 100% | 헬스체크, 상태 확인 |
| 지역 관리 API | 4개 | ✅ 100% | 지역별 최저가, 공항 정보 |
| 항공편 검색 API | 5개 | ✅ 100% | 기본/기간별 검색 |
| 월별 분석 API | 4개 | ✅ 100% | 월별 최저가 분석 |
| 유틸리티 API | 6개 | ✅ 100% | 공항 검색, 환율 정보 |
| 환율 API | 5개 | ✅ 100% | 한국수출입은행 환율 연동 |
| 날짜 관리 API | 15개 | ✅ 100% | 공휴일, 시즌 정보 |
| 캐시 관리 API | 6개 | ✅ 100% | 캐시 상태, 통계 |
| **총합** | **48개** | **✅ 100%** | **모든 기능 완성** |

## 🛡️ 인증

현재 Phase 1에서는 인증이 필요하지 않습니다. Phase 2에서 JWT 기반 인증이 추가될 예정입니다.

### 미래 인증 계획 (Phase 2)

- **JWT 토큰**: Bearer 인증 방식
- **사용자 등급**: Basic, Premium, Enterprise
- **API 호출 제한**: 등급별 차등 적용
- **캐시 우선순위**: 사용자 등급에 따른 캐시 우선순위

## 📍 시스템 API

### 시스템 상태 확인

#### `GET /health`

전체 시스템의 상태를 확인합니다.

**응답 예시:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-06T12:00:00Z",
  "environment": "development",
  "python_version": "3.12",
  "services": {
    "amadeus_api": {
      "status": "healthy",
      "active": true
    },
    "cache_system": {
      "status": "healthy",
      "connected": true,
      "type": "redis"
    },
    "region_data": {
      "status": "healthy",
      "loaded_regions": 8
    }
  },
  "api_endpoints": {
    "total_routes": 43,
    "core_apis": [
      "/api/v1/regions/lowest-prices",
      "/api/v1/flights/search-by-duration",
      "/api/v1/flights/monthly-cheapest",
      "/api/v1/utils/date-info",
      "/api/v1/cache/status"
    ]
  }
}
```

### API 정보

#### `GET /api/v1`

API 버전 및 기능 정보를 반환합니다.

**응답 예시:**
```json
{
  "message": "지능형 일본 항공권 분석기 API v1",
  "version": "0.2.0",
  "environment": "development",
  "python_version": "3.12.4",
  "phase": "Phase 1 MVP",
  "status": "완성",
  "available_routes": {
    "regions": "/api/v1/regions",
    "flights": "/api/v1/flights",
    "utils": "/api/v1/utils",
    "cache": "/api/v1/cache"
  },
  "core_features": [
    "지역별 최저가 조회",
    "기간별 항공편 검색",
    "날짜/시즌 정보",
    "캐시 시스템"
  ]
}
```

### API 상태

#### `GET /api/v1/status`

API별 완성 상태를 확인합니다.

**응답 예시:**
```json
{
  "api_version": "v1",
  "phase": "Phase 1 MVP Complete",
  "completion_status": {
    "regions_api": "✅ 완성",
    "flights_api": "✅ 완성",
    "utils_api": "✅ 완성",
    "cache_api": "✅ 완성"
  },
  "next_phase": "Phase 2 - LLM 분석 기능",
  "ready_for_frontend": true
}
```

## 🗾 지역 관리 API

### 지역 목록 조회

#### `GET /api/v1/regions/`

일본의 모든 지역 정보를 조회합니다.

**응답 예시:**
```json
{
  "success": true,
  "message": "지역 목록 조회 완료",
  "data": {
    "hokkaido": {
      "id": "hokkaido",
      "name": "홋카이도",
      "name_en": "Hokkaido",
      "main_airport": "CTS",
      "airports": [
        {
          "iata": "CTS",
          "name": "신치토세공항",
          "city": "삿포로",
          "is_international": true
        }
      ]
    },
    "kanto": {
      "id": "kanto",
      "name": "간토 (도쿄)",
      "name_en": "Kanto (Tokyo)",
      "main_airport": "NRT",
      "airports": [
        {
          "iata": "NRT",
          "name": "나리타국제공항",
          "city": "도쿄",
          "is_international": true
        },
        {
          "iata": "HND",
          "name": "하네다공항",
          "city": "도쿄",
          "is_international": true
        }
      ]
    }
  }
}
```

### 지역별 최저가 조회

#### `GET /api/v1/regions/lowest-prices`

**🎯 메인 화면용 핵심 API** - 모든 지역의 최저가 정보를 조회합니다.

**Query Parameters:**
- `origin` (optional): 출발지 IATA 코드 (기본값: "ICN")
- `duration_days` (optional): 여행 기간 (기본값: 4)

**응답 예시:**
```json
{
  "success": true,
  "message": "지역별 최저가 조회 완료",
  "data": {
    "hokkaido": {
      "region_id": "hokkaido",
      "region_name": "홋카이도",
      "price": 280000,
      "departure_date": "2025-08-15",
      "return_date": "2025-08-18",
      "duration_days": 4,
      "airport": "CTS",
      "last_updated": "2025-07-06T12:00:00Z"
    },
    "kanto": {
      "region_id": "kanto",
      "region_name": "간토 (도쿄)",
      "price": 320000,
      "departure_date": "2025-08-16",
      "return_date": "2025-08-19",
      "duration_days": 4,
      "airport": "NRT",
      "last_updated": "2025-07-06T12:00:00Z"
    }
  },
  "last_updated": "2025-07-06T12:00:00Z"
}
```

### 지역별 공항 목록

#### `GET /api/v1/regions/{region_id}/airports`

특정 지역의 공항 목록을 조회합니다.

**Path Parameters:**
- `region_id`: 지역 ID (예: "hokkaido", "kanto")

**응답 예시:**
```json
{
  "success": true,
  "message": "홋카이도 지역 공항 목록",
  "data": {
    "region_id": "hokkaido",
    "region_name": "홋카이도",
    "airports": [
      {
        "iata": "CTS",
        "name": "신치토세공항",
        "city": "삿포로",
        "is_international": true
      },
      {
        "iata": "HKD",
        "name": "하코다테공항",
        "city": "하코다테",
        "is_international": false
      }
    ]
  }
}
```

## ✈️ 항공편 검색 API

### 기본 항공편 검색

#### `POST /api/v1/flights/search`

출발지, 도착지, 날짜를 지정하여 항공편을 검색합니다.

**Request Body:**
```json
{
  "origin": "ICN",
  "destination": "NRT",
  "departure_date": "2025-08-15",
  "return_date": "2025-08-18",
  "adults": 1,
  "currency": "KRW"
}
```

**응답 예시:**
```json
{
  "success": true,
  "message": "항공편 검색 완료",
  "data": [
    {
      "id": "1",
      "source": "GDS",
      "itineraries": [
        {
          "duration": "PT2H30M",
          "segments": [
            {
              "departure": {
                "iataCode": "ICN",
                "at": "2025-08-15T09:00:00"
              },
              "arrival": {
                "iataCode": "NRT",
                "at": "2025-08-15T11:30:00"
              },
              "carrierCode": "KE",
              "number": "704"
            }
          ]
        }
      ],
      "price": {
        "currency": "KRW",
        "total": "280000",
        "base": "250000"
      }
    }
  ],
  "meta": {
    "count": 10
  }
}
```

### 기간별 항공편 검색

#### `POST /api/v1/flights/search-by-duration`

**⭐ 핵심 기능** - 여행 기간을 지정하여 최적의 항공편을 검색합니다.

**Request Body:**
```json
{
  "origin": "ICN",
  "destination": "CTS",
  "departure_date": "2025-08-15",
  "duration_days": 4,
  "adults": 1,
  "currency": "KRW"
}
```

**응답 예시:**
```json
{
  "success": true,
  "message": "4일 여행 항공편 검색 완료",
  "data": [
    {
      "id": "duration-search-1",
      "calculated_return_date": "2025-08-18",
      "duration_info": {
        "requested_days": 4,
        "actual_days": 4,
        "nights": 3
      },
      "price": {
        "currency": "KRW",
        "total": "280000"
      },
      "itineraries": [...]
    }
  ],
  "meta": {
    "search_params": {
      "duration_days": 4,
      "calculated_return": "2025-08-18"
    }
  }
}
```

### 최저가 날짜 검색

#### `POST /api/v1/flights/cheapest-dates`

날짜 유연성을 두고 최저가 날짜를 찾습니다.

**Request Body:**
```json
{
  "origin": "ICN",
  "destination": "NRT",
  "departure_date": "2025-08-15",
  "duration": 4,
  "flexibility_days": 7
}
```

**응답 예시:**
```json
{
  "success": true,
  "message": "최저가 날짜 검색 완료",
  "data": [
    {
      "type": "flight-date",
      "origin": "ICN",
      "destination": "NRT",
      "departureDate": "2025-08-13",
      "returnDate": "2025-08-16",
      "price": {
        "total": "250000",
        "currency": "KRW"
      }
    }
  ],
  "meta": {
    "flexibility_range": "±7 days",
    "cheapest_price": "250000",
    "savings": "30000"
  }
}
```

### 공항 정보 조회

#### `GET /api/v1/flights/airport/{iata_code}`

특정 공항의 상세 정보를 조회합니다.

**Path Parameters:**
- `iata_code`: IATA 공항 코드 (예: "ICN", "NRT")

**응답 예시:**
```json
{
  "success": true,
  "message": "공항 정보 조회 완료",
  "data": {
    "type": "location",
    "subType": "AIRPORT",
    "name": "Incheon International Airport",
    "iataCode": "ICN",
    "address": {
      "cityName": "Seoul",
      "countryName": "South Korea",
      "countryCode": "KR"
    }
  }
}
```

### 인기 노선 조회

#### `GET /api/v1/flights/popular-routes`

인기 항공 노선 정보를 조회합니다.

**Query Parameters:**
- `origin` (optional): 출발지 (기본값: "ICN")
- `limit` (optional): 결과 수 (기본값: 10)

**응답 예시:**
```json
{
  "success": true,
  "message": "인기 노선 조회 완료",
  "data": [
    {
      "destination": "NRT",
      "destination_name": "도쿄 (나리타)",
      "popularity_score": 95,
      "avg_price": "320000",
      "flight_time": "2h 30m"
    },
    {
      "destination": "CTS",
      "destination_name": "삿포로 (신치토세)",
      "popularity_score": 88,
      "avg_price": "280000",
      "flight_time": "2h 45m"
    }
  ]
}
```

## 📊 월별 분석 API

### 월별 최저가 검색

#### `GET /api/v1/flights/monthly-cheapest`

**⭐ 핵심 기능** - 특정 월의 지역별 최저가 일정을 분석합니다.

**Query Parameters:**
- `year`: 대상 연도 (필수)
- `month`: 대상 월 (필수, 1-12)
- `origin`: 출발지 IATA 코드 (기본값: "ICN")
- `duration`: 여행 기간 (기본값: 4일)

**응답 예시:**
```json
{
  "success": true,
  "message": "2025년 8월 월별 최저가 분석 완료",
  "data": {
    "search_params": {
      "year": 2025,
      "month": 8,
      "origin": "ICN",
      "duration": 4
    },
    "regions": {
      "hokkaido": {
        "region_name": "홋카이도",
        "cheapest_price": 280000,
        "departure_date": "2025-08-15",
        "return_date": "2025-08-18",
        "airport": "CTS",
        "price_trend": "medium"
      },
      "kanto": {
        "region_name": "간토 (도쿄)",
        "cheapest_price": 320000,
        "departure_date": "2025-08-16",
        "return_date": "2025-08-19",
        "airport": "NRT",
        "price_trend": "high"
      }
    },
    "summary": {
      "total_regions": 6,
      "cheapest_region": "hokkaido",
      "most_expensive_region": "okinawa",
      "avg_price": 340000,
      "price_range": {
        "min": 280000,
        "max": 450000
      }
    }
  }
}
```

### 이번 달 최저가 (단축 API)

#### `GET /api/v1/flights/this-month-cheapest`

이번 달의 최저가 정보를 빠르게 조회합니다.

**Query Parameters:**
- `origin` (optional): 출발지 (기본값: "ICN")
- `duration` (optional): 여행 기간 (기본값: 4일)

### 다음 달 최저가

#### `GET /api/v1/flights/next-month-cheapest`

다음 달의 최저가 정보를 조회합니다.

**Query Parameters:**
- `origin` (optional): 출발지 (기본값: "ICN")
- `duration` (optional): 여행 기간 (기본값: 4일)

### 특정 월 분석

#### `GET /api/v1/flights/monthly-analysis/{year}/{month}`

특정 연도/월의 상세 분석 정보를 조회합니다.

**Path Parameters:**
- `year`: 연도 (예: 2025)
- `month`: 월 (예: 8)

**Query Parameters:**
- `origin` (optional): 출발지 (기본값: "ICN")
- `include_trends` (optional): 가격 트렌드 포함 여부 (기본값: true)

## 🛠️ 유틸리티 API

### 날짜 정보 조회

#### `GET /api/v1/utils/date-info`

**⭐ 핵심 기능** - 일본 공휴일, 시즌 정보 및 가격 영향도를 조회합니다.

**Query Parameters:**
- `date`: 조회할 날짜 (YYYY-MM-DD 형식)

**응답 예시:**
```json
{
  "success": true,
  "message": "날짜 정보 조회 완료",
  "data": {
    "date": "2025-05-03",
    "weekday": 5,
    "weekday_name": "토",
    "is_weekend": true,
    "is_holiday": true,
    "holiday_name": "헌법기념일",
    "season": "golden_week",
    "price_impact": "very_high",
    "description": "골든위크 핵심 기간",
    "recommendations": [
      "항공료 최고 성수기",
      "3개월 전 예약 권장",
      "대체 날짜 고려"
    ]
  }
}
```

### 공항 검색 (자동완성)

#### `GET /api/v1/utils/airports/search`

공항명이나 도시명으로 공항을 검색합니다.

**Query Parameters:**
- `query`: 검색어 (공항명, 도시명, IATA 코드)
- `limit` (optional): 결과 수 (기본값: 10)

**응답 예시:**
```json
{
  "success": true,
  "message": "공항 검색 완료",
  "data": [
    {
      "iata": "NRT",
      "name": "나리타국제공항",
      "city": "도쿄",
      "region_id": "kanto",
      "region_name": "간토 (도쿄)",
      "is_international": true
    },
    {
      "iata": "HND",
      "name": "하네다공항",
      "city": "도쿄",
      "region_id": "kanto",
      "region_name": "간토 (도쿄)",
      "is_international": true
    }
  ]
}
```

### 환율 정보 조회

#### `GET /api/v1/utils/exchange-rate`

KRW/JPY 환율 정보를 조회합니다.

**응답 예시:**
```json
{
  "success": true,
  "message": "환율 정보 조회 완료",
  "data": {
    "from_currency": "KRW",
    "to_currency": "JPY",
    "rate": 0.1089,
    "last_updated": "2025-07-06T12:00:00Z",
    "source": "exchange_api"
  }
}
```

### 일본 공휴일 조회

#### `GET /api/v1/utils/holidays`

연도별 일본 공휴일 정보를 조회합니다.

**Query Parameters:**
- `year`: 조회할 연도 (기본값: 현재 연도)

**응답 예시:**
```json
{
  "success": true,
  "message": "2025년 일본 공휴일 조회 완료",
  "data": [
    {
      "date": "2025-01-01",
      "name": "元日",
      "name_en": "New Year's Day",
      "type": "national",
      "season": "winter_holiday",
      "price_impact": "very_high",
      "description": "연말연시 성수기"
    },
    {
      "date": "2025-05-03",
      "name": "憲法記念日",
      "name_en": "Constitution Memorial Day",
      "type": "national",
      "season": "golden_week",
      "price_impact": "very_high",
      "description": "골든위크 핵심 기간"
    }
  ]
}
```

### 여행 시즌 정보

#### `GET /api/v1/utils/seasons`

일본 여행 시즌 정보를 조회합니다.

**응답 예시:**
```json
{
  "success": true,
  "message": "여행 시즌 정보 조회 완료",
  "data": {
    "golden_week": {
      "period": "4월 말 ~ 5월 초",
      "price_impact": "very_high",
      "description": "최고 성수기"
    },
    "cherry_blossom": {
      "period": "3월 말 ~ 4월 중순",
      "price_impact": "high",
      "description": "벚꽃 시즌"
    },
    "autumn_leaves": {
      "period": "10월 ~ 11월",
      "price_impact": "high",
      "description": "단풍 시즌"
    }
  }
}
```

### 가격 동향 정보

#### `GET /api/v1/utils/price-trends`

월별 가격 동향 정보를 조회합니다.

**응답 예시:**
```json
{
  "success": true,
  "message": "가격 동향 정보 조회 완료",
  "data": {
    "monthly_trends": {
      "1": "very_high",
      "2": "low",
      "3": "high",
      "4": "very_high",
      "5": "very_high",
      "6": "medium",
      "7": "high",
      "8": "high",
      "9": "medium",
      "10": "high",
      "11": "high",
      "12": "very_high"
    },
    "best_months": ["2", "6", "9"],
    "worst_months": ["1", "4", "5", "12"]
  }
}
```

## 📅 날짜 관리 API

### 날짜 정보 조회

#### `GET /api/v1/date-management/date-info`

특정 날짜의 상세 정보를 조회합니다.

**Query Parameters:**
- `date`: 조회할 날짜 (YYYY-MM-DD 형식)

**응답 예시:**
```json
{
  "success": true,
  "message": "날짜 정보 조회 완료",
  "data": {
    "date": "2025-05-03",
    "day_of_week": 5,
    "day_name": "토요일",
    "is_weekend": true,
    "is_holiday": true,
    "holiday_info": {
      "name": "헌법기념일",
      "name_en": "Constitution Memorial Day",
      "type": "national"
    },
    "season": "golden_week",
    "price_impact": "very_high",
    "special_periods": ["골든위크"],
    "recommendations": [
      "항공료 최고 성수기",
      "3개월 전 예약 권장",
      "대체 날짜 고려"
    ]
  }
}
```

### 기간별 날짜 정보

#### `GET /api/v1/date-management/period-info`

특정 기간의 날짜 정보를 조회합니다.

**Query Parameters:**
- `start_date`: 시작 날짜 (YYYY-MM-DD)
- `end_date`: 종료 날짜 (YYYY-MM-DD)

### 특별 기간 조회

#### `GET /api/v1/date-management/special-periods`

골든위크, 연말연시 등 특별 기간 정보를 조회합니다.

**Query Parameters:**
- `year`: 조회할 연도 (기본값: 현재 연도)

### 최적 여행 날짜 추천

#### `GET /api/v1/date-management/best-travel-dates`

가격과 날씨를 고려한 최적 여행 날짜를 추천합니다.

**Query Parameters:**
- `month`: 대상 월 (1-12)
- `duration`: 여행 기간 (기본값: 4일)
- `budget_level`: 예산 수준 (low, medium, high)

### 주말/공휴일 체크

#### `GET /api/v1/date-management/weekend-holiday-check`

특정 날짜가 주말이나 공휴일인지 확인합니다.

**Query Parameters:**
- `date`: 확인할 날짜 (YYYY-MM-DD)

### 연휴 정보

#### `GET /api/v1/date-management/long-weekends`

연도별 연휴 정보를 조회합니다.

**Query Parameters:**
- `year`: 조회할 연도 (기본값: 현재 연도)

### 시즌별 날짜

#### `GET /api/v1/date-management/seasonal-dates`

벚꽃, 단풍 등 시즌별 추천 날짜를 조회합니다.

**Query Parameters:**
- `season`: 시즌 (cherry_blossom, autumn_leaves, golden_week)
- `year`: 조회할 연도

### 가격 영향도 분석

#### `GET /api/v1/date-management/price-impact-analysis`

날짜별 가격 영향도를 분석합니다.

**Query Parameters:**
- `start_date`: 시작 날짜
- `end_date`: 종료 날짜

### 공휴일 캘린더

#### `GET /api/v1/date-management/holiday-calendar`

월별 공휴일 캘린더를 조회합니다.

**Query Parameters:**
- `year`: 연도
- `month`: 월 (1-12)

### 여행 패턴 분석

#### `GET /api/v1/date-management/travel-patterns`

한국인의 일본 여행 패턴을 분석합니다.

**Query Parameters:**
- `period`: 분석 기간 (monthly, quarterly, yearly)

### 대체 날짜 추천

#### `GET /api/v1/date-management/alternative-dates`

성수기 날짜의 대체 날짜를 추천합니다.

**Query Parameters:**
- `preferred_date`: 선호 날짜 (YYYY-MM-DD)
- `flexibility_days`: 유연성 기간 (일 단위)

### 예약 최적 타이밍

#### `GET /api/v1/date-management/booking-timing`

여행 날짜별 예약 최적 타이밍을 조회합니다.

**Query Parameters:**
- `travel_date`: 여행 날짜 (YYYY-MM-DD)
- `destination`: 목적지 (지역 ID)

### 날씨 정보

#### `GET /api/v1/date-management/weather-info`

특정 날짜의 일본 날씨 정보를 조회합니다.

**Query Parameters:**
- `date`: 조회할 날짜 (YYYY-MM-DD)
- `region`: 지역 (hokkaido, kanto, kansai 등)

### 이벤트 정보

#### `GET /api/v1/date-management/events`

특정 기간의 일본 이벤트 정보를 조회합니다.

**Query Parameters:**
- `start_date`: 시작 날짜
- `end_date`: 종료 날짜
- `region`: 지역 (선택적)

### 휴가 추천

#### `GET /api/v1/date-management/vacation-recommendations`

한국 직장인을 위한 휴가 추천을 제공합니다.

**Query Parameters:**
- `year`: 연도
- `vacation_days`: 사용 가능한 휴가 일수

## 💱 환율 API

### 현재 환율 조회

#### `GET /api/v1/llm/exchange-rates`

현재 환율 정보를 조회합니다.

**Query Parameters:**
- `currency_codes` (optional): 쉼표로 구분된 통화 코드 목록 (예: "USD,JPY,EUR")

**응답 예시:**
```json
{
  "success": true,
  "rates": [
    {
      "currency_code": "USD",
      "currency_name": "미국 달러",
      "base_rate": 1350.50,
      "buy_rate": 1360.00,
      "sell_rate": 1341.00,
      "send_rate": 1355.00,
      "receive_rate": 1346.00,
      "exchange_date": "20250715"
    },
    {
      "currency_code": "JPY",
      "currency_name": "일본 엔",
      "base_rate": 9.12,
      "buy_rate": 9.25,
      "sell_rate": 8.99,
      "send_rate": 9.15,
      "receive_rate": 9.05,
      "exchange_date": "20250715"
    }
  ],
  "updated_at": "2025-07-15T12:00:00Z",
  "source": "한국수출입은행"
}
```

### 과거 환율 조회

#### `GET /api/v1/llm/exchange-rates/historical`

특정 날짜의 과거 환율 정보를 조회합니다.

**Query Parameters:**
- `date` (required): 조회할 날짜 (YYYYMMDD 형식)
- `currency_codes` (optional): 쉼표로 구분된 통화 코드 목록

**응답 예시:**
```json
{
  "success": true,
  "rates": [
    {
      "currency_code": "USD",
      "currency_name": "미국 달러",
      "base_rate": 1345.20,
      "buy_rate": 1355.00,
      "sell_rate": 1335.40,
      "send_rate": 1350.00,
      "receive_rate": 1340.40,
      "exchange_date": "20250701"
    }
  ],
  "updated_at": "2025-07-15T12:00:00Z",
  "source": "한국수출입은행"
}
```

### 통화 변환

#### `POST /api/v1/llm/currency-conversion`

통화 변환을 수행합니다.

**Request Body:**
```json
{
  "amount": 500000,
  "from_currency": "KRW",
  "to_currency": "JPY"
}
```

**응답 예시:**
```json
{
  "success": true,
  "amount": 500000,
  "from_currency": "KRW",
  "to_currency": "JPY",
  "converted_amount": 45600.00,
  "exchange_rate": 0.0912,
  "converted_at": "2025-07-15T12:00:00Z",
  "rate_date": "20250715"
}
```

### 지원 통화 목록

#### `GET /api/v1/llm/exchange-rates/supported`

지원하는 통화 코드 목록을 조회합니다.

**응답 예시:**
```json
{
  "success": true,
  "supported_currencies": [
    "USD", "JPY", "EUR", "GBP", "CHF", "CAD", "AUD", "NZD",
    "SEK", "NOK", "DKK", "CNY", "HKD", "SGD", "THB", "MYR",
    "INR", "IDR", "PHP", "VND", "BRL", "RUB", "ZAR", "TRY"
  ],
  "total_count": 80
}
```

### 환율 캐시 통계

#### `GET /api/v1/llm/exchange-rates/cache-stats`

환율 캐시 시스템의 통계 정보를 조회합니다.

**응답 예시:**
```json
{
  "success": true,
  "cache_stats": {
    "total_entries": 25,
    "valid_entries": 23,
    "cache_hit_ratio": 0.92,
    "default_ttl": 3600
  }
}
```

## 💾 캐시 관리 API

### 캐시 상태 조회

#### `GET /api/v1/cache/status`

캐시 시스템의 상태와 성능을 확인합니다.

**응답 예시:**
```json
{
  "success": true,
  "message": "캐시 상태 조회 완료",
  "data": {
    "cache_type": "redis",
    "status": "healthy",
    "redis_version": "7.0.5",
    "total_keys": 150,
    "active_keys": 142,
    "expired_keys": 8,
    "memory_usage": {
      "used_memory": "2.5MB",
      "used_memory_peak": "3.1MB",
      "memory_fragmentation_ratio": 1.1
    },
    "uptime_seconds": 86400,
    "last_updated": "2025-07-06T12:00:00Z"
  }
}
```

### 캐시 통계 조회

#### `GET /api/v1/cache/statistics`

캐시 히트율 및 성능 통계를 조회합니다.

**응답 예시:**
```json
{
  "success": true,
  "message": "캐시 통계 조회 완료",
  "data": {
    "cache_hit_rate": 85.6,
    "total_requests": 1250,
    "cache_hits": 1070,
    "cache_misses": 180,
    "avg_response_time": 45.2
  }
}
```

### 캐시 갱신 (관리자용)

#### `POST /api/v1/cache/refresh`

캐시를 수동으로 갱신합니다.

**Request Body:**
```json
{
  "regions": ["hokkaido", "kanto"],
  "force_update": false,
  "origin": "ICN"
}
```

**응답 예시:**
```json
{
  "success": true,
  "message": "캐시 갱신 완료",
  "data": {
    "refreshed_regions": ["hokkaido", "kanto"],
    "total_updated_keys": 25,
    "refresh_time": "2025-07-06T12:00:00Z"
  }
}
```

### 캐시 키 목록 조회

#### `GET /api/v1/cache/keys`

현재 캐시에 저장된 모든 키를 조회합니다.

**Query Parameters:**
- `pattern` (optional): 검색 패턴 (예: "monthly_*")
- `limit` (optional): 결과 수 제한 (기본값: 100)

**응답 예시:**
```json
{
  "success": true,
  "message": "캐시 키 목록 조회 완료",
  "data": {
    "keys": [
      "monthly_cheapest:ICN:2025:07",
      "monthly_cheapest:ICN:2025:08",
      "regions_lowest_prices:ICN:4",
      "flight_search:ICN:NRT:2025-08-15"
    ],
    "total_count": 156,
    "pattern_matches": 4
  }
}
```

### 캐시 정리

#### `POST /api/v1/cache/cleanup`

만료된 캐시를 정리합니다.

**응답 예시:**
```json
{
  "success": true,
  "message": "캐시 정리 완료",
  "data": {
    "cleaned_keys": 23,
    "freed_memory": "1.2MB",
    "cleanup_time": "2025-07-06T12:00:00Z"
  }
}
```

### 캐시 워밍업

#### `POST /api/v1/cache/warmup`

주요 캐시를 미리 로드합니다.

**Request Body:**
```json
{
  "regions": ["all"],
  "months": ["current", "next"],
  "origins": ["ICN"]
}
```

**응답 예시:**
```json
{
  "success": true,
  "message": "캐시 워밍업 완료",
  "data": {
    "warmed_keys": 45,
    "warmup_time": "2025-07-06T12:00:00Z",
    "estimated_hits": 89
  }
}
```

## 📊 응답 형식

### 표준 응답 구조

모든 API는 다음과 같은 일관된 응답 형식을 사용합니다:

```json
{
  "success": boolean,
  "message": string,
  "data": object | array,
  "meta": object (optional),
  "timestamp": string (ISO 8601)
}
```

### 성공 응답

```json
{
  "success": true,
  "message": "요청 처리 완료",
  "data": {
    // 실제 데이터
  },
  "meta": {
    "count": 10,
    "page": 1,
    "from_cache": true
  },
  "timestamp": "2025-07-06T12:00:00Z"
}
```

### 실패 응답

```json
{
  "success": false,
  "message": "요청 처리 실패",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "잘못된 요청 데이터",
    "details": "IATA 코드는 3자리여야 합니다"
  },
  "timestamp": "2025-07-06T12:00:00Z"
}
```

## ❌ 에러 코드

### HTTP 상태 코드

- `200` - 성공
- `400` - 잘못된 요청 (Bad Request)
- `404` - 리소스 없음 (Not Found)
- `422` - 검증 오류 (Unprocessable Entity)
- `500` - 서버 내부 오류 (Internal Server Error)
- `503` - 서비스 이용 불가 (Service Unavailable)

### 애플리케이션 에러 코드

```json
{
  "VALIDATION_ERROR": "요청 데이터 검증 실패",
  "AMADEUS_API_ERROR": "Amadeus API 호출 실패",
  "CACHE_ERROR": "캐시 시스템 오류",
  "NOT_FOUND": "요청한 리소스를 찾을 수 없음",
  "RATE_LIMIT_EXCEEDED": "API 호출 한도 초과",
  "INTERNAL_ERROR": "서버 내부 오류"
}
```

### 에러 응답 예시

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "잘못된 IATA 코드입니다",
    "details": "IATA 코드는 3자리 영문자여야 합니다. 입력값: 'ICNN'"
  },
  "suggestions": [
    "올바른 IATA 코드를 확인하세요",
    "공항 검색 API를 사용해보세요: /api/v1/utils/airports/search"
  ],
  "timestamp": "2025-07-06T12:00:00Z"
}
```

## 🔍 API 사용 예시

### 메인 화면 데이터 로드

```bash
# 1. 지역별 최저가 조회 (메인 화면)
curl -X GET "http://localhost:8000/api/v1/regions/lowest-prices"

# 2. 날짜 정보 확인
curl -X GET "http://localhost:8000/api/v1/utils/date-info?date=2025-08-15"

# 3. 환율 정보 조회
curl -X GET "http://localhost:8000/api/v1/utils/exchange-rate"
```

### 항공편 검색 플로우

```bash
# 1. 공항 검색 (자동완성)
curl -X GET "http://localhost:8000/api/v1/utils/airports/search?query=삿포로"

# 2. 4일 여행 항공편 검색
curl -X POST "http://localhost:8000/api/v1/flights/search-by-duration" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "ICN",
    "destination": "CTS",
    "departure_date": "2025-08-15",
    "duration_days": 4,
    "adults": 1
  }'

# 3. 최저가 날짜 검색 (유연한 날짜)
curl -X POST "http://localhost:8000/api/v1/flights/cheapest-dates" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "ICN",
    "destination": "CTS",
    "departure_date": "2025-08-15",
    "duration": 4,
    "flexibility_days": 7
  }'
```

### 관리자 기능

```bash
# 캐시 상태 확인
curl -X GET "http://localhost:8000/api/v1/cache/status"

# 시스템 전체 상태 확인
curl -X GET "http://localhost:8000/health"

# 캐시 갱신
curl -X POST "http://localhost:8000/api/v1/cache/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "force_update": true,
    "origin": "ICN"
  }'
```

## 🚀 성능 정보

### 응답 시간

| API 카테고리 | 평균 응답 시간 | 캐시 히트 시 | 설명 |
|-------------|-------------|-------------|------|
| 지역 최저가 | ~200ms | ~45ms | 메인 화면용 핵심 API |
| 항공편 검색 | ~2-3초 | ~150ms | Amadeus API 호출 포함 |
| 월별 분석 | ~500ms | ~80ms | 복잡한 데이터 분석 |
| 유틸리티 | ~100ms | ~20ms | 간단한 정보 조회 |
| 캐시 관리 | ~50ms | N/A | 캐시 시스템 직접 조회 |

### 캐시 효율성

- **전체 캐시 히트율**: 85%+
- **메인 API 히트율**: 90%+
- **캐시 만료 시간**: 1-12시간 (데이터 유형별)
- **캐시 갱신 주기**: 자동 스케줄링

### 동시성 처리

- **FastAPI 비동기 처리**: 100+ 동시 요청
- **Redis 연결 풀**: 최대 20개 연결
- **Celery 백그라운드 작업**: 별도 워커 프로세스

### 안정성

- **Redis 장애 대응**: 자동 메모리 캐시 전환
- **Amadeus API 장애**: 더미 데이터 제공 옵션
- **재시도 로직**: 3회 자동 재시도
- **로깅**: 구조화된 로그 시스템

---

## 🔧 개발자 정보

### 테스트 환경

```bash
# 개발 서버 시작
uvicorn app.main:app --reload

# 테스트 실행
pytest tests/ -v

# API 문서 확인
open http://localhost:8000/docs
```

### 모니터링

- **헬스체크**: `/health`
- **시스템 상태**: `/api/v1/status`
- **캐시 상태**: `/api/v1/cache/status`
- **API 문서**: `/docs`

---

**🚀 Happy API Development!**

더 자세한 정보는 [대화형 API 문서](/docs)를 참조하세요.

**📞 문의 및 지원**
- **GitHub Issues**: [프로젝트 이슈](https://github.com/Soobean/flight_recommand/issues)
- **API 문서**: [Swagger UI](http://localhost:8000/docs)
- **프로젝트 문서**: [README.md](README.md)
