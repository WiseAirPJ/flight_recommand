"""
새로운 DateService 테스트
"""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.services.date_service import DateService
from app.utils.date_calculator import DateCalculator


class TestNewDateService:
    """새로운 DateService 테스트 클래스"""

    @pytest.fixture
    def mock_holiday_cache_service(self):
        """Mock HolidayCacheService"""
        with patch("app.services.date_service.HolidayCacheService") as mock:
            service = AsyncMock()
            service.get_holiday_by_date.return_value = None
            service.get_holidays.return_value = [
                {
                    "date": "2025-01-01",
                    "name": "元日",
                    "name_en": "New Year's Day",
                    "season": "winter_holiday",
                    "price_impact": "very_high",
                    "description": "연말연시 성수기",
                }
            ]
            service.get_holidays_in_range.return_value = []
            service.refresh_cache.return_value = True
            service.get_cache_stats.return_value = {
                "years_cached": [2025],
                "total_holidays_cached": 15,
            }
            mock.return_value = service
            yield service

    @pytest.fixture
    def date_service(self, mock_holiday_cache_service):
        """DateService 인스턴스"""
        return DateService()

    @pytest.mark.asyncio
    async def test_get_date_info_regular_date(
        self, date_service, mock_holiday_cache_service
    ):
        """일반 날짜 정보 조회 테스트"""
        # Mock: 공휴일이 아닌 날짜
        mock_holiday_cache_service.get_holiday_by_date.return_value = None

        result = await date_service.get_date_info("2025-02-15")

        assert result["date"] == "2025-02-15"
        assert result["is_holiday"] is False
        assert "season" in result
        assert "price_impact" in result
        mock_holiday_cache_service.get_holiday_by_date.assert_called_once_with(
            "2025-02-15"
        )

    @pytest.mark.asyncio
    async def test_get_date_info_holiday(
        self, date_service, mock_holiday_cache_service
    ):
        """공휴일 정보 조회 테스트"""
        # Mock: 공휴일 반환
        holiday_data = {
            "name": "元日",
            "name_en": "New Year's Day",
            "season": "winter_holiday",
            "price_impact": "very_high",
            "description": "연말연시 성수기",
        }
        mock_holiday_cache_service.get_holiday_by_date.return_value = holiday_data

        result = await date_service.get_date_info("2025-01-01")

        assert result["is_holiday"] is True
        assert result["holiday_name"] == "元日"
        assert result["holiday_name_en"] == "New Year's Day"
        assert result["price_impact"] == "very_high"

    @pytest.mark.asyncio
    async def test_get_year_holidays(self, date_service, mock_holiday_cache_service):
        """연도별 공휴일 조회 테스트"""
        holidays = await date_service.get_year_holidays(2025)

        assert len(holidays) == 1
        assert holidays[0]["date"] == "2025-01-01"
        mock_holiday_cache_service.get_holidays.assert_called_once_with(2025)

    @pytest.mark.asyncio
    async def test_find_cheapest_months(self, date_service, mock_holiday_cache_service):
        """가장 저렴한 월 찾기 테스트"""
        # Mock: 2월에 공휴일 없음, 1월에 1개
        mock_holiday_cache_service.get_holidays.return_value = [
            {"date": "2025-01-01", "name": "元日"}
        ]

        result = await date_service.find_cheapest_months(2025)

        assert len(result) > 0
        assert all("month" in item for item in result)
        assert all("score" in item for item in result)
        # 점수 낮은 순으로 정렬되어 있는지 확인
        scores = [item["score"] for item in result]
        assert scores == sorted(scores)

    @pytest.mark.asyncio
    async def test_is_peak_season(self, date_service, mock_holiday_cache_service):
        """성수기 여부 확인 테스트"""
        # Mock: 높은 가격 영향도 반환
        holiday_data = {
            "name": "元日",
            "season": "winter_holiday",
            "price_impact": "very_high",
            "description": "연말연시 성수기",
        }
        mock_holiday_cache_service.get_holiday_by_date.return_value = holiday_data

        result = await date_service.is_peak_season("2025-01-01")
        assert result is True

        # 비성수기 테스트
        mock_holiday_cache_service.get_holiday_by_date.return_value = None
        result = await date_service.is_peak_season("2025-02-15")
        # 2월은 일반적으로 비수기
        assert result is False

    @pytest.mark.asyncio
    async def test_get_month_characteristics(self, date_service):
        """월별 특성 정보 조회 테스트"""
        result = await date_service.get_month_characteristics(4)  # 4월

        assert "weather" in result
        assert "crowds" in result
        assert "price_level" in result
        assert "events" in result

    @pytest.mark.asyncio
    async def test_get_holidays_in_range(
        self, date_service, mock_holiday_cache_service
    ):
        """기간별 공휴일 조회 테스트"""
        range_holidays = [
            {"date": "2025-01-01", "name": "元日"},
            {"date": "2025-01-13", "name": "成人の日"},
        ]
        mock_holiday_cache_service.get_holidays_in_range.return_value = range_holidays

        result = await date_service.get_holidays_in_range("2025-01-01", "2025-01-31")

        assert len(result) == 2
        mock_holiday_cache_service.get_holidays_in_range.assert_called_once_with(
            "2025-01-01", "2025-01-31"
        )

    @pytest.mark.asyncio
    async def test_get_cheapest_periods(self, date_service):
        """가장 저렴한 여행 기간 찾기 테스트"""
        result = await date_service.get_cheapest_periods(2025, 7)

        assert isinstance(result, list)
        # 결과가 있다면 필수 필드 확인
        if result:
            assert all("start_date" in item for item in result)
            assert all("end_date" in item for item in result)
            assert all("duration_days" in item for item in result)

    @pytest.mark.asyncio
    async def test_refresh_holiday_cache(
        self, date_service, mock_holiday_cache_service
    ):
        """공휴일 캐시 새로고침 테스트"""
        result = await date_service.refresh_holiday_cache(2025)

        assert result is True
        mock_holiday_cache_service.refresh_cache.assert_called_once_with(2025)

    @pytest.mark.asyncio
    async def test_get_service_status(self, date_service, mock_holiday_cache_service):
        """서비스 상태 정보 테스트"""
        result = await date_service.get_service_status()

        assert result["service"] == "DateService"
        assert result["version"] == "2.0 (API-based)"
        assert result["status"] == "healthy"
        assert result["features"]["external_api"] is True
        assert result["features"]["hardcoded_data"] is False

    @pytest.mark.asyncio
    async def test_price_impact_explanation(self, date_service):
        """가격 영향도 설명 테스트"""
        result = await date_service.get_price_impact_explanation("very_high")
        assert "50-100%" in result

        result = await date_service.get_price_impact_explanation("unknown")
        assert result == "정보 없음"

    @pytest.mark.asyncio
    async def test_error_handling(self, date_service, mock_holiday_cache_service):
        """에러 처리 테스트"""
        # Mock에서 예외 발생시키기
        mock_holiday_cache_service.get_holiday_by_date.side_effect = Exception(
            "API Error"
        )

        result = await date_service.get_date_info("2025-01-01")
        assert "error" in result


class TestDateCalculator:
    """DateCalculator 테스트 클래스"""

    def test_get_season_info_spring(self):
        """봄 시즌 정보 테스트"""
        test_date = date(2025, 4, 15)  # 4월 15일
        result = DateCalculator.get_season_info(test_date)

        assert result["season"] == "spring"
        assert result["price_impact"] == "very_high"  # 벚꽃 절정기

    def test_get_season_info_golden_week(self):
        """골든위크 기간 테스트"""
        test_date = date(2025, 5, 3)  # 5월 3일
        result = DateCalculator.get_season_info(test_date)

        assert result["season"] == "golden_week"
        assert result["price_impact"] == "very_high"

    def test_get_season_info_winter(self):
        """겨울 시즌 정보 테스트"""
        test_date = date(2025, 2, 15)  # 2월 15일
        result = DateCalculator.get_season_info(test_date)

        assert result["season"] == "winter"
        assert result["price_impact"] == "low"

    def test_get_month_characteristics(self):
        """월별 특성 정보 테스트"""
        result = DateCalculator.get_month_characteristics(4)  # 4월

        assert "벚꽃 절정" in result["events"]
        assert result["crowds"] == "최고"
        assert result["price_level"] == "최고"
        assert "벚꽃 구경" in result["recommended_activities"]

    def test_find_cheapest_periods(self):
        """가장 저렴한 기간 찾기 테스트"""
        result = DateCalculator.find_cheapest_periods(2025, 7)

        assert isinstance(result, list)
        assert len(result) <= 20  # 최대 20개 반환

        # 결과가 있다면 점수 순으로 정렬되어 있는지 확인
        if len(result) > 1:
            scores = [item["avg_score"] for item in result]
            assert scores == sorted(scores)


class TestHolidayAPIClient:
    """HolidayAPIClient 테스트 (기본적인 기능만)"""

    @pytest.fixture
    def api_client(self):
        from app.services.holiday_api_client import HolidayAPIClient

        return HolidayAPIClient()

    def test_translate_holiday_name(self, api_client):
        """공휴일명 번역 테스트"""
        result = api_client._translate_holiday_name("元日")
        assert result == "New Year's Day"

        result = api_client._translate_holiday_name("Unknown Holiday")
        assert result == "Unknown Holiday"

    def test_determine_season(self, api_client):
        """시즌 결정 테스트"""
        # 골든위크
        test_date = date(2025, 5, 3)
        result = api_client._determine_season(test_date)
        assert result == "golden_week"

        # 일반 봄
        test_date = date(2025, 3, 15)
        result = api_client._determine_season(test_date)
        assert result == "spring"

    def test_calculate_price_impact(self, api_client):
        """가격 영향도 계산 테스트"""
        # 신정
        test_date = date(2025, 1, 1)
        result = api_client._calculate_price_impact(test_date, "元日")
        assert result == "very_high"

        # 일반 공휴일
        test_date = date(2025, 6, 15)
        result = api_client._calculate_price_impact(test_date, "일반 공휴일")
        assert result in ["medium", "high"]
