"""
항공편 API 테스트
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.flights import get_amadeus_service, get_cache_service
from app.main import app

client = TestClient(app)


class TestFlightsAPI:
    """항공편 API 테스트 클래스"""

    @pytest.fixture
    def mock_amadeus_service(self):
        service = Mock(source="amadeus_test")
        service.search_flight_offers = AsyncMock(
            return_value={
                "success": True,
                "data": [{"id": "1", "price": {"total": "300000", "currency": "KRW"}}],
                "meta": {"source": "amadeus_test"},
                "dictionaries": {},
            }
        )
        service.get_airport_info = AsyncMock()
        app.dependency_overrides[get_amadeus_service] = lambda: service
        yield service
        app.dependency_overrides.pop(get_amadeus_service, None)

    @pytest.fixture
    def mock_cache_service(self):
        service = Mock()
        service.get_cache.return_value = None
        app.dependency_overrides[get_cache_service] = lambda: service
        yield service
        app.dependency_overrides.pop(get_cache_service, None)

    def test_search_flights_success(self, mock_amadeus_service, mock_cache_service):
        """항공편 검색 성공 테스트"""
        request_data = {
            "origin": "ICN",
            "destination": "NRT",
            "departure_date": (date.today() + timedelta(days=30)).isoformat(),
            "adults": 1,
        }

        response = client.post("/api/v1/flights/search", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "flights" in data["data"]

    def test_search_flights_invalid_date(self):
        """잘못된 날짜 형식 테스트"""
        request_data = {
            "origin": "ICN",
            "destination": "NRT",
            "departure_date": "2025-13-50",  # 잘못된 날짜
            "adults": 1,
        }

        response = client.post("/api/v1/flights/search", json=request_data)

        assert response.status_code == 422

    def test_search_by_duration_success(self, mock_amadeus_service, mock_cache_service):
        """기간별 검색 성공 테스트"""
        request_data = {
            "origin": "ICN",
            "destination": "NRT",
            "departure_date": (date.today() + timedelta(days=30)).isoformat(),
            "duration_days": 4,
            "adults": 1,
        }

        response = client.post("/api/v1/flights/search-by-duration", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "trip_details" in data["data"]

    def test_airport_info_success(self, mock_amadeus_service, mock_cache_service):
        """공항 정보 조회 성공 테스트"""
        mock_amadeus_service.get_airport_info.return_value = {
            "success": True,
            "data": {"iata": "ICN", "name": "인천국제공항"},
        }

        response = client.get("/api/v1/flights/airport/ICN")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_airport_info_invalid_iata(self):
        """잘못된 IATA 코드 테스트"""
        response = client.get("/api/v1/flights/airport/INVALID")

        assert response.status_code == 422  # 입력 검증 오류

    def test_popular_routes_success(self, mock_cache_service):
        """인기 노선 조회 성공 테스트"""
        response = client.get("/api/v1/flights/popular-routes?origin=ICN&limit=5")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "popular_routes" in data["data"]
        assert len(data["data"]["popular_routes"]) <= 5

    def test_health_check(self):
        """헬스 체크 테스트"""
        response = client.get("/api/v1/flights/health")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "flights"
        assert data["status"] == "healthy"
