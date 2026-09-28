import logging
from datetime import date, datetime
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)


class HolidayAPIClient:
    """일본 공휴일 API 클라이언트"""

    def __init__(self):
        self.base_url = "https://holidays-jp.github.io/api/v1"
        self.timeout = 10.0

    async def get_holidays(self, year: int) -> List[Dict[str, Any]]:
        """
        특정 연도의 일본 공휴일 조회

        Args:
            year: 조회할 연도

        Returns:
            공휴일 정보 리스트
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/{year}.json")
                response.raise_for_status()

                holidays_data = response.json()

                # 데이터 포맷 정규화
                formatted_holidays = []
                for date_str, name in holidays_data.items():
                    try:
                        # 날짜 파싱 검증
                        parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                        holiday_info = {
                            "date": date_str,
                            "name": name,
                            "name_en": self._translate_holiday_name(name),
                            "type": "national",
                            "season": self._determine_season(parsed_date),
                            "price_impact": self._calculate_price_impact(
                                parsed_date, name
                            ),
                            "description": self._get_holiday_description(name),
                        }
                        formatted_holidays.append(holiday_info)

                    except ValueError as e:
                        logger.warning(f"Invalid date format: {date_str}, error: {e}")
                        continue

                logger.info(
                    f"Successfully fetched {len(formatted_holidays)} "
                    f"holidays for {year}"
                )
                return formatted_holidays

        except httpx.TimeoutException:
            logger.error(f"Timeout while fetching holidays for {year}")
            return self._get_fallback_holidays(year)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error while fetching holidays for {year}: {e}")
            return self._get_fallback_holidays(year)

        except Exception as e:
            logger.error(f"Unexpected error while fetching holidays for {year}: {e}")
            return self._get_fallback_holidays(year)

    def _translate_holiday_name(self, japanese_name: str) -> str:
        """일본어 공휴일명 영어 번역"""
        translations = {
            "元日": "New Year's Day",
            "成人の日": "Coming of Age Day",
            "建国記念の日": "National Foundation Day",
            "天皇誕生日": "Emperor's Birthday",
            "春分の日": "Vernal Equinox Day",
            "昭和の日": "Showa Day",
            "憲法記念日": "Constitution Memorial Day",
            "みどりの日": "Greenery Day",
            "こどもの日": "Children's Day",
            "海の日": "Marine Day",
            "山の日": "Mountain Day",
            "敬老の日": "Respect for the Aged Day",
            "秋分の日": "Autumnal Equinox Day",
            "スポーツの日": "Sports Day",
            "体育の日": "Sports Day",
            "文化の日": "Culture Day",
            "勤労感謝の日": "Labor Thanksgiving Day",
        }
        return translations.get(japanese_name, japanese_name)

    def _determine_season(self, holiday_date: date) -> str:
        """공휴일 날짜의 시즌 결정"""
        month = holiday_date.month
        day = holiday_date.day

        # 특별 시즌 체크
        if (month == 4 and day >= 29) or (month == 5 and day <= 5):
            return "golden_week"
        elif month == 12 and day >= 25:
            return "winter_holiday"
        elif month == 1 and day <= 7:
            return "winter_holiday"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        elif month in [9, 10, 11]:
            return "autumn"
        else:
            return "winter"

    def _calculate_price_impact(self, holiday_date: date, name: str) -> str:
        """공휴일의 가격 영향도 계산"""
        month = holiday_date.month
        day = holiday_date.day

        # 최고 성수기
        if any(
            keyword in name for keyword in ["元日", "昭和", "憲法", "みどり", "こども"]
        ):
            return "very_high"

        # 골든위크 기간
        if (month == 4 and day >= 29) or (month == 5 and day <= 5):
            return "very_high"

        # 연말연시
        if (month == 12 and day >= 25) or (month == 1 and day <= 7):
            return "very_high"

        # 벚꽃 시즌 (3-4월)
        if month in [3, 4]:
            return "high"

        # 단풍 시즌 (10-11월)
        if month in [10, 11]:
            return "high"

        # 여름 휴가철
        if month in [7, 8]:
            return "high"

        # 기타 공휴일
        return "medium"

    def _get_holiday_description(self, name: str) -> str:
        """공휴일 설명 생성"""
        descriptions = {
            "元日": "연말연시 성수기",
            "成人の日": "3연휴",
            "建国기념일": "평일 공휴일",
            "天皇誕生日": "평일 공휴일",
            "春分の日": "벚꽃 시즌 시작",
            "昭和の日": "골든위크 시작",
            "憲法記念日": "골든위크 핵심 기간",
            "みどりの日": "골든위크 핵심 기간",
            "こどもの日": "골든위크 마지막",
            "海の日": "여름휴가철",
            "山の日": "여름휴가철",
            "敬老の日": "초가을 3연휴",
            "秋分の日": "가을 시작",
            "スポーツの日": "단풍 시즌",
            "体育の日": "단풍 시즌",
            "文화の日": "단풍 성수기",
            "勤労感謝の日": "단풍 시즌",
        }
        return descriptions.get(name, "일본 국경일")

    def _get_fallback_holidays(self, year: int) -> List[Dict[str, Any]]:
        """API 실패시 폴백 공휴일 데이터"""
        # 고정 공휴일들 (매년 동일)
        fixed_holidays = [
            {"month": 1, "day": 1, "name": "元日", "price_impact": "very_high"},
            {"month": 2, "day": 11, "name": "建国記念の日", "price_impact": "low"},
            {"month": 2, "day": 23, "name": "天皇誕生日", "price_impact": "low"},
            {"month": 4, "day": 29, "name": "昭和の日", "price_impact": "very_high"},
            {"month": 5, "day": 3, "name": "憲法記念日", "price_impact": "very_high"},
            {"month": 5, "day": 4, "name": "みどりの日", "price_impact": "very_high"},
            {"month": 5, "day": 5, "name": "こどもの日", "price_impact": "very_high"},
            {"month": 8, "day": 11, "name": "山の日", "price_impact": "high"},
            {"month": 11, "day": 3, "name": "文化の日", "price_impact": "high"},
            {"month": 11, "day": 23, "name": "勤労感謝の日", "price_impact": "high"},
        ]

        fallback_holidays = []
        for holiday in fixed_holidays:
            date_str = f"{year}-{holiday['month']:02d}-{holiday['day']:02d}"
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            holiday_info = {
                "date": date_str,
                "name": holiday["name"],
                "name_en": self._translate_holiday_name(holiday["name"]),
                "type": "national",
                "season": self._determine_season(parsed_date),
                "price_impact": holiday["price_impact"],
                "description": self._get_holiday_description(holiday["name"]),
            }
            fallback_holidays.append(holiday_info)

        logger.warning(
            f"Using fallback holiday data for {year} "
            f"({len(fallback_holidays)} holidays)"
        )
        return fallback_holidays
