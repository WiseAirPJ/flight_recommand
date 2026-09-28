"""
검증 유틸리티 테스트
"""

from datetime import date, timedelta

import pytest

from app.utils.validators import (
    validate_date_format,
    validate_duration,
    validate_iata_code,
    validate_passenger_count,
)


class TestValidators:
    """검증 함수 테스트 클래스"""

    def test_validate_date_format_success(self):
        """올바른 날짜 형식 테스트"""
        future_date = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
        result = validate_date_format(future_date)
        assert result == future_date

    def test_validate_date_format_invalid_format(self):
        """잘못된 날짜 형식 테스트"""
        with pytest.raises(ValueError, match="날짜 형식이 올바르지 않습니다"):
            validate_date_format("2025-13-50")

    def test_validate_date_format_past_date(self):
        """과거 날짜 테스트"""
        past_date = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        with pytest.raises(ValueError, match="날짜는 오늘 이후여야 합니다"):
            validate_date_format(past_date)

    def test_validate_date_format_allow_past(self):
        """과거 날짜 허용 테스트"""
        past_date = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        result = validate_date_format(past_date, allow_past=True)
        assert result == past_date

    def test_validate_iata_code_success(self):
        """올바른 IATA 코드 테스트"""
        assert validate_iata_code("icn") == "ICN"
        assert validate_iata_code("NRT") == "NRT"

    def test_validate_iata_code_invalid_length(self):
        """잘못된 길이 IATA 코드 테스트"""
        with pytest.raises(ValueError, match="IATA 코드는 3자리여야 합니다"):
            validate_iata_code("IC")

        with pytest.raises(ValueError, match="IATA 코드는 3자리여야 합니다"):
            validate_iata_code("ICNX")

    def test_validate_iata_code_invalid_characters(self):
        """잘못된 문자 IATA 코드 테스트"""
        with pytest.raises(ValueError, match="IATA 코드는 영문자만 포함해야 합니다"):
            validate_iata_code("IC1")

    def test_validate_duration_success(self):
        """올바른 기간 테스트"""
        assert validate_duration(3) == 3
        assert validate_duration(15) == 15

    def test_validate_duration_too_short(self):
        """너무 짧은 기간 테스트"""
        with pytest.raises(ValueError, match="여행 기간은 최소 2일 이상이어야 합니다"):
            validate_duration(1)

    def test_validate_duration_too_long(self):
        """너무 긴 기간 테스트"""
        with pytest.raises(ValueError, match="여행 기간은 최대 30일까지 가능합니다"):
            validate_duration(31)

    def test_validate_passenger_count_success(self):
        """올바른 승객 수 테스트"""
        assert validate_passenger_count(1) == 1
        assert validate_passenger_count(5) == 5

    def test_validate_passenger_count_too_few(self):
        """너무 적은 승객 수 테스트"""
        with pytest.raises(ValueError, match="승객 수는 최소 1명 이상이어야 합니다"):
            validate_passenger_count(0)

    def test_validate_passenger_count_too_many(self):
        """너무 많은 승객 수 테스트"""
        with pytest.raises(ValueError, match="승객 수는 최대 9명까지 가능합니다"):
            validate_passenger_count(10)
