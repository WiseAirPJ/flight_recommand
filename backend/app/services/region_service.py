import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RegionService:
    """일본 지역 및 공항 정보 관리 서비스"""

    def __init__(self):
        """서비스 초기화 및 지역 데이터 로드"""
        self.regions_data = self._load_regions_data()
        logger.info(f"RegionService 초기화 완료: {len(self.regions_data)}개 지역 로드")

    def _load_regions_data(self) -> Dict[str, Any]:
        """
        일본 지역별 공항 데이터 로드
        실제 운영시에는 데이터베이스에서 조회할 수 있음
        """
        return {
            "hokkaido": {
                "id": "hokkaido",
                "name": "홋카이도",
                "name_en": "Hokkaido",
                "main_airport": "CTS",
                "airports": [
                    {
                        "iata": "CTS",
                        "name": "신치토세공항",
                        "city": "삿포로",
                        "is_international": True,
                    },
                    {
                        "iata": "HKD",
                        "name": "하코다테공항",
                        "city": "하코다테",
                        "is_international": False,
                    },
                ],
                # 지도용 폴리곤 좌표 (간소화된 홋카이도 경계)
                "coordinates": [
                    [45.415, 141.346],
                    [45.415, 145.817],
                    [42.063, 145.817],
                    [42.063, 139.676],
                    [43.064, 140.098],
                    [45.415, 141.346],
                ],
            },
            "kanto": {
                "id": "kanto",
                "name": "간토 (도쿄)",
                "name_en": "Kanto (Tokyo)",
                "main_airport": "NRT",
                "airports": [
                    {
                        "iata": "NRT",
                        "name": "나리타국제공항",
                        "city": "도쿄",
                        "is_international": True,
                    },
                    {
                        "iata": "HND",
                        "name": "하네다공항",
                        "city": "도쿄",
                        "is_international": True,
                    },
                    {
                        "iata": "IBR",
                        "name": "이바라키공항",
                        "city": "이바라키",
                        "is_international": False,
                    },
                ],
                "coordinates": [
                    [36.400, 138.722],
                    [36.400, 140.999],
                    [35.135, 140.999],
                    [35.135, 138.722],
                    [36.400, 138.722],
                ],
            },
            "kansai": {
                "id": "kansai",
                "name": "간사이 (오사카)",
                "name_en": "Kansai (Osaka)",
                "main_airport": "KIX",
                "airports": [
                    {
                        "iata": "KIX",
                        "name": "간사이국제공항",
                        "city": "오사카",
                        "is_international": True,
                    },
                    {
                        "iata": "ITM",
                        "name": "이타미공항",
                        "city": "오사카",
                        "is_international": False,
                    },
                    {
                        "iata": "UKB",
                        "name": "고베공항",
                        "city": "고베",
                        "is_international": False,
                    },
                ],
                "coordinates": [
                    [35.650, 133.200],
                    [35.650, 136.900],
                    [33.800, 136.900],
                    [33.800, 133.200],
                    [35.650, 133.200],
                ],
            },
            "chubu": {
                "id": "chubu",
                "name": "중부 (나고야)",
                "name_en": "Chubu (Nagoya)",
                "main_airport": "NGO",
                "airports": [
                    {
                        "iata": "NGO",
                        "name": "주부센토레아국제공항",
                        "city": "나고야",
                        "is_international": True,
                    },
                    {
                        "iata": "KIJ",
                        "name": "니가타공항",
                        "city": "니가타",
                        "is_international": False,
                    },
                    {
                        "iata": "FSZ",
                        "name": "시즈오카공항",
                        "city": "시즈오카",
                        "is_international": False,
                    },
                ],
                "coordinates": [
                    [38.000, 136.500],
                    [38.000, 138.700],
                    [34.500, 138.700],
                    [34.500, 136.500],
                    [38.000, 136.500],
                ],
            },
            "kyushu": {
                "id": "kyushu",
                "name": "규슈 (후쿠오카)",
                "name_en": "Kyushu (Fukuoka)",
                "main_airport": "FUK",
                "airports": [
                    {
                        "iata": "FUK",
                        "name": "후쿠오카공항",
                        "city": "후쿠오카",
                        "is_international": True,
                    },
                    {
                        "iata": "NGS",
                        "name": "나가사키공항",
                        "city": "나가사키",
                        "is_international": False,
                    },
                    {
                        "iata": "KMJ",
                        "name": "구마모토공항",
                        "city": "구마모토",
                        "is_international": False,
                    },
                    {
                        "iata": "KOJ",
                        "name": "가고시마공항",
                        "city": "가고시마",
                        "is_international": False,
                    },
                ],
                "coordinates": [
                    [34.000, 129.500],
                    [34.000, 131.500],
                    [31.000, 131.500],
                    [31.000, 129.500],
                    [34.000, 129.500],
                ],
            },
            "okinawa": {
                "id": "okinawa",
                "name": "오키나와",
                "name_en": "Okinawa",
                "main_airport": "OKA",
                "airports": [
                    {
                        "iata": "OKA",
                        "name": "나하공항",
                        "city": "나하",
                        "is_international": True,
                    },
                    {
                        "iata": "ISG",
                        "name": "이시가키공항",
                        "city": "이시가키",
                        "is_international": False,
                    },
                ],
                "coordinates": [
                    [26.500, 127.500],
                    [26.500, 128.500],
                    [24.000, 128.500],
                    [24.000, 127.500],
                    [26.500, 127.500],
                ],
            },
        }

    async def get_all_regions(self) -> Dict[str, Any]:
        """
        모든 지역 정보 조회

        Returns:
            지역별 상세 정보 딕셔너리
        """
        return self.regions_data

    async def get_region_by_id(self, region_id: str) -> Optional[Dict[str, Any]]:
        """
        특정 지역 정보 조회

        Args:
            region_id: 지역 ID (예: 'hokkaido', 'kanto')

        Returns:
            지역 정보 또는 None
        """
        return self.regions_data.get(region_id)

    async def get_region_airports(self, region_id: str) -> List[Dict[str, Any]]:
        """
        특정 지역의 공항 목록 조회

        Args:
            region_id: 지역 ID

        Returns:
            공항 정보 리스트
        """
        region = await self.get_region_by_id(region_id)
        return region.get("airports", []) if region else []

    async def get_main_airport(self, region_id: str) -> Optional[str]:
        """
        지역의 주요 공항 IATA 코드 조회

        Args:
            region_id: 지역 ID

        Returns:
            주요 공항 IATA 코드 또는 None
        """
        region = await self.get_region_by_id(region_id)
        return region.get("main_airport") if region else None

    async def search_airports(self, query: str) -> List[Dict[str, Any]]:
        """
        공항 검색 (자동완성용)

        Args:
            query: 검색어 (공항명, 도시명, IATA 코드)

        Returns:
            검색 결과 공항 리스트
        """
        query_lower = query.lower()
        results = []

        for region_data in self.regions_data.values():
            for airport in region_data["airports"]:
                # IATA 코드, 공항명, 도시명으로 검색
                if (
                    query_lower in airport["iata"].lower()
                    or query_lower in airport["name"].lower()
                    or query_lower in airport["city"].lower()
                ):
                    # 지역 정보도 함께 포함
                    airport_with_region = airport.copy()
                    airport_with_region["region_id"] = region_data["id"]
                    airport_with_region["region_name"] = region_data["name"]
                    results.append(airport_with_region)

        # 국제공항을 우선으로 정렬
        results.sort(key=lambda x: (not x.get("is_international", False), x["name"]))

        return results[:10]  # 상위 10개만 반환

    async def get_region_by_airport(
        self, airport_iata: str
    ) -> Optional[Dict[str, Any]]:
        """
        공항 코드로 지역 정보 조회

        Args:
            airport_iata: 공항 IATA 코드

        Returns:
            해당 공항이 속한 지역 정보
        """
        for region_data in self.regions_data.values():
            for airport in region_data["airports"]:
                if airport["iata"] == airport_iata.upper():
                    return region_data
        return None

    async def get_international_airports(self) -> List[Dict[str, Any]]:
        """
        모든 국제공항 목록 조회

        Returns:
            국제공항 리스트
        """
        international_airports = []

        for region_data in self.regions_data.values():
            for airport in region_data["airports"]:
                if airport.get("is_international", False):
                    airport_with_region = airport.copy()
                    airport_with_region["region_id"] = region_data["id"]
                    airport_with_region["region_name"] = region_data["name"]
                    international_airports.append(airport_with_region)

        return international_airports

    async def get_regions_summary(self) -> Dict[str, Any]:
        """
        지역 요약 통계

        Returns:
            지역 관련 통계 정보
        """
        total_airports = 0
        international_count = 0

        for region_data in self.regions_data.values():
            total_airports += len(region_data["airports"])
            international_count += sum(
                1
                for airport in region_data["airports"]
                if airport.get("is_international", False)
            )

        return {
            "total_regions": len(self.regions_data),
            "total_airports": total_airports,
            "international_airports": international_count,
            "domestic_airports": total_airports - international_count,
            "regions_list": [
                {
                    "id": region["id"],
                    "name": region["name"],
                    "airport_count": len(region["airports"]),
                }
                for region in self.regions_data.values()
            ],
        }

    def get_region_coordinates(self, region_id: str) -> Optional[List[List[float]]]:
        """
        지역의 지도 폴리곤 좌표 조회

        Args:
            region_id: 지역 ID

        Returns:
            폴리곤 좌표 리스트 또는 None
        """
        region = self.regions_data.get(region_id)
        return region.get("coordinates") if region else None

    def is_valid_region(self, region_id: str) -> bool:
        """
        유효한 지역 ID인지 확인

        Args:
            region_id: 검증할 지역 ID

        Returns:
            유효성 여부
        """
        return region_id in self.regions_data
