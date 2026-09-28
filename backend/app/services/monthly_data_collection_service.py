import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.services.amadeus_service import AmadeusService
from app.services.cache_service import CacheService
from app.services.region_service import RegionService

logger = logging.getLogger(__name__)


class MonthlyDataCollectionService:
    """월간 데이터 수집 및 관리 서비스"""

    def __init__(self):
        """서비스 초기화"""
        self.amadeus_service = AmadeusService()
        self.cache_service = CacheService()
        self.region_service = RegionService()

        # 설정
        self.default_origin = "ICN"
        self.max_regions_per_batch = 5  # 한 번에 처리할 최대 지역 수

        logger.info("MonthlyDataCollectionService 초기화 완료")

    async def collect_month_data(
        self,
        year: int,
        month: int,
        origin: str = "ICN",
        regions: Optional[List[str]] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        특정 월의 지역별 최저가 데이터 수집

        Args:
            year: 수집할 년도
            month: 수집할 월 (1-12)
            origin: 출발지 공항 코드 (기본값: ICN)
            regions: 수집할 지역 ID 리스트 (없으면 전체)
            force_refresh: 강제 갱신 여부

        Returns:
            수집 결과 딕셔너리
        """
        start_time = datetime.now()
        collection_id = f"{year}-{month:02d}-{origin}"

        logger.info(f"월간 데이터 수집 시작: {collection_id}")

        try:
            # 캐시 확인
            cache_result = await self._check_cache(
                year, month, origin, force_refresh, start_time
            )
            if cache_result:
                return cache_result

            # 대상 지역 준비
            target_regions = await self._prepare_target_regions(regions)

            # 데이터 수집
            collection_result = await self._collect_regions_data(
                target_regions, origin, year, month, collection_id, start_time
            )

            # 캐시 저장
            await self._save_to_cache(year, month, origin, collection_result)

            logger.info(
                f"월간 데이터 수집 완료: {collection_id} - "
                f"성공: {collection_result['successful_regions']}/{collection_result['total_regions']}"
            )

            return {
                "success": True,
                "data": collection_result,
                "cache_hit": False,
                "collection_time": collection_result["collection_time_seconds"],
            }

        except Exception as e:
            error_msg = f"월간 데이터 수집 실패 ({collection_id}): {str(e)}"
            logger.error(error_msg)

            return {
                "success": False,
                "error": error_msg,
                "collection_id": collection_id,
                "collection_time": (datetime.now() - start_time).total_seconds(),
            }

    async def _check_cache(
        self,
        year: int,
        month: int,
        origin: str,
        force_refresh: bool,
        start_time: datetime,
    ) -> Optional[Dict[str, Any]]:
        """캐시 확인 및 반환"""
        if force_refresh:
            return None

        cache_key = self.cache_service.cache_keys["monthly_data"].format(
            origin=origin, year=year, month=month
        )

        cached_data = self.cache_service.get_cache(cache_key)
        if cached_data:
            logger.info(f"캐시된 데이터 반환: {cache_key}")
            return {
                "success": True,
                "data": cached_data,
                "cache_hit": True,
                "collection_time": (datetime.now() - start_time).total_seconds(),
            }
        return None

    async def _prepare_target_regions(self, regions: Optional[List[str]]):
        """대상 지역 목록 준비"""
        region_data = await self.region_service.get_all_regions()
        if not region_data.get("success"):
            raise Exception(f"지역 데이터 로드 실패: {region_data.get('message', '')}")

        all_regions = region_data["regions"]

        if regions:
            target_regions = [r for r in all_regions if r.id in regions]
        else:
            target_regions = all_regions

        if not target_regions:
            raise Exception("처리할 지역이 없습니다.")

        logger.info(f"대상 지역 수: {len(target_regions)}")
        return target_regions

    async def _collect_regions_data(
        self,
        target_regions,
        origin: str,
        year: int,
        month: int,
        collection_id: str,
        start_time: datetime,
    ) -> Dict[str, Any]:
        """지역별 데이터 수집"""
        date_ranges = self._generate_date_ranges(year, month)
        region_results = []
        failed_regions = []

        for region in target_regions:
            try:
                region_result = await self._collect_region_data(
                    region, origin, date_ranges
                )
                if region_result:
                    region_results.append(region_result)
                    logger.info(f"지역 데이터 수집 완료: {region.id}")
                else:
                    failed_regions.append(region.id)
                    logger.warning(f"지역 데이터 수집 실패: {region.id}")

            except Exception as e:
                logger.error(f"지역 {region.id} 처리 중 오류: {str(e)}")
                failed_regions.append(region.id)
                continue

        return {
            "collection_id": collection_id,
            "year": year,
            "month": month,
            "origin": origin,
            "total_regions": len(target_regions),
            "successful_regions": len(region_results),
            "failed_regions": len(failed_regions),
            "failed_region_ids": failed_regions,
            "regions_data": region_results,
            "collected_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
            "collection_time_seconds": (datetime.now() - start_time).total_seconds(),
        }

    async def _save_to_cache(
        self, year: int, month: int, origin: str, collection_result: Dict[str, Any]
    ):
        """수집 결과를 캐시에 저장"""
        cache_key = self.cache_service.cache_keys["monthly_data"].format(
            origin=origin, year=year, month=month
        )

        cache_success = self.cache_service.set_cache(
            cache_key, collection_result, ttl_seconds=24 * 3600
        )

        if not cache_success:
            logger.warning(f"캐시 저장 실패: {cache_key}")

    def _generate_date_ranges(self, year: int, month: int) -> List[Dict[str, str]]:
        """해당 월의 날짜 범위 생성 (2-7일 여행 기간)"""
        ranges = []

        # 해당 월의 첫날과 마지막날 계산
        from calendar import monthrange

        _, last_day = monthrange(year, month)

        # 2일~7일 여행 기간으로 가능한 조합 생성
        for day in range(1, last_day - 1):  # 최소 2일 여행을 위해 -1
            for duration in [2, 3, 4, 5, 6, 7]:
                departure_date = datetime(year, month, day)
                return_date = departure_date + timedelta(days=duration)

                # 동일 월내에서만 처리 (단순화)
                if return_date.month == month:
                    ranges.append(
                        {
                            "departure_date": departure_date.strftime("%Y-%m-%d"),
                            "return_date": return_date.strftime("%Y-%m-%d"),
                            "duration": duration,
                        }
                    )

        # 너무 많으면 샘플링 (성능 최적화)
        if len(ranges) > 50:
            # 주요 날짜들만 선별 (월초, 월중, 월말 + 주말)
            import random

            random.seed(year * 12 + month)  # 일관된 샘플링
            ranges = random.sample(ranges, 50)

        return ranges

    async def _collect_region_data(
        self, region, origin: str, date_ranges: List[Dict[str, str]]
    ) -> Optional[Dict[str, Any]]:
        """특정 지역의 최저가 데이터 수집"""

        best_price = None
        best_offer = None
        total_searches = 0
        successful_searches = 0

        # 지역의 주요 공항 사용
        destination = region.main_airport

        for date_range in date_ranges:
            try:
                # 항공편 검색 요청
                search_result = await self.amadeus_service.search_flights(
                    origin=origin,
                    destination=destination,
                    departure_date=date_range["departure_date"],
                    return_date=date_range["return_date"],
                    adults=1,
                )

                total_searches += 1

                if search_result.get("success") and search_result.get("offers"):
                    successful_searches += 1
                    offers = search_result["offers"]

                    # 최저가 찾기
                    for offer in offers:
                        try:
                            price = int(float(offer["price"]["total"]))

                            if best_price is None or price < best_price:
                                best_price = price
                                best_offer = {
                                    "price": price,
                                    "departure_date": date_range["departure_date"],
                                    "return_date": date_range["return_date"],
                                    "duration": date_range["duration"],
                                    "currency": offer["price"].get("currency", "KRW"),
                                    "source": offer.get("source", "unknown"),
                                }
                        except (KeyError, ValueError, TypeError) as e:
                            logger.warning(f"가격 파싱 오류: {str(e)}")
                            continue

                # API 요청 간격 (Rate limiting 방지)
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.warning(f"검색 실패 ({destination}, {date_range}): {str(e)}")
                continue

        if best_offer:
            return {
                "region_id": region.id,
                "region_name": region.name,
                "airport": destination,
                "best_price": best_price,
                "best_offer": best_offer,
                "search_stats": {
                    "total_searches": total_searches,
                    "successful_searches": successful_searches,
                    "success_rate": successful_searches / total_searches
                    if total_searches > 0
                    else 0,
                },
            }

        return None

    async def get_cached_months(self, origin: str = "ICN") -> Dict[str, Any]:
        """캐시된 월간 데이터 목록 조회"""
        try:
            # 캐시에서 월간 데이터 키들 검색
            pattern = f"monthly_cheapest:{origin}:*"
            cache_result = await self.cache_service.get_cache_keys(pattern=pattern)

            cached_months = []
            current_date = datetime.now()

            for key in cache_result.get("keys", []):
                try:
                    # 키에서 년월 추출: monthly_cheapest:ICN:2024:03
                    parts = key.split(":")
                    if len(parts) >= 4:
                        year = int(parts[2])
                        month = int(parts[3])

                        # 데이터 유효성 확인
                        cached_data = self.cache_service.get_cache(key)
                        if cached_data:
                            cached_months.append(
                                {
                                    "year": year,
                                    "month": month,
                                    "cache_key": key,
                                    "has_data": True,
                                    "regions_count": len(
                                        cached_data.get("regions_data", [])
                                    ),
                                    "collection_date": cached_data.get("collected_at"),
                                    "expires_at": cached_data.get("expires_at"),
                                }
                            )

                except (ValueError, IndexError) as e:
                    logger.warning(f"키 파싱 오류 ({key}): {str(e)}")
                    continue

            # 년월별 정렬
            cached_months.sort(key=lambda x: (x["year"], x["month"]))

            # 통계 계산
            months_by_origin = {}
            months_by_origin[origin] = len(cached_months)

            return {
                "success": True,
                "total_cached_months": len(cached_months),
                "months_by_origin": months_by_origin,
                "cached_months": cached_months,
                "current_time": current_date.isoformat(),
            }

        except Exception as e:
            logger.error(f"통계 조회 실패: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "total_cached_months": 0,
                "months_by_origin": {},
            }
