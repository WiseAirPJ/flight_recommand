import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.services.holiday_cache_service import HolidayCacheService
from app.utils.date_calculator import DateCalculator

logger = logging.getLogger(__name__)


class DateService:
    def __init__(self):
        self.holiday_cache_service = HolidayCacheService()
        self.date_calculator = DateCalculator()
        logger.info("DateService 초기화 완료 (API 기반)")

    async def get_date_info(self, date_str: str) -> Dict[str, Any]:
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            date_info = {
                "date": date_str,
                "weekday": parsed_date.weekday(),
                "weekday_name": ["월", "화", "수", "목", "금", "토", "일"][
                    parsed_date.weekday()
                ],
                "is_weekend": parsed_date.weekday() >= 5,
                "month": parsed_date.month,
                "is_holiday": False,
                "holiday_name": None,
                "season": None,
                "price_impact": "low",
                "description": None,
            }

            holiday_info = await self.holiday_cache_service.get_holiday_by_date(
                date_str
            )

            if holiday_info:
                date_info.update(
                    {
                        "is_holiday": True,
                        "holiday_name": holiday_info["name"],
                        "holiday_name_en": holiday_info.get("name_en", ""),
                        "season": holiday_info["season"],
                        "price_impact": holiday_info["price_impact"],
                        "description": holiday_info["description"],
                    }
                )
            else:
                season_info = self.date_calculator.get_season_info(parsed_date)
                date_info.update(season_info)

            return date_info

        except Exception as e:
            logger.error(f"Error getting date info for {date_str}: {e}")
            return {"error": str(e)}

    async def get_year_holidays(self, year: int) -> List[Dict[str, Any]]:
        try:
            holidays = await self.holiday_cache_service.get_holidays(year)
            return sorted(holidays, key=lambda x: x["date"])

        except Exception as e:
            logger.error(f"Error getting holidays for {year}: {e}")
            return []

    async def get_price_impact_explanation(self, price_impact: str) -> str:
        explanations = {
            "very_high": "연중 최고 성수기로 항공료가 평소보다 50-100% 높습니다.",
            "high": "성수기로 항공료가 평소보다 30-50% 높습니다.",
            "medium": "일반 성수기로 항공료가 평소보다 10-30% 높습니다.",
            "low": "비수기로 항공료가 평소 수준이거나 더 저렴합니다.",
        }
        return explanations.get(price_impact, "정보 없음")

    async def find_cheapest_months(
        self, year: int, exclude_holidays: bool = False
    ) -> List[Dict[str, Any]]:
        try:
            month_scores = []

            holidays = await self.holiday_cache_service.get_holidays(year)
            holiday_by_month = {}

            for holiday in holidays:
                month = int(holiday["date"][5:7])
                if month not in holiday_by_month:
                    holiday_by_month[month] = []
                holiday_by_month[month].append(holiday)

            for month in range(1, 13):
                holiday_count = len(holiday_by_month.get(month, []))

                if exclude_holidays and holiday_count >= 2:
                    continue

                month_char = self.date_calculator.get_month_characteristics(month)

                sample_date = date(year, month, 15)
                season_info = self.date_calculator.get_season_info(sample_date)

                price_impact_scores = {"low": 1, "medium": 3, "high": 5, "very_high": 7}

                base_score = price_impact_scores.get(season_info["price_impact"], 3)
                holiday_penalty = holiday_count * 0.5
                total_score = base_score + holiday_penalty

                month_scores.append(
                    {
                        "month": month,
                        "score": total_score,
                        "holiday_count": holiday_count,
                        "season": season_info["season"],
                        "price_level": month_char.get("price_level", "보통"),
                        "weather": month_char.get("weather", "정보 없음"),
                        "recommendation_level": (
                            "높음"
                            if total_score <= 2
                            else "보통" if total_score <= 3.5 else "낮음"
                        ),
                    }
                )

            month_scores.sort(key=lambda x: x["score"])
            return month_scores

        except Exception as e:
            logger.error(f"Error finding cheapest months for {year}: {e}")
            return []

    async def is_peak_season(self, date_str: str) -> bool:
        try:
            date_info = await self.get_date_info(date_str)
            return date_info.get("price_impact") in ["high", "very_high"]
        except Exception as e:
            logger.error(f"Error checking peak season for {date_str}: {e}")
            return False

    async def get_month_characteristics(self, month: int) -> Dict[str, Any]:
        try:
            return self.date_calculator.get_month_characteristics(month)
        except Exception as e:
            logger.error(f"Error getting month characteristics for {month}: {e}")
            return {}

    async def get_holidays_in_range(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        try:
            return await self.holiday_cache_service.get_holidays_in_range(
                start_date, end_date
            )
        except Exception as e:
            logger.error(
                f"Error getting holidays in range {start_date} to {end_date}: {e}"
            )
            return []

    async def get_cheapest_periods(
        self, year: int, duration_days: int = 7
    ) -> List[Dict[str, Any]]:
        try:
            return self.date_calculator.find_cheapest_periods(year, duration_days)
        except Exception as e:
            logger.error(f"Error finding cheapest periods for {year}: {e}")
            return []

    async def refresh_holiday_cache(self, year: Optional[int] = None) -> bool:
        try:
            return await self.holiday_cache_service.refresh_cache(year)
        except Exception as e:
            logger.error(f"Error refreshing holiday cache: {e}")
            return False

    async def get_service_status(self) -> Dict[str, Any]:
        try:
            cache_stats = await self.holiday_cache_service.get_cache_stats()

            return {
                "service": "DateService",
                "version": "2.0 (API-based)",
                "status": "healthy",
                "features": {
                    "external_api": True,
                    "caching": True,
                    "dynamic_calculation": True,
                    "hardcoded_data": False,
                },
                "cache_stats": cache_stats,
                "supported_years": cache_stats.get("years_cached", []),
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {"service": "DateService", "status": "error", "error": str(e)}
