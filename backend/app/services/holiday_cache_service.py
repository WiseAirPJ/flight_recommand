import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services.cache_service import CacheService
from app.services.holiday_api_client import HolidayAPIClient

logger = logging.getLogger(__name__)


class HolidayCacheService:
    """공휴일 데이터 캐싱 관리 서비스"""

    def __init__(self):
        self.cache_service = CacheService()
        self.api_client = HolidayAPIClient()
        self.cache_ttl = 86400  # 24시간

    async def get_holidays(
        self, year: int, force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """
        연도별 공휴일 조회 (캐시 우선)

        Args:
            year: 조회할 연도
            force_refresh: 강제 새로고침 여부

        Returns:
            공휴일 정보 리스트
        """
        cache_key = f"holidays:{year}"

        # 강제 새로고침이 아닌 경우 캐시 확인
        if not force_refresh:
            cached_data = self.cache_service.get_cache(cache_key)
            if cached_data:
                logger.info(f"Holiday data for {year} retrieved from cache")
                return cached_data

        # API에서 새 데이터 조회
        try:
            holidays = await self.api_client.get_holidays(year)

            # 캐시에 저장
            if holidays:
                self.cache_service.set_cache(cache_key, holidays, self.cache_ttl)
                logger.info(
                    f"Holiday data for {year} cached successfully "
                    f"({len(holidays)} holidays)"
                )

            return holidays

        except Exception as e:
            logger.error(f"Failed to fetch holidays for {year}: {e}")

            # 캐시에 오래된 데이터라도 있으면 사용
            cached_data = self.cache_service.get_cache(cache_key)
            if cached_data:
                logger.warning(f"Using stale cached data for {year}")
                return cached_data

            # 캐시도 없으면 빈 리스트 반환
            return []

    async def get_holiday_by_date(self, date_str: str) -> Optional[Dict[str, Any]]:
        """
        특정 날짜의 공휴일 정보 조회

        Args:
            date_str: 날짜 문자열 (YYYY-MM-DD)

        Returns:
            공휴일 정보 또는 None
        """
        try:
            year = int(date_str[:4])
            holidays = await self.get_holidays(year)

            for holiday in holidays:
                if holiday["date"] == date_str:
                    return holiday

            return None

        except Exception as e:
            logger.error(f"Error getting holiday for date {date_str}: {e}")
            return None

    async def get_holidays_in_range(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """
        날짜 범위의 공휴일 조회

        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)

        Returns:
            해당 기간의 공휴일 리스트
        """
        try:
            start_year = int(start_date[:4])
            end_year = int(end_date[:4])

            all_holidays = []

            # 연도별로 공휴일 조회
            for year in range(start_year, end_year + 1):
                holidays = await self.get_holidays(year)
                all_holidays.extend(holidays)

            # 날짜 범위 필터링
            filtered_holidays = [
                holiday
                for holiday in all_holidays
                if start_date <= holiday["date"] <= end_date
            ]

            # 날짜순 정렬
            filtered_holidays.sort(key=lambda x: x["date"])

            return filtered_holidays

        except Exception as e:
            logger.error(
                f"Error getting holidays in range {start_date} to {end_date}: {e}"
            )
            return []

    async def preload_holidays(self, years: List[int]) -> Dict[int, int]:
        """
        여러 연도의 공휴일 데이터 미리 로드

        Args:
            years: 로드할 연도 리스트

        Returns:
            연도별 로드된 공휴일 수
        """
        results = {}

        for year in years:
            try:
                holidays = await self.get_holidays(year, force_refresh=True)
                results[year] = len(holidays)
                logger.info(f"Preloaded {len(holidays)} holidays for {year}")

            except Exception as e:
                logger.error(f"Failed to preload holidays for {year}: {e}")
                results[year] = 0

        return results

    async def refresh_cache(self, year: Optional[int] = None) -> bool:
        """
        캐시 새로고침

        Args:
            year: 특정 연도만 새로고침 (None이면 현재/다음년도)

        Returns:
            성공 여부
        """
        try:
            current_year = datetime.now().year

            if year:
                years_to_refresh = [year]
            else:
                # 현재년도와 다음년도
                years_to_refresh = [current_year, current_year + 1]

            success_count = 0

            for year_to_refresh in years_to_refresh:
                try:
                    holidays = await self.get_holidays(
                        year_to_refresh, force_refresh=True
                    )
                    if holidays:
                        success_count += 1
                        logger.info(
                            f"Successfully refreshed cache for {year_to_refresh}"
                        )
                    else:
                        logger.warning(f"No holidays found for {year_to_refresh}")

                except Exception as e:
                    logger.error(f"Failed to refresh cache for {year_to_refresh}: {e}")

            return success_count > 0

        except Exception as e:
            logger.error(f"Error during cache refresh: {e}")
            return False

    async def clear_cache(self, year: Optional[int] = None) -> bool:
        """
        캐시 삭제

        Args:
            year: 특정 연도만 삭제 (None이면 모든 공휴일 캐시)

        Returns:
            성공 여부
        """
        try:
            if year:
                cache_key = f"holidays:{year}"
                await self.cache_service.delete_cache_key(cache_key)
                logger.info(f"Cleared holiday cache for {year}")
            else:
                # 패턴으로 모든 공휴일 캐시 삭제
                # Redis에서 keys 패턴 사용 (실제 구현시 scan 사용 권장)
                for year_to_clear in range(2020, 2030):  # 범위 제한
                    cache_key = f"holidays:{year_to_clear}"
                    await self.cache_service.delete_cache_key(cache_key)

                logger.info("Cleared all holiday cache")

            return True

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False

    async def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 정보"""
        try:
            current_year = datetime.now().year
            stats = {
                "cache_service_active": hasattr(self.cache_service, "redis_client"),
                "years_cached": [],
                "total_holidays_cached": 0,
                "last_updated": {},
            }

            # 최근 몇 년간 캐시 상태 확인
            for year in range(current_year - 1, current_year + 3):
                cache_key = f"holidays:{year}"
                cached_data = self.cache_service.get_cache(cache_key)

                if cached_data:
                    stats["years_cached"].append(year)
                    stats["total_holidays_cached"] += len(cached_data)
                    # 캐시 생성 시간 추정 (실제로는 Redis TTL 확인)
                    stats["last_updated"][year] = "cached"

            return stats

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}
