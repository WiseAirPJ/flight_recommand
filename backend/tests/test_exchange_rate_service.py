from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from app.services.exchange_rate_service import (
    ExchangeRate,
    ExchangeRateResponse,
    ExchangeRateService,
    ExchangeRateType,
)


class TestExchangeRateService:
    """환율 서비스 테스트 클래스"""

    @pytest.fixture
    def exchange_service(self):
        """환율 서비스 인스턴스 픽스처"""
        with patch("app.services.exchange_rate_service.settings") as mock_settings:
            mock_settings.KOREAEXIM_API_KEY = "test_api_key"
            mock_settings.KOREAEXIM_BASE_URL = "https://oapi.koreaexim.go.kr"
            return ExchangeRateService()

    @pytest.fixture
    def sample_api_response(self):
        """샘플 API 응답 데이터"""
        return [
            {
                "result": 1,
                "cur_unit": "USD",
                "cur_nm": "미국 달러",
                "deal_bas_r": "1,300.00",
                "bkpr": "1,320.00",
                "yy_efee_r": "1,280.00",
                "ten_dd_efee_r": "1,290.00",
                "kftc_bkpr": "1,310.00",
            },
            {
                "result": 1,
                "cur_unit": "JPY(100)",
                "cur_nm": "일본 엔",
                "deal_bas_r": "950.00",
                "bkpr": "970.00",
                "yy_efee_r": "930.00",
                "ten_dd_efee_r": "940.00",
                "kftc_bkpr": "960.00",
            },
        ]

    @pytest.fixture
    def sample_exchange_rates(self):
        """샘플 환율 데이터"""
        return [
            ExchangeRate(
                currency_code="USD",
                currency_name="미국 달러",
                base_rate=1300.0,
                buy_rate=1320.0,
                sell_rate=1280.0,
                send_rate=1290.0,
                receive_rate=1310.0,
                exchange_date="1",
            ),
            ExchangeRate(
                currency_code="JPY(100)",
                currency_name="일본 엔",
                base_rate=950.0,
                buy_rate=970.0,
                sell_rate=930.0,
                send_rate=940.0,
                receive_rate=960.0,
                exchange_date="1",
            ),
        ]

    def test_exchange_rate_service_initialization(self, exchange_service):
        """환율 서비스 초기화 테스트"""
        assert exchange_service.base_url == "https://oapi.koreaexim.go.kr"
        assert exchange_service.endpoint == "/site/program/financial/exchangeJSON"
        assert exchange_service.auth_key == "test_api_key"
        assert exchange_service.cache_service.get_cache("absent") is None
        assert exchange_service.cache_ttl == 14400

    def test_exchange_rate_data_class(self):
        """환율 데이터 클래스 테스트"""
        rate = ExchangeRate(
            currency_code="USD",
            currency_name="미국 달러",
            base_rate=1300.0,
            buy_rate=1320.0,
            sell_rate=1280.0,
            send_rate=1290.0,
            receive_rate=1310.0,
            exchange_date="20240101",
        )

        rate_dict = rate.to_dict()
        assert rate_dict["currency_code"] == "USD"
        assert rate_dict["base_rate"] == 1300.0
        assert isinstance(rate_dict, dict)

    def test_exchange_rate_response_data_class(self, sample_exchange_rates):
        """환율 응답 데이터 클래스 테스트"""
        response = ExchangeRateResponse(
            success=True, rates=sample_exchange_rates, updated_at="2024-01-01T00:00:00"
        )

        response_dict = response.to_dict()
        assert response_dict["success"] is True
        assert len(response_dict["rates"]) == 2
        assert response_dict["source"] == "한국수출입은행"

    def test_parse_exchange_rates(self, exchange_service, sample_api_response):
        """환율 데이터 파싱 테스트"""
        rates = exchange_service._parse_exchange_rates(sample_api_response)

        assert len(rates) == 2
        assert rates[0].currency_code == "USD"
        assert rates[0].base_rate == 1300.0
        assert rates[1].currency_code == "JPY"
        assert rates[1].base_rate == 9.5

    def test_parse_exchange_rates_with_invalid_data(self, exchange_service):
        """잘못된 데이터로 환율 파싱 테스트"""
        invalid_data = [
            {
                "cur_unit": "USD",
                "cur_nm": "미국 달러",
                "deal_bas_r": "N/A",  # 잘못된 값
                "bkpr": "",
                "yy_efee_r": None,
            }
        ]

        rates = exchange_service._parse_exchange_rates(invalid_data)

        assert rates == []

    def test_cache_functionality(self, exchange_service):
        """캐시 기능 테스트"""
        cache_key = "test_rates_20240101"
        test_data = {"test": "data"}

        # 캐시 저장
        exchange_service.cache_service.set_cache(cache_key, test_data, ttl_seconds=3600)

        # 캐시 조회
        cached_data = exchange_service.cache_service.get_cache(cache_key)
        assert cached_data == test_data

        # 캐시 만료 테스트
        exchange_service.cache_service.set_cache(cache_key, test_data, ttl_seconds=0)
        cached_data = exchange_service.cache_service.get_cache(cache_key)
        assert cached_data is None

    @pytest.mark.asyncio
    async def test_fetch_exchange_rates_success(
        self, exchange_service, sample_api_response
    ):
        """환율 API 호출 성공 테스트"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = sample_api_response
            mock_response.raise_for_status.return_value = None

            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            result = await exchange_service._fetch_exchange_rates("20240101", "AP01")

            assert result == sample_api_response
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_fetch_exchange_rates_no_api_key(self, exchange_service):
        """API 키가 없는 경우 테스트"""
        exchange_service.auth_key = None

        result = await exchange_service._fetch_exchange_rates("20240101", "AP01")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_exchange_rates_http_error(self, exchange_service):
        """HTTP 오류 발생 테스트"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = (
                Exception("HTTP Error")
            )

            result = await exchange_service._fetch_exchange_rates("20240101", "AP01")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_current_rates_success(
        self, exchange_service, sample_api_response
    ):
        """현재 환율 조회 성공 테스트"""
        with patch.object(exchange_service, "_fetch_exchange_rates") as mock_fetch:
            mock_fetch.return_value = sample_api_response

            result = await exchange_service.get_current_rates()

            assert result.success is True
            assert len(result.rates) == 2
            assert result.rates[0].currency_code == "USD"

    @pytest.mark.asyncio
    async def test_get_current_rates_with_currency_filter(
        self, exchange_service, sample_api_response
    ):
        """특정 통화 필터링 테스트"""
        with patch.object(exchange_service, "_fetch_exchange_rates") as mock_fetch:
            mock_fetch.return_value = sample_api_response

            result = await exchange_service.get_current_rates(currency_codes=["USD"])

            assert result.success is True
            assert len(result.rates) == 1
            assert result.rates[0].currency_code == "USD"

    @pytest.mark.asyncio
    async def test_get_current_rates_from_cache(
        self, exchange_service, sample_api_response
    ):
        """캐시에서 현재 환율 조회 테스트"""
        # 캐시에 데이터 설정
        today = datetime.now().strftime("%Y%m%d")
        cache_key = f"exchange_rate:v2:{today}"

        cached_response = ExchangeRateResponse(
            success=True,
            rates=exchange_service._parse_exchange_rates(sample_api_response),
            updated_at=datetime.now().isoformat(),
        )

        exchange_service.cache_service.set_cache(cache_key, cached_response.to_dict())

        with patch.object(exchange_service, "_fetch_exchange_rates") as mock_fetch:
            result = await exchange_service.get_current_rates()

            # API 호출이 발생하지 않아야 함
            mock_fetch.assert_not_called()
            assert result.success is True

    @pytest.mark.asyncio
    async def test_get_current_rates_api_failure(self, exchange_service):
        """API 호출 실패 테스트"""
        with patch.object(exchange_service, "_fetch_exchange_rates") as mock_fetch:
            mock_fetch.return_value = None

            result = await exchange_service.get_current_rates()

            assert result.success is False
            assert "환율이 없습니다" in result.error_message

    @pytest.mark.asyncio
    async def test_get_historical_rates_success(
        self, exchange_service, sample_api_response
    ):
        """과거 환율 조회 성공 테스트"""
        with patch.object(exchange_service, "_fetch_exchange_rates") as mock_fetch:
            mock_fetch.return_value = sample_api_response

            result = await exchange_service.get_historical_rates("20240101")

            assert result.success is True
            assert len(result.rates) == 2

    @pytest.mark.asyncio
    async def test_get_historical_rates_invalid_date(self, exchange_service):
        """잘못된 날짜 형식 테스트"""
        result = await exchange_service.get_historical_rates("2024-01-01")

        assert result.success is False
        assert "날짜 형식이 올바르지 않습니다" in result.error_message

    @pytest.mark.asyncio
    async def test_convert_currency_same_currency(self, exchange_service):
        """같은 통화 변환 테스트"""
        result = await exchange_service.convert_currency(100, "USD", "USD")

        assert result["success"] is True
        assert result["converted_amount"] == 100
        assert result["exchange_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_convert_currency_to_krw(self, exchange_service):
        """USD를 KRW로 변환 테스트"""
        mock_response = ExchangeRateResponse(
            success=True,
            rates=[
                ExchangeRate(
                    currency_code="USD",
                    currency_name="미국 달러",
                    base_rate=1300.0,
                    buy_rate=1320.0,
                    sell_rate=1280.0,
                    send_rate=1290.0,
                    receive_rate=1310.0,
                    exchange_date="20240101",
                )
            ],
            updated_at=datetime.now().isoformat(),
        )

        with patch.object(exchange_service, "get_current_rates") as mock_get_rates:
            mock_get_rates.return_value = mock_response

            result = await exchange_service.convert_currency(100, "USD", "KRW")

            assert result["success"] is True
            assert result["converted_amount"] == 130000.0
            assert result["exchange_rate"] == 1300.0

    @pytest.mark.asyncio
    async def test_convert_currency_failure(self, exchange_service):
        """통화 변환 실패 테스트"""
        mock_response = ExchangeRateResponse(
            success=False,
            rates=[],
            updated_at=datetime.now().isoformat(),
            error_message="환율 정보 없음",
        )

        with patch.object(exchange_service, "get_current_rates") as mock_get_rates:
            mock_get_rates.return_value = mock_response

            result = await exchange_service.convert_currency(100, "XXX", "KRW")

            assert result["success"] is False
            assert "환율이 없습니다" in result["error"]

    def test_get_supported_currencies(self, exchange_service):
        """지원 통화 목록 테스트"""
        currencies = exchange_service.get_supported_currencies()

        assert isinstance(currencies, list)
        assert "USD" in currencies
        assert "JPY" in currencies
        assert "EUR" in currencies
        assert "KRW" in currencies

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, exchange_service):
        """캐시 통계 테스트"""
        # 캐시에 데이터 추가
        exchange_service.cache_service.set_cache("test1", {"data": "test1"})
        exchange_service.cache_service.set_cache("test2", {"data": "test2"})

        stats = await exchange_service.get_cache_stats()

        assert stats["cache_backend"] == "CacheService"
        assert stats["default_ttl"] == 14400

    def test_exchange_rate_type_enum(self):
        """환율 타입 열거형 테스트"""
        assert ExchangeRateType.CURRENT.value == "AP01"
        assert ExchangeRateType.HISTORICAL.value == "AP01"

    @pytest.mark.asyncio
    async def test_error_handling_in_get_current_rates(self, exchange_service):
        """get_current_rates 오류 처리 테스트"""
        with patch.object(exchange_service, "_fetch_exchange_rates") as mock_fetch:
            mock_fetch.side_effect = Exception("Unexpected error")

            result = await exchange_service.get_current_rates()

            assert result.success is False
            assert "환율 조회 중 오류가 발생했습니다" in result.error_message

    @pytest.mark.asyncio
    async def test_error_handling_in_convert_currency(self, exchange_service):
        """convert_currency 오류 처리 테스트"""
        with patch.object(exchange_service, "get_current_rates") as mock_get_rates:
            mock_get_rates.side_effect = Exception("Unexpected error")

            result = await exchange_service.convert_currency(100, "USD", "KRW")

            assert result["success"] is False
            assert "통화 변환 중 오류가 발생했습니다" in result["error"]


@pytest.mark.asyncio
async def test_currency_filters_do_not_contaminate_cache():
    service = ExchangeRateService()
    data = [
        {
            "result": 1,
            "cur_unit": "JPY(100)",
            "deal_bas_r": "950",
            "tts": "960",
            "ttb": "940",
        },
        {"result": 1, "cur_unit": "USD", "deal_bas_r": "1300"},
    ]
    with patch.object(service, "_fetch_exchange_rates", return_value=data) as fetch:
        jpy = await service.get_current_rates(["JPY"])
        usd = await service.get_current_rates(["USD"])
        assert isinstance(usd.rates[0], ExchangeRate)
        assert usd.rates[0].currency_code == "USD"
        assert jpy.rates[0].base_rate == 9.5
        assert jpy.rates[0].send_rate == 9.6
        assert fetch.call_count == 1
        result = await service.convert_currency(1300, "KRW", "USD")
        assert result["converted_amount"] == 1
        historical = await service.get_historical_rates("20200101", ["JPY"])
        assert historical.rates[0].exchange_date == "20200101"
        assert fetch.call_args.args == ("20200101", "AP01")
