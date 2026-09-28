from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.services.llm.llm_service import (
    FlightAnalysis,
    LLMService,
    PriceAlert,
    PriceTrend,
    RouteAnalysis,
    TrendDirection,
)


class TestLLMService:
    """LLM 서비스 테스트 클래스"""

    @pytest.fixture
    def llm_service(self):
        """LLM 서비스 인스턴스 픽스처"""
        with patch("app.services.llm.llm_service.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.LLM_MODEL = "gpt-4o-mini"
            mock_settings.LLM_MAX_TOKENS = 4000
            mock_settings.LLM_TEMPERATURE = 0.7
            mock_settings.OPENAI_API_KEY = None
            return LLMService()

    @pytest.fixture
    def sample_flight_data(self):
        """샘플 항공편 데이터"""
        return [
            {
                "id": "flight1",
                "price": {"total": 500.0},
                "itineraries": [
                    {
                        "duration": "PT3H30M",
                        "segments": [
                            {
                                "departure": {"iataCode": "ICN"},
                                "arrival": {"iataCode": "NRT"},
                            }
                        ],
                    }
                ],
            },
            {
                "id": "flight2",
                "price": {"total": 450.0},
                "itineraries": [
                    {
                        "duration": "PT5H15M",
                        "segments": [
                            {
                                "departure": {"iataCode": "ICN"},
                                "arrival": {"iataCode": "BKK"},
                            },
                            {
                                "departure": {"iataCode": "BKK"},
                                "arrival": {"iataCode": "NRT"},
                            },
                        ],
                    }
                ],
            },
        ]

    def test_llm_service_initialization(self, llm_service):
        """LLM 서비스 초기화 테스트"""
        assert llm_service.cache_service.get_cache("absent") is None
        assert llm_service.cache_ttl == 300
        assert llm_service.price_history == {}
        assert llm_service.price_alerts == []

    @pytest.mark.asyncio
    async def test_dummy_analysis(self, llm_service, sample_flight_data):
        """더미 분석 테스트"""
        result = await llm_service._get_dummy_analysis(sample_flight_data)

        assert result["success"] is True
        assert len(result["results"]) == 2
        assert result["model_used"] == "dummy"
        assert result["results"][0]["flight_id"] == "flight1"
        assert result["results"][0]["efficiency_score"] == 75

    @pytest.mark.asyncio
    async def test_dummy_efficiency_score(self, llm_service, sample_flight_data):
        """더미 효율성 점수 테스트"""
        result = await llm_service._get_dummy_efficiency_score(sample_flight_data[0])

        assert result["flight_id"] == "flight1"
        assert result["efficiency_score"] == 75
        assert result["model_used"] == "dummy"
        assert "breakdown" in result

    def test_fallback_analysis(self, llm_service, sample_flight_data):
        """폴백 분석 테스트"""
        result = llm_service._get_fallback_analysis(sample_flight_data[0])

        assert result["flight_id"] == "flight1"
        assert result["efficiency_score"] == 50
        assert result["model_used"] == "fallback"
        assert "분석 중 오류가 발생했습니다" in result["summary"]

    def test_cache_functionality(self, llm_service, sample_flight_data):
        """캐시 기능 테스트"""
        cache_key = llm_service._get_cache_key("test_query", sample_flight_data)
        test_data = {"test": "data"}

        # 캐시 저장
        llm_service._set_cache(cache_key, test_data)

        # 캐시 조회
        cached_data = llm_service._get_from_cache(cache_key)
        assert cached_data == test_data

        # 캐시 통계
        stats = llm_service.get_cache_stats()
        assert stats["cache_backend"] == "CacheService"

    def test_price_history_update(self, llm_service, sample_flight_data):
        """가격 히스토리 업데이트 테스트"""
        llm_service._update_price_history(sample_flight_data)

        assert "flight1" in llm_service.price_history
        assert "flight2" in llm_service.price_history
        assert len(llm_service.price_history["flight1"]) == 1
        assert llm_service.price_history["flight1"][0]["price"] == 500.0

    def test_price_trends_analysis(self, llm_service, sample_flight_data):
        """가격 트렌드 분석 테스트"""
        # 가격 히스토리 추가
        llm_service._update_price_history(sample_flight_data)

        # 트렌드 분석
        trends = llm_service._analyze_price_trends(sample_flight_data)

        assert len(trends) == 2
        assert isinstance(trends[0], PriceTrend)
        assert trends[0].current_price == 500.0
        assert trends[0].trend_direction == TrendDirection.STABLE

    def test_route_analysis(self, llm_service, sample_flight_data):
        """경로 분석 테스트"""
        routes = llm_service._analyze_routes(sample_flight_data)

        assert len(routes) == 2
        assert isinstance(routes[0], RouteAnalysis)
        assert routes[0].route == "ICN -> NRT"
        assert routes[0].stops == 0
        assert routes[1].stops == 1

    def test_parse_duration(self, llm_service):
        """소요시간 파싱 테스트"""
        assert llm_service._parse_duration("PT3H30M") == 210  # 3시간 30분 = 210분
        assert llm_service._parse_duration("PT2H") == 120  # 2시간 = 120분
        assert llm_service._parse_duration("PT45M") == 45  # 45분
        assert llm_service._parse_duration("INVALID") == 0  # 잘못된 형식

    def test_price_alert_creation(self, llm_service):
        """가격 알림 생성 테스트"""
        alert = llm_service.create_price_alert(
            flight_id="flight1",
            threshold_price=400.0,
            user_id="user123",
            alert_type="price_drop",
        )

        assert isinstance(alert, PriceAlert)
        assert alert.flight_id == "flight1"
        assert alert.threshold_price == 400.0
        assert alert.user_id == "user123"
        assert alert.is_active is True
        assert len(llm_service.price_alerts) == 1

    def test_price_alert_check(self, llm_service, sample_flight_data):
        """가격 알림 확인 테스트"""
        # 알림 설정 (현재 가격 500보다 높은 임계값)
        llm_service.create_price_alert(
            flight_id="flight1", threshold_price=600.0, user_id="user123"
        )

        # 가격 하락 시뮬레이션
        sample_flight_data[0]["price"]["total"] = 550.0

        triggered_alerts = llm_service.check_price_alerts(sample_flight_data)
        assert len(triggered_alerts) == 1
        assert triggered_alerts[0]["alert"].flight_id == "flight1"
        assert "가격이" in triggered_alerts[0]["message"]

    @pytest.mark.asyncio
    async def test_advanced_analysis_integration(self, llm_service, sample_flight_data):
        """고급 분석 통합 테스트"""
        # LLM 클라이언트가 없는 경우 테스트
        llm_service.client = None

        result = await llm_service.analyze_flights_advanced(
            "test query", sample_flight_data
        )

        assert isinstance(result, FlightAnalysis)
        assert len(result.price_trends) == 2
        assert len(result.route_analysis) == 2
        assert result.best_deal is not None
        assert isinstance(result.recommendations, list)

    def test_cache_expiration(self, llm_service):
        """캐시 만료 테스트"""
        cache_key = "test_key"
        test_data = {"test": "data"}

        # 캐시 저장
        llm_service._set_cache(cache_key, test_data)

        # 시간 조작 (TTL 초과)
        old_timestamp = datetime.now() - timedelta(seconds=llm_service.cache_ttl + 1)
        llm_service.cache_service._memory_cache[f"llm:{cache_key}"][
            "expires_at"
        ] = old_timestamp.isoformat()

        # 만료된 캐시 조회
        cached_data = llm_service._get_from_cache(cache_key)
        assert cached_data is None
        assert llm_service.cache_service.get_cache(f"llm:{cache_key}") is None

    def test_price_history_cleanup(self, llm_service, sample_flight_data):
        """가격 히스토리 정리 테스트"""
        # 오래된 데이터 추가
        old_timestamp = datetime.now() - timedelta(days=35)
        llm_service.price_history["flight1"] = [
            {"price": 600.0, "timestamp": old_timestamp}
        ]

        # 새 데이터 추가 (정리 트리거)
        llm_service._update_price_history(sample_flight_data)

        # 30일 이상 된 데이터는 제거됨
        assert len(llm_service.price_history["flight1"]) == 1
        assert llm_service.price_history["flight1"][0]["price"] == 500.0

    def test_trend_direction_calculation(self, llm_service, sample_flight_data):
        """트렌드 방향 계산 테스트"""
        # 가격 히스토리 설정 (상승 트렌드)
        llm_service.price_history["flight1"] = [
            {"price": 400.0, "timestamp": datetime.now() - timedelta(days=5)},
            {"price": 450.0, "timestamp": datetime.now() - timedelta(days=3)},
            {"price": 500.0, "timestamp": datetime.now() - timedelta(days=1)},
        ]

        # 현재 가격을 더 높게 설정
        sample_flight_data[0]["price"]["total"] = 550.0

        trends = llm_service._analyze_price_trends(sample_flight_data)

        assert trends[0].trend_direction == TrendDirection.UP
        assert trends[0].price_change_percent > 5

    @pytest.mark.asyncio
    async def test_error_handling(self, llm_service, sample_flight_data):
        """오류 처리 테스트"""
        # 잘못된 항공편 데이터
        invalid_data = [{"invalid": "data"}]

        # 오류가 발생해도 기본값 반환
        result = await llm_service.analyze_flights_advanced("test", invalid_data)

        assert isinstance(result, FlightAnalysis)
        assert len(result.price_trends) == 1
        assert result.price_trends[0].current_price == 0
