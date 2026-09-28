# 가격 예측 고도화 계획

**지능형 일본 항공권 분석기 -가격 예측 상세 로드맵**

---

##  현재 상태

###  완료된 기능 (Phase 1-2)
- **Phase 1**: 기본 항공편 검색 및 지역별 최저가 조회
- **Phase 2**: LLM 기반 분석 및 환율 서비스
- **Phase 3 초기**: 기본 RandomForest 가격 예측 모델

###  Phase 3 목표
**ML 기반 지능형 가격 예측 시스템 구축**

---

##  단계별 고도화 계획

###  **Stage 1: 실제 데이터 수집 시스템** (우선순위: 🔴 HIGH)

####  데이터 수집 인프라
- **Amadeus API 기반 가격 히스토리 수집**
  - 일별/주별 가격 수집 스케줄러
  - 지역별, 노선별 세분화 수집
  - API 호출 최적화 및 비용 관리

- **데이터베이스 설계**
  - PostgreSQL 스키마 설계
  - 시계열 데이터 최적화 (TimescaleDB 고려)
  - 인덱싱 및 파티셔닝 전략

- **데이터 품질 관리**
  - 중복 제거 및 이상치 탐지
  - 결측값 처리 로직
  - 데이터 유효성 검증

####  구현 파일
```
backend/app/
├── services/
│   ├── data_collection_service.py
│   ├── data_quality_service.py
│   └── historical_data_service.py
├── models/
│   ├── price_history.py
│   └── data_quality_metrics.py
├── tasks/
│   ├── price_collection_task.py
│   └── data_cleanup_task.py
└── api/v1/
    └── data_collection.py
```

####  성공 지표
- 90일 이상 연속 데이터 수집
- 데이터 품질 점수 95% 이상
- API 호출 비용 최적화 달성

---

###  **Stage 2: 고급 ML 모델 구현** (우선순위: 🟡 MEDIUM)

####  모델 다양화 (바뀔 수도 있음)
- **XGBoost 모델**
  - 그래디언트 부스팅 기반 예측
  - 하이퍼파라미터 최적화
  - Feature importance 분석

- **LightGBM 모델**
  - 빠른 훈련 속도
  - 메모리 효율성
  - 범주형 변수 처리

- **LSTM 시계열 모델**
  - 장기 의존성 학습
  - 시계열 패턴 인식
  - 다변량 시계열 예측

####  앙상블 시스템
- **모델 결합 전략**
  - Voting Classifier
  - Stacking 앙상블
  - 동적 가중치 조정

- **모델 선택 로직**
  - 성능 기반 자동 선택
  - 시나리오별 최적 모델
  - 실시간 성능 모니터링

####  구현 파일
```
backend/app/
├── services/
│   ├── advanced_prediction_service.py
│   ├── ensemble_service.py
│   └── model_selection_service.py
├── models/
│   ├── xgboost_model.py
│   ├── lstm_model.py
│   └── ensemble_model.py
└── utils/
    ├── model_utils.py
    └── hyperparameter_tuning.py
```

####  성공 지표
- 예측 정확도 85% 이상
- 모델 응답 시간 2초 이내
- 3개 이상 모델 성공적 운영

---

###  **Stage 3: Feature Engineering 파이프라인** (우선순위: 🟡 MEDIUM)

####  시계열 특성 엔지니어링
- **기본 시계열 특성**
  - 이동평균 (7일, 30일, 90일)
  - 변동성 지표 (표준편차, 변동계수)
  - 추세 및 계절성 분해

- **고급 시계열 특성**
  - 자기회귀 특성 (lag features)
  - 지수평활법 기반 특성
  - 푸리에 변환 기반 주기성 특성

####  외부 요인 통합
- **거시경제 지표**
  - 유가 변동성
  - 환율 변동성
  - 경제 지표 (GDP, 인플레이션)

- **이벤트 기반 특성**
  - 일본 이벤트 캘린더
  - 한국 연휴 영향도
  - 코로나 등 특수 상황 지표

####  구현 파일
```
backend/app/
├── services/
│   ├── feature_engineering_service.py
│   ├── external_data_service.py
│   └── time_series_feature_service.py
├── pipelines/
│   ├── feature_pipeline.py
│   └── preprocessing_pipeline.py
└── utils/
    ├── feature_utils.py
    └── time_series_utils.py
```

####  성공 지표
- 50+ 특성 변수 생성
- 특성 중요도 분석 완료
- 전처리 파이프라인 안정화

---

### **Stage 4: MLOps 및 모니터링** (우선순위: 🟡 MEDIUM)

####  성능 모니터링
- **MLflow 통합**
  - 실험 추적 시스템
  - 모델 버전 관리
  - 메트릭 시각화

- **실시간 모니터링**
  - 예측 정확도 추적
  - 모델 드리프트 감지
  - 성능 저하 알림

####  A/B 테스트 시스템
- **모델 비교 테스트**
  - 트래픽 분할 시스템
  - 성능 지표 비교
  - 통계적 유의성 검증

####  구현 파일
```
backend/app/
├── services/
│   ├── model_monitoring_service.py
│   ├── ab_testing_service.py
│   └── mlflow_service.py
├── monitoring/
│   ├── performance_tracker.py
│   ├── drift_detector.py
│   └── alert_manager.py
└── api/v1/
    └── monitoring.py
```

####  성공 지표
- 모델 성능 실시간 추적
- 드리프트 감지 시스템 구축
- A/B 테스트 자동화

---

### **Stage 5: 자동화된 재훈련 시스템** (우선순위: 🟢 LOW)

####  자동 재훈련 파이프라인
- **트리거 기반 재훈련**
  - 성능 저하 감지 시
  - 새로운 데이터 임계치 도달 시
  - 정기적 스케줄 재훈련

- **모델 배포 자동화**
  - 카나리 배포 시스템
  - 롤백 메커니즘
  - 무중단 배포

####  구현 파일
```
backend/app/
├── services/
│   ├── auto_retrain_service.py
│   ├── model_deployment_service.py
│   └── rollback_service.py
├── tasks/
│   ├── retrain_task.py
│   └── deployment_task.py
└── utils/
    └── deployment_utils.py
```

####  성공 지표
- 자동 재훈련 시스템 구축
- 무중단 배포 달성
- 모델 성능 지속적 개선

---

## 기술 스택 확장

### 현재 → 확장 후

| 구분 | 현재 | 확장 후 |
|------|------|---------|
| **ML 라이브러리** | scikit-learn | scikit-learn + XGBoost + LightGBM + TensorFlow |
| **데이터베이스** | Redis (캐시) | PostgreSQL + TimescaleDB + Redis |
| **모니터링** | 기본 로깅 | MLflow + Prometheus + Grafana |
| **스케줄링** | 없음 | Celery + Redis + Cron |
| **배포** | 수동 | Docker + CI/CD + 카나리 배포 |

### 새로운 의존성

```bash
# ML 라이브러리
pip install xgboost lightgbm tensorflow

# 데이터베이스
pip install psycopg2-binary sqlalchemy timescaledb

# MLOps
pip install mlflow prometheus-client

# 스케줄링
pip install celery redis

# 모니터링
pip install grafana-api
```

---

##  성과 지표 (KPI)

### 기술적 지표
- **예측 정확도**: 현재 70% → 목표 85%
- **응답 시간**: 현재 3초 → 목표 1초
- **데이터 커버리지**: 현재 더미 → 목표 실제 90일 이상

### 비즈니스 지표
- **사용자 만족도**: 예측 신뢰도 90% 이상
- **비용 절감**: API 호출 비용 30% 절감
- **서비스 안정성**: 99.9% 업타임

---

##  프로젝트 구조 (완성 후)

```
backend/
├── app/
│   ├── api/v1/
│   │   ├── prediction.py          # 기본 예측 API
│   │   ├── advanced_prediction.py # 고급 예측 API
│   │   ├── data_collection.py     # 데이터 수집 API
│   │   └── monitoring.py          # 모니터링 API
│   ├── services/
│   │   ├── price_prediction_service.py      # 기본 예측
│   │   ├── advanced_prediction_service.py   # 고급 예측
│   │   ├── data_collection_service.py       # 데이터 수집
│   │   ├── feature_engineering_service.py   # 특성 엔지니어링
│   │   ├── model_monitoring_service.py      # 모델 모니터링
│   │   └── auto_retrain_service.py          # 자동 재훈련
│   ├── models/
│   │   ├── price_history.py        # 가격 히스토리 모델
│   │   ├── xgboost_model.py        # XGBoost 모델
│   │   ├── lstm_model.py           # LSTM 모델
│   │   └── ensemble_model.py       # 앙상블 모델
│   ├── pipelines/
│   │   ├── feature_pipeline.py     # 특성 파이프라인
│   │   └── training_pipeline.py    # 훈련 파이프라인
│   └── tasks/
│       ├── price_collection_task.py # 가격 수집 태스크
│       └── retrain_task.py          # 재훈련 태스크
├── tests/
│   ├── test_advanced_prediction.py
│   ├── test_feature_engineering.py
│   └── test_model_monitoring.py
├── mlflow/                          # MLflow 관련 파일
├── docker-compose.yml              # 전체 서비스 구성
└── requirements-ml.txt             # ML 의존성
```

---

## 시작하기

### 1단계: 환경 설정
```bash
# ML 의존성 설치
pip install -r requirements-ml.txt

# 데이터베이스 설정
docker-compose up -d postgres timescaledb

# MLflow 서버 시작
mlflow server --host 0.0.0.0 --port 5000
```

### 2단계: 첫 번째 단계 선택
각 단계는 독립적으로 진행 가능하며, 우선순위에 따라 선택하여 구현합니다.

---

## 단계 별

1. **Stage 1**: 실제 데이터 수집 시스템 (권장)
2. **Stage 2**: 고급 ML 모델 구현
3. **Stage 3**: Feature Engineering 파이프라인
4. **Stage 4**: MLOps 및 모니터링
5. **Stage 5**: 자동화된 재훈련 시스템

---

**업데이트 일자**: 2025-07-15
**상태**: 계획 완료, 구현 대기중
