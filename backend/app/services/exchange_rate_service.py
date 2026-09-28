import asyncio
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
    HISTORICAL = "AP01"  # 과거 환율


@dataclass
class ExchangeRate:
    """환율 정보 데이터 클래스"""

    currency_code: str  # 통화 코드 (USD, JPY, EUR 등)
    currency_name: str  # 통화명
    base_rate: float  # 기준환율
    buy_rate: float  # 공급하지 않는 현찰 환율은 0
    sell_rate: float  # 공급하지 않는 현찰 환율은 0
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
        self.base_url = settings.KOREAEXIM_BASE_URL
        self.endpoint = "/site/program/financial/exchangeJSON"
        self.auth_key = settings.KOREAEXIM_API_KEY
        self.cache_service = cache_service or CacheService()
        self.cache_ttl = 14400

    async def get_current_rates(self, currency_codes=None):
        return await self._get_rates(datetime.now().strftime("%Y%m%d"), currency_codes)

    async def get_historical_rates(self, date, currency_codes=None):
        return await self._get_rates(date, currency_codes)

    async def _get_rates(self, date, currency_codes):
        now = datetime.now().isoformat()
        try:
            if len(date) != 8:
                raise ValueError("YYYYMMDD 형식 필요")
            datetime.strptime(date, "%Y%m%d")
            key = f"exchange_rate:v2:{date}"
            cached = await asyncio.to_thread(self.cache_service.get_cache, key)
            if cached:
                rates = [ExchangeRate(**item) for item in cached["rates"]]
                now = cached["updated_at"]
            else:
                data = await self._fetch_exchange_rates(
                    date, ExchangeRateType.CURRENT.value
                )
                rates = self._parse_exchange_rates(data or [], date)
                if not rates:
                    return ExchangeRateResponse(
                        False, [], now, error_message="해당 날짜의 환율이 없습니다."
                    )
                # Cache the full table so a previous JPY request cannot poison a USD request.
                await asyncio.to_thread(
                    self.cache_service.set_cache,
                    key,
                    {"rates": [rate.to_dict() for rate in rates], "updated_at": now},
                    self.cache_ttl,
                )
            if currency_codes:
                rates = [rate for rate in rates if rate.currency_code in currency_codes]
            return ExchangeRateResponse(bool(rates), rates, now)
        except ValueError, TypeError:
            return ExchangeRateResponse(
                False,
                [],
                now,
                error_message="날짜 형식이 올바르지 않습니다. (YYYYMMDD)",
            )

        except Exception:
            logger.exception("환율 조회 실패")
            return ExchangeRateResponse(
                False, [], now, error_message="환율 조회 중 오류가 발생했습니다."
            )

    async def convert_currency(self, amount, from_currency, to_currency="KRW"):
        try:
            return await self._convert_currency(amount, from_currency, to_currency)
        except Exception:
            logger.exception("통화 변환 실패")
            return {"success": False, "error": "통화 변환 중 오류가 발생했습니다."}

    async def _convert_currency(self, amount, from_currency, to_currency="KRW"):
        from_currency, to_currency = from_currency.upper(), to_currency.upper()
        if from_currency == to_currency:
            return {
                "success": True,
                "amount": amount,
                "converted_amount": amount,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "exchange_rate": 1.0,
            }
        response = await self.get_current_rates([from_currency, to_currency])
        rates = {rate.currency_code: rate.base_rate for rate in response.rates}
        rates["KRW"] = 1.0
        if not rates.get(from_currency) or not rates.get(to_currency):
            return {"success": False, "error": "변환에 필요한 환율이 없습니다."}
        factor = rates[from_currency] / rates[to_currency]
        return {
            "success": True,
            "amount": amount,
            "converted_amount": round(amount * factor, 2),
            "from_currency": from_currency,
            "to_currency": to_currency,
            "exchange_rate": factor,
            "converted_at": datetime.now().isoformat(),
            "rate_date": response.rates[0].exchange_date if response.rates else None,
        }

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
            logger.error("환율 공급자 HTTP 요청 실패")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON 디코딩 오류: {e}")
            return None
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}")
            return None

    def _parse_exchange_rates(self, data, exchange_date=None):
        rates = []
        for item in data:
            try:
                if item.get("result", 1) != 1:
                    continue
                unit = item.get("cur_unit", "")
                divisor = 100 if unit.endswith("(100)") else 1
                code = unit.split("(")[0]

                def number(field):
                    return float(str(item.get(field) or "0").replace(",", "")) / divisor

                base = number("deal_bas_r")
                if not code or base <= 0:
                    continue
                rates.append(
                    ExchangeRate(
                        currency_code=code,
                        currency_name=item.get("cur_nm", ""),
                        base_rate=base,
                        buy_rate=0,
                        sell_rate=0,
                        send_rate=number("tts"),
                        receive_rate=number("ttb"),
                        exchange_date=exchange_date
                        or datetime.now().strftime("%Y%m%d"),
                    )
                )
            except ValueError, TypeError:
                continue
        return rates

    def _get_cache_key(self, prefix, date):
        return f"exchange_rate:v2:{date}"

    def get_supported_currencies(self):
        # Product-supported display currencies; availability depends on the provider/date.
        return ["KRW", "JPY", "USD", "EUR"]

    async def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 정보"""
        try:
            return {
                "service_type": "exchange_rate",
                "cache_backend": "CacheService",
                "default_ttl": self.cache_ttl,
                "cache_service_stats": "Use CacheAdminService.get_cache_statistics() for detailed stats",
            }
        except Exception as e:
            logger.error(f"캐시 통계 조회 실패: {e}")
            return {"error": str(e)}
