from datetime import datetime, timedelta
from typing import Any, Dict


def enhance_flight_search_response(
    result: Dict[str, Any], request, *args, **kwargs
) -> Dict[str, Any]:
    flights = result.get("data", [])

    return {
        "flights": flights,
        "search_params": {
            "origin": request.origin,
            "destination": request.destination,
            "departure_date": request.departure_date,
            "return_date": getattr(request, "return_date", None),
            "adults": request.adults,
            "currency": request.currency,
            "non_stop": request.non_stop,
        },
        "search_timestamp": datetime.now().isoformat(),
        "from_cache": False,
        "result_count": len(flights) if flights else 0,
    }


def enhance_duration_search_response(
    result: Dict[str, Any], request, *args, **kwargs
) -> Dict[str, Any]:
    """기간별 검색 응답 보강"""
    flights = result.get("data", [])

    # 귀국 날짜 계산
    departure = datetime.strptime(request.departure_date, "%Y-%m-%d").date()
    return_date = departure + timedelta(days=request.duration_days - 1)

    return {
        "flights": flights,
        "trip_details": {
            "departure_date": request.departure_date,
            "return_date": return_date.strftime("%Y-%m-%d"),
            "duration_days": request.duration_days,
            "nights": request.duration_days - 1,
            "destination": request.destination,
            "description": f"{request.duration_days - 1}박 {request.duration_days}일",
        },
        "search_params": {
            "origin": request.origin,
            "destination": request.destination,
            "duration_days": request.duration_days,
            "adults": request.adults,
            "currency": request.currency,
            "non_stop": request.non_stop,
        },
        "search_timestamp": datetime.now().isoformat(),
        "from_cache": False,
        "result_count": len(flights) if flights else 0,
    }


def enhance_cheapest_dates_response(
    result: Dict[str, Any], request, *args, **kwargs
) -> Dict[str, Any]:
    """최저가 날짜 응답 보강"""
    search_result = result.get("data", [])

    # 가격 분석
    price_analysis = {}
    if search_result:
        prices = []
        for item in search_result:
            try:
                price = float(item.get("price", {}).get("total", 0))
                prices.append(price)
            except ValueError, TypeError:
                continue

        if prices:
            price_analysis = {
                "min_price": min(prices),
                "max_price": max(prices),
                "avg_price": sum(prices) / len(prices),
                "price_range": max(prices) - min(prices),
                "savings_potential": (
                    f"최대 {max(prices) - min(prices):,.0f} {request.currency} 차이"
                    if len(prices) > 1
                    else "N/A"
                ),
            }

    return {
        "cheapest_options": search_result,
        "search_params": {
            "origin": request.origin,
            "destination": request.destination,
            "base_departure_date": request.departure_date,
            "duration": request.duration,
            "flexibility_days": request.flexibility_days,
        },
        "price_analysis": price_analysis,
        "search_timestamp": datetime.now().isoformat(),
        "result_count": len(search_result) if search_result else 0,
        "recommendations": {
            "best_value": search_result[0] if search_result else None,
            "booking_advice": "예약 시 실제 가격과 수하물 조건을 다시 확인하세요.",
        },
    }


def enhance_airport_info_response(
    result: Dict[str, Any], iata_code: str, *args, **kwargs
) -> Dict[str, Any]:
    """공항 정보 응답 보강"""
    airport_data = result.get("data", {})

    return {
        **airport_data,
        "queried_iata": iata_code.upper(),
        "last_updated": datetime.now().isoformat(),
    }


def get_popular_routes_data(origin: str = "ICN", limit: int = 10) -> Dict[str, Any]:
    """Static destinations, with no fabricated prices or popularity statistics."""
    routes = [
        {"destination": code, "city": city}
        for code, city in [
            ("NRT", "도쿄"),
            ("KIX", "오사카"),
            ("CTS", "삿포로"),
            ("FUK", "후쿠오카"),
            ("NGO", "나고야"),
            ("OKA", "나하"),
        ]
    ]
    return {
        "origin": origin,
        "popular_routes": routes[:limit],
        "total_routes": min(len(routes), limit),
        "data_source": "static_destination_catalog",
        "note": "추천 여행지 목록이며 운항 여부나 인기도 순위가 아닙니다.",
    }
