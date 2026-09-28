from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.exchange_rate_service import ExchangeRateService
from app.services.llm.llm_service import LLMService

router = APIRouter(prefix="/llm", tags=["LLM Analysis"])


class FlightAnalysisRequest(BaseModel):
    """항공편 분석 요청"""

    query: str = Field(..., description="사용자 검색 쿼리")
    flight_data: List[Dict[str, Any]] = Field(..., description="항공편 데이터")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "서울에서 도쿄로 가는 항공편",
                "flight_data": [
                    {
                        "id": "flight1",
                        "price": {"total": 450000},
                        "itineraries": [
                            {
                                "duration": "PT2H30M",
                                "segments": [
                                    {
                                        "departure": {"iataCode": "ICN"},
                                        "arrival": {"iataCode": "NRT"},
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        }


class PriceAlertRequest(BaseModel):
    """가격 알림 요청"""

    flight_id: str = Field(..., description="항공편 ID")
    threshold_price: float = Field(..., description="알림 임계가격")
    user_id: str = Field(..., description="사용자 ID")
    alert_type: str = Field(default="price_drop", description="알림 타입")


class CurrencyConversionRequest(BaseModel):
    """통화 변환 요청"""

    amount: float = Field(..., description="변환할 금액")
    from_currency: str = Field(..., description="원래 통화")
    to_currency: str = Field(default="KRW", description="변환할 통화")


def get_llm_service() -> LLMService:
    """LLM 서비스 의존성"""
    return LLMService()


def get_exchange_service() -> ExchangeRateService:
    """환율 서비스 의존성"""
    return ExchangeRateService()


@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_flights(
    request: FlightAnalysisRequest, llm_service: LLMService = Depends(get_llm_service)
) -> Dict[str, Any]:
    """고급 항공편 분석"""
    try:
        result = await llm_service.analyze_flights_advanced(
            query=request.query, flight_data=request.flight_data
        )

        return {
            "success": True,
            "analysis": {
                "price_trends": [
                    {
                        "current_price": trend.current_price,
                        "trend_direction": trend.trend_direction.value,
                        "price_change_percent": trend.price_change_percent,
                        "predicted_price": trend.predicted_price,
                        "confidence": trend.confidence,
                    }
                    for trend in result.price_trends
                ],
                "route_analysis": [
                    {
                        "route": route.route,
                        "total_duration": route.total_duration,
                        "stops": route.stops,
                        "price_efficiency": route.price_efficiency,
                        "convenience_score": route.convenience_score,
                        "recommendation_score": route.recommendation_score,
                    }
                    for route in result.route_analysis
                ],
                "best_deal": result.best_deal,
                "recommendations": result.recommendations,
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"항공편 분석 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/basic-analysis", response_model=Dict[str, Any])
async def basic_flight_analysis(
    request: FlightAnalysisRequest, llm_service: LLMService = Depends(get_llm_service)
) -> Dict[str, Any]:
    """기본 항공편 분석"""
    try:
        result = await llm_service.analyze_flights(
            flights_data=request.flight_data, context={"query": request.query}
        )

        return {
            "success": True,
            "analysis": result,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"기본 항공편 분석 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/price-alerts", response_model=Dict[str, Any])
async def create_price_alert(
    request: PriceAlertRequest, llm_service: LLMService = Depends(get_llm_service)
) -> Dict[str, Any]:
    """가격 알림 생성"""
    try:
        alert = llm_service.create_price_alert(
            flight_id=request.flight_id,
            threshold_price=request.threshold_price,
            user_id=request.user_id,
            alert_type=request.alert_type,
        )

        return {
            "success": True,
            "alert": {
                "flight_id": alert.flight_id,
                "threshold_price": alert.threshold_price,
                "user_id": alert.user_id,
                "alert_type": alert.alert_type,
                "created_at": alert.created_at.isoformat(),
                "is_active": alert.is_active,
            },
            "message": "가격 알림이 생성되었습니다.",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"가격 알림 생성 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/check-alerts", response_model=Dict[str, Any])
async def check_price_alerts(
    flight_data: List[Dict[str, Any]],
    llm_service: LLMService = Depends(get_llm_service),
) -> Dict[str, Any]:
    """가격 알림 확인"""
    try:
        triggered_alerts = llm_service.check_price_alerts(flight_data)

        return {
            "success": True,
            "triggered_alerts": [
                {
                    "alert_id": alert["alert"].flight_id,
                    "flight_id": alert["flight"]["id"],
                    "message": alert["message"],
                    "current_price": alert["flight"]["price"]["total"],
                }
                for alert in triggered_alerts
            ],
            "count": len(triggered_alerts),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"가격 알림 확인 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/cache-stats", response_model=Dict[str, Any])
async def get_llm_cache_stats(
    llm_service: LLMService = Depends(get_llm_service),
) -> Dict[str, Any]:
    """LLM 캐시 통계"""
    try:
        stats = llm_service.get_cache_stats()

        return {
            "success": True,
            "cache_stats": stats,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"캐시 통계 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/exchange-rates", response_model=Dict[str, Any])
async def get_current_exchange_rates(
    currencies: Optional[str] = None,
    exchange_service: ExchangeRateService = Depends(get_exchange_service),
) -> Dict[str, Any]:
    """현재 환율 조회"""
    try:
        currency_codes = currencies.split(",") if currencies else None

        result = await exchange_service.get_current_rates(currency_codes)

        return {
            "success": result.success,
            "rates": result.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"환율 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/exchange-rates/historical", response_model=Dict[str, Any])
async def get_historical_exchange_rates(
    date: str,
    currencies: Optional[str] = None,
    exchange_service: ExchangeRateService = Depends(get_exchange_service),
) -> Dict[str, Any]:
    """과거 환율 조회"""
    try:
        currency_codes = currencies.split(",") if currencies else None

        result = await exchange_service.get_historical_rates(date, currency_codes)

        return {
            "success": result.success,
            "rates": result.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"과거 환율 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/currency-conversion", response_model=Dict[str, Any])
async def convert_currency(
    request: CurrencyConversionRequest,
    exchange_service: ExchangeRateService = Depends(get_exchange_service),
) -> Dict[str, Any]:
    """통화 변환"""
    try:
        result = await exchange_service.convert_currency(
            amount=request.amount,
            from_currency=request.from_currency,
            to_currency=request.to_currency,
        )

        return {
            "success": result.get("success", False),
            "conversion": result,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"통화 변환 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/exchange-rates/supported", response_model=Dict[str, Any])
async def get_supported_currencies(
    exchange_service: ExchangeRateService = Depends(get_exchange_service),
) -> Dict[str, Any]:
    """지원하는 통화 목록"""
    try:
        currencies = exchange_service.get_supported_currencies()

        return {
            "success": True,
            "currencies": currencies,
            "count": len(currencies),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"지원 통화 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/exchange-rates/cache-stats", response_model=Dict[str, Any])
async def get_exchange_cache_stats(
    exchange_service: ExchangeRateService = Depends(get_exchange_service),
) -> Dict[str, Any]:
    """환율 캐시 통계"""
    try:
        stats = await exchange_service.get_cache_stats()

        return {
            "success": True,
            "cache_stats": stats,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"환율 캐시 통계 조회 중 오류가 발생했습니다: {str(e)}",
        )
