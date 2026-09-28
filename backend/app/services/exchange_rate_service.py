import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

from app.config.settings import settings
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class ExchangeRateType(Enum):
    """환율 데이터 타입"""

    CURRENT = "AP01"  # 현재 환율
    HISTORICAL = "AP02"  # 과거 환율


@dataclass
class ExchangeRate:
    """환율 정보 데이터 클래스"""

    currency_code: str  # 통화 코드 (USD, JPY, EUR 등)
    currency_name: str  # 통화명
    base_rate: float  # 기준환율
    buy_rate: float  # 현찰 살때
    sell_rate: float  # 현찰 팔때
    send_rate: float  # 송금 보낼때
    receive_rate: float  # 송금 받을때
    exchange_date: str  # 환율 기준일자

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)


@dataclass
class ExchangeRateResponse:
    """환율 API 응답 데이터"""

    success: bool
    rates: List[ExchangeRate]
    updated_at: str
    source: str = "한국수출입은행"
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "success": self.success,
            "rates": [rate.to_dict() for rate in self.rates],
            "updated_at": self.updated_at,
            "source": self.source,
            "error_message": self.error_message,
        }


class ExchangeRateService:
    """한국수출입은행 환율 API 서비스"""

    def __init__(self, cache_service: CacheService = None):
        self.base_url = "https://oapi.koreaexim.go.kr"
        self.endpoint = "/site/program/financial/exchangeJSON"
        self.auth_key = settings.KOREAEXIM_API_KEY
        self.cache_service = cache_service or CacheService()
        self.cache_ttl = 14400

    async def get_current_rates(
        self, currency_codes: Optional[List[str]] = None
    ) -> ExchangeRateResponse:
        """현재 환율 조회"""
        try:
            today = datetime.now().strftime("%Y%m%d")

            # 캐시 확인
            cache_key = f"exchange_rate:current_rates_{today}"
            cached_data = self.cache_service.get_cache(cache_key)
            if cached_data:
                logger.info("캐시에서 환율 정보 반환")
                return ExchangeRateResponse(**cached_data)

            # API 호출
            rates_data = await self._fetch_exchange_rates(
                date=today, data_type=ExchangeRateType.CURRENT.value
            )

            if not rates_data:
                return ExchangeRateResponse(
                    success=False,
                    rates=[],
                    updated_at=datetime.now().isoformat(),
                    error_message="환율 데이터를 가져올 수 없습니다.",
                )

            # 데이터 파싱
            exchange_rates = self._parse_exchange_rates(rates_data)

            # 특정 통화 필터링
            if currency_codes:
                exchange_rates = [
                    rate
                    for rate in exchange_rates
                    if rate.currency_code in currency_codes
                ]

            response = ExchangeRateResponse(
                success=True,
                rates=exchange_rates,
                updated_at=datetime.now().isoformat(),
            )

            # 캐시에 저장
            self.cache_service.set_cache(cache_key, response.to_dict(), self.cache_ttl)

            return response

        except Exception as e:
            logger.error(f"환율 조회 실패: {e}")
            return ExchangeRateResponse(
                success=False,
                rates=[],
                updated_at=datetime.now().isoformat(),
                error_message=f"환율 조회 중 오류가 발생했습니다: {str(e)}",
            )

    async def get_historical_rates(
        self, date: str, currency_codes: Optional[List[str]] = None
    ) -> ExchangeRateResponse:
        """과거 환율 조회"""
        try:
            # 날짜 형식 검증
            try:
                datetime.strptime(date, "%Y%m%d")
            except ValueError:
                return ExchangeRateResponse(
                    success=False,
                    rates=[],
                    updated_at=datetime.now().isoformat(),
                    error_message="날짜 형식이 올바르지 않습니다. (YYYYMMDD 형식 필요)",
                )

            # 캐시 확인
            cache_key = f"exchange_rate:historical_rates_{date}"
            cached_data = self.cache_service.get_cache(cache_key)
            if cached_data:
                logger.info(f"캐시에서 과거 환율 정보 반환: {date}")
                return ExchangeRateResponse(**cached_data)

            # API 호출
            rates_data = await self._fetch_exchange_rates(
                date=date, data_type=ExchangeRateType.HISTORICAL.value
            )

            if not rates_data:
                return ExchangeRateResponse(
                    success=False,
                    rates=[],
                    updated_at=datetime.now().isoformat(),
                    error_message=f"{date} 날짜의 환율 데이터를 찾을 수 없습니다.",
                )

            # 데이터 파싱
            exchange_rates = self._parse_exchange_rates(rates_data)

            # 특정 통화 필터링
            if currency_codes:
                exchange_rates = [
                    rate
                    for rate in exchange_rates
                    if rate.currency_code in currency_codes
                ]

            response = ExchangeRateResponse(
                success=True,
                rates=exchange_rates,
                updated_at=datetime.now().isoformat(),
            )

            # 캐시에 저장 (과거 데이터는 더 오래 캐시)
            self.cache_service.set_cache(cache_key, response.to_dict(), 86400)  # 24시간

            return response

        except Exception as e:
            logger.error(f"과거 환율 조회 실패: {e}")
            return ExchangeRateResponse(
                success=False,
                rates=[],
                updated_at=datetime.now().isoformat(),
                error_message=f"과거 환율 조회 중 오류가 발생했습니다: {str(e)}",
            )

    async def convert_currency(
        self, amount: float, from_currency: str, to_currency: str = "KRW"
    ) -> Dict[str, Any]:
        """통화 변환"""
        try:
            if from_currency == to_currency:
                return {
                    "success": True,
                    "amount": amount,
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "converted_amount": amount,
                    "exchange_rate": 1.0,
                    "converted_at": datetime.now().isoformat(),
                }

            # 현재 환율 조회
            rates_response = await self.get_current_rates([from_currency])

            if not rates_response.success or not rates_response.rates:
                return {"success": False, "error": f"{from_currency} 환율 정보를 찾을 수 없습니다."}

            rate = rates_response.rates[0]

            # KRW로 변환하는 경우
            if to_currency == "KRW":
                exchange_rate = rate.base_rate
                converted_amount = amount * exchange_rate
            else:
                # 다른 통화로 변환하는 경우 (KRW를 거쳐서 변환)
                to_rates_response = await self.get_current_rates([to_currency])
                if not to_rates_response.success or not to_rates_response.rates:
                    return {
                        "success": False,
                        "error": f"{to_currency} 환율 정보를 찾을 수 없습니다.",
                    }

                to_rate = to_rates_response.rates[0]
                # from_currency -> KRW -> to_currency
                krw_amount = amount * rate.base_rate
                converted_amount = krw_amount / to_rate.base_rate
                exchange_rate = rate.base_rate / to_rate.base_rate

            return {
                "success": True,
                "amount": amount,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "converted_amount": round(converted_amount, 2),
                "exchange_rate": round(exchange_rate, 4),
                "converted_at": datetime.now().isoformat(),
                "rate_date": rate.exchange_date,
            }

        except Exception as e:
            logger.error(f"통화 변환 실패: {e}")
            return {"success": False, "error": f"통화 변환 중 오류가 발생했습니다: {str(e)}"}

    async def _fetch_exchange_rates(
        self, date: str, data_type: str
    ) -> Optional[List[Dict]]:
        """환율 API 호출"""
        if not self.auth_key:
            logger.warning("한국수출입은행 API 키가 설정되지 않았습니다.")
            return None

        params = {"authkey": self.auth_key, "searchdate": date, "data": data_type}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}{self.endpoint}", params=params
                )
                response.raise_for_status()

                data = response.json()

                # API 오류 응답 처리
                if isinstance(data, dict) and "error" in data:
                    logger.error(f"API 오류 응답: {data}")
                    return None

                return data if isinstance(data, list) else None

        except httpx.HTTPError as e:
            logger.error(f"HTTP 오류: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON 디코딩 오류: {e}")
            return None
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}")
            return None

    def _parse_exchange_rates(self, data: List[Dict]) -> List[ExchangeRate]:
        """환율 데이터 파싱"""
        rates = []

        for item in data:
            try:
                # 숫자 데이터 안전하게 변환
                def safe_float(value):
                    if not value or value == "N/A":
                        return 0.0
                    return float(str(value).replace(",", ""))

                rate = ExchangeRate(
                    currency_code=item.get("cur_unit", ""),
                    currency_name=item.get("cur_nm", ""),
                    base_rate=safe_float(item.get("deal_bas_r", 0)),
                    buy_rate=safe_float(item.get("bkpr", 0)),
                    sell_rate=safe_float(item.get("yy_efee_r", 0)),
                    send_rate=safe_float(item.get("ten_dd_efee_r", 0)),
                    receive_rate=safe_float(item.get("kftc_bkpr", 0)),
                    exchange_date=item.get("result", 1),
                )

                rates.append(rate)

            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"환율 데이터 파싱 오류: {e}, 데이터: {item}")
                continue

        return rates

    def _get_cache_key(self, prefix: str, date: str) -> str:
        """캐시 키 생성"""
        return f"exchange_rate:{prefix}_{date}"

    def get_supported_currencies(self) -> List[str]:
        """지원하는 통화 코드 목록"""
        return [
            "USD",
            "JPY",
            "EUR",
            "GBP",
            "CHF",
            "CAD",
            "AUD",
            "NZD",
            "SEK",
            "NOK",
            "DKK",
            "CNY",
            "HKD",
            "SGD",
            "THB",
            "MYR",
            "INR",
            "IDR",
            "PHP",
            "VND",
            "BRL",
            "RUB",
            "ZAR",
            "TRY",
            "MXN",
            "CLP",
            "EGP",
            "AED",
            "SAR",
            "KWD",
            "BHD",
            "QAR",
            "OMR",
            "JOD",
            "LBP",
            "KZT",
            "UZS",
            "MNT",
            "FJD",
            "NPR",
            "LKR",
            "BDT",
            "PKR",
            "CZK",
            "HUF",
            "PLN",
            "BGN",
            "RON",
            "HRK",
            "RSD",
            "ISK",
            "ALL",
            "MKD",
            "ILS",
            "GEL",
            "AMD",
            "AZN",
            "KGS",
            "TJS",
            "AFN",
            "MMK",
            "LAK",
            "KHR",
            "BND",
            "TWD",
            "SRD",
            "PEN",
            "COP",
            "UYU",
            "PYG",
            "BOB",
            "VEF",
            "ARS",
            "DOP",
            "CUP",
            "HTG",
            "JMD",
            "BBD",
            "BSD",
            "BZD",
            "XCD",
            "TTD",
            "GYD",
            "AWG",
            "BMD",
            "KYD",
            "SVC",
            "NIO",
            "CRC",
            "GTQ",
            "HNL",
            "PAB",
        ]

    async def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 정보"""
        try:
            return {
                "service_type": "exchange_rate",
                "cache_backend": "CacheService",
                "default_ttl": self.cache_ttl,
                "cache_service_stats": "Use CacheService.get_cache_statistics() for detailed stats",
            }
        except Exception as e:
            logger.error(f"캐시 통계 조회 실패: {e}")
            return {"error": str(e)}
