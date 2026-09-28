"""Versioned cache keys include every condition that changes a quote."""

import hashlib
import json


def _request_key(prefix, args, kwargs):
    request = args[0] if args else kwargs.get("request")
    if request is None:
        raise ValueError("검색 조건이 필요합니다.")
    payload = request.model_dump(mode="json")
    service = kwargs.get("amadeus_service")
    if service is not None:
        payload["source"] = service.source
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return f"{prefix}:v2:{digest}"


def flight_search_key(*args, **kwargs):
    return _request_key("flight_search", args, kwargs)


def duration_search_key(*args, **kwargs):
    return _request_key("duration_search", args, kwargs)


def cheapest_dates_key(*args, **kwargs):
    return _request_key("cheapest_dates", args, kwargs)


def airport_info_key(*args, **kwargs):
    code = args[0] if args else kwargs.get("iata_code", "")
    return f"airport_info:{code.upper()}"


def popular_routes_key(*args, **kwargs):
    return f"popular_routes:{kwargs.get('origin', 'ICN')}:{kwargs.get('limit', 10)}"


def monthly_search_key(request, source):
    return _request_key(f"monthly_cheapest:{source}", [request], {})
