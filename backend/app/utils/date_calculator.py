from datetime import date, timedelta
from typing import Any, Dict, List, Optional


class DateCalculator:
    """날짜 계산 및 시즌 분석 유틸리티"""

    @staticmethod
    def get_season_info(target_date: date) -> Dict[str, Any]:
        """
        날짜의 시즌 정보 동적 계산

        Args:
            target_date: 대상 날짜

        Returns:
            시즌 정보 딕셔너리
        """
        month = target_date.month

        # 특별 기간 우선 체크
        special_period = DateCalculator._check_special_periods(target_date)
        if special_period:
            return special_period

        # 기본 시즌 분류
        season_mapping = {
            "spring": {
                "months": [3, 4, 5],
                "name": "봄",
                "characteristics": ["벚꽃", "온화한 날씨", "관광 성수기"],
                "base_price_impact": "high",
            },
            "summer": {
                "months": [6, 7, 8],
                "name": "여름",
                "characteristics": ["더운 날씨", "여름휴가", "습한 기후"],
                "base_price_impact": "medium",
            },
            "autumn": {
                "months": [9, 10, 11],
                "name": "가을",
                "characteristics": ["단풍", "선선한 날씨", "관광 성수기"],
                "base_price_impact": "high",
            },
            "winter": {
                "months": [12, 1, 2],
                "name": "겨울",
                "characteristics": ["추운 날씨", "비교적 한적", "스키 시즌"],
                "base_price_impact": "low",
            },
        }

        # 해당 월의 시즌 찾기
        for season_key, season_data in season_mapping.items():
            if month in season_data["months"]:
                price_impact = DateCalculator._calculate_seasonal_price_impact(
                    target_date, season_key, season_data["base_price_impact"]
                )

                return {
                    "season": season_key,
                    "season_name": season_data["name"],
                    "price_impact": price_impact,
                    "characteristics": season_data["characteristics"],
                    "description": DateCalculator._get_seasonal_description(
                        target_date, season_key
                    ),
                }

        # 기본값 (예외 상황)
        return {
            "season": "unknown",
            "season_name": "미분류",
            "price_impact": "medium",
            "characteristics": [],
            "description": "시즌 정보 없음",
        }

    @staticmethod
    def _check_special_periods(target_date: date) -> Optional[Dict[str, Any]]:
        """특별 기간 확인"""
        month = target_date.month
        day = target_date.day

        special_periods = [
            {
                "condition": lambda m, d: (m == 4 and d >= 29) or (m == 5 and d <= 5),
                "info": {
                    "season": "golden_week",
                    "season_name": "골든위크",
                    "price_impact": "very_high",
                    "characteristics": ["연휴", "최고 성수기", "교통 혼잡"],
                    "description": "골든위크 연휴 기간",
                },
            },
            {
                "condition": lambda m, d: m == 8 and 13 <= d <= 16,
                "info": {
                    "season": "obon",
                    "season_name": "오봉",
                    "price_impact": "high",
                    "characteristics": ["귀성철", "전통 명절", "교통 혼잡"],
                    "description": "오봉 귀성철 기간",
                },
            },
            {
                "condition": lambda m, d: (m == 12 and d >= 25) or (m == 1 and d <= 7),
                "info": {
                    "season": "winter_holiday",
                    "season_name": "연말연시",
                    "price_impact": "very_high",
                    "characteristics": ["연말연시", "최고 성수기", "휴가철"],
                    "description": "연말연시 휴가 기간",
                },
            },
            {
                "condition": lambda m, d: m == 9 and 15 <= d <= 23,
                "info": {
                    "season": "silver_week",
                    "season_name": "실버위크",
                    "price_impact": "high",
                    "characteristics": ["가을 연휴", "단풍 시즌", "관광 성수기"],
                    "description": "실버위크 연휴 기간",
                },
            },
        ]

        for period in special_periods:
            if period["condition"](month, day):
                return period["info"]

        return None

    @staticmethod
    def _calculate_seasonal_price_impact(
        target_date: date, season: str, base_impact: str
    ) -> str:
        """시즌별 세부 가격 영향도 계산"""
        month = target_date.month
        day = target_date.day

        # 시즌별 세부 조정
        season_mapping = {
            "spring": DateCalculator._get_spring_impact,
            "summer": DateCalculator._get_summer_impact,
            "autumn": DateCalculator._get_autumn_impact,
            "winter": DateCalculator._get_winter_impact,
        }

        calculator = season_mapping.get(season)
        if calculator:
            return calculator(month, day, base_impact)
        return base_impact

    @staticmethod
    def _get_spring_impact(month: int, day: int, base_impact: str) -> str:
        if month == 4:  # 벚꽃 절정기
            return "very_high"
        elif month == 3 and day >= 20:  # 벚꽃 시작
            return "high"
        return base_impact

    @staticmethod
    def _get_summer_impact(month: int, day: int, base_impact: str) -> str:
        if month in [7, 8]:  # 여름휴가철
            return "high"
        return base_impact

    @staticmethod
    def _get_autumn_impact(month: int, day: int, base_impact: str) -> str:
        if month in [10, 11]:  # 단풍 시즌
            return "high"
        return "medium"

    @staticmethod
    def _get_winter_impact(month: int, day: int, base_impact: str) -> str:
        if month == 12 and day >= 20:  # 연말 시작
            return "high"
        elif month == 1 and day <= 10:  # 신정 연휴
            return "high"
        return base_impact

    @staticmethod
    def _get_seasonal_description(target_date: date, season: str) -> str:
        """시즌별 상세 설명 생성"""
        month = target_date.month

        descriptions = {
            "spring": {
                3: "봄 시작, 벚꽃 개화 준비",
                4: "벚꽃 절정기, 최고 성수기",
                5: "신록 시즌, 쾌적한 날씨",
            },
            "summer": {
                6: "장마철 시작, 습한 날씨",
                7: "여름휴가철, 더운 날씨",
                8: "한여름, 오봉 기간 포함",
            },
            "autumn": {
                9: "초가을, 선선한 날씨 시작",
                10: "단풍 시작, 관광 성수기",
                11: "단풍 절정, 가을 관광 최적기",
            },
            "winter": {
                12: "겨울 시작, 연말 분위기",
                1: "신정 연휴, 겨울 관광",
                2: "겨울 비수기, 가장 저렴한 시기",
            },
        }

        return descriptions.get(season, {}).get(month, f"{season} 시즌")

    @staticmethod
    def get_month_characteristics(month: int) -> Dict[str, Any]:
        """월별 특징 정보"""
        characteristics = {
            1: {
                "weather": "추움 (-5~10°C)",
                "crowds": "낮음 (신정 연휴 제외)",
                "price_level": "저렴",
                "events": ["신정", "겨울 일루미네이션"],
                "recommended_activities": ["온천", "스키", "실내 관광"],
                "clothing": "두꺼운 겨울옷 필수",
            },
            2: {
                "weather": "추움 (0~12°C)",
                "crowds": "가장 낮음",
                "price_level": "가장 저렴",
                "events": ["매화 개화", "설분"],
                "recommended_activities": ["온천", "매화 구경", "겨울 축제"],
                "clothing": "겨울옷, 방한용품",
            },
            3: {
                "weather": "쌀쌀함 (5~15°C)",
                "crowds": "증가",
                "price_level": "상승",
                "events": ["벚꽃 개화 시작", "춘분"],
                "recommended_activities": ["벚꽃 구경 준비", "하이킹"],
                "clothing": "얇은 겨울옷, 봄옷 준비",
            },
            4: {
                "weather": "온화함 (10~20°C)",
                "crowds": "최고",
                "price_level": "최고",
                "events": ["벚꽃 절정", "골든위크"],
                "recommended_activities": ["벚꽃 구경", "야외 활동", "피크닉"],
                "clothing": "봄옷, 가벼운 자켓",
            },
            5: {
                "weather": "쾌적함 (15~25°C)",
                "crowds": "높음",
                "price_level": "높음",
                "events": ["신록", "골든위크"],
                "recommended_activities": ["하이킹", "야외 관광", "정원 구경"],
                "clothing": "봄옷, 얇은 긴팔",
            },
            6: {
                "weather": "습함 (20~28°C)",
                "crowds": "보통",
                "price_level": "보통",
                "events": ["장마철", "수국 개화"],
                "recommended_activities": ["실내 관광", "박물관", "온천"],
                "clothing": "우산 필수, 통풍 좋은 옷",
            },
            7: {
                "weather": "더움 (25~35°C)",
                "crowds": "높음",
                "price_level": "높음",
                "events": ["여름축제", "불꽃놀이"],
                "recommended_activities": ["해수욕", "축제", "에어컨 시설"],
                "clothing": "여름옷, 자외선 차단용품",
            },
            8: {
                "weather": "매우 더움 (27~37°C)",
                "crowds": "높음",
                "price_level": "높음",
                "events": ["오봉", "여름축제"],
                "recommended_activities": ["해수욕", "실내 관광", "냉방 시설"],
                "clothing": "여름옷, 모자, 선글라스",
            },
            9: {
                "weather": "선선함 (20~28°C)",
                "crowds": "보통",
                "price_level": "보통",
                "events": ["초가을", "코스모스"],
                "recommended_activities": ["하이킹", "야외 활동 재개"],
                "clothing": "가을옷, 얇은 긴팔",
            },
            10: {
                "weather": "쾌적함 (15~23°C)",
                "crowds": "높음",
                "price_level": "높음",
                "events": ["단풍 시작", "가을축제"],
                "recommended_activities": ["단풍 구경", "하이킹", "온천"],
                "clothing": "가을옷, 가벼운 자켓",
            },
            11: {
                "weather": "선선함 (10~18°C)",
                "crowds": "높음",
                "price_level": "높음",
                "events": ["단풍 절정", "가을 단풍축제"],
                "recommended_activities": ["단풍 관광", "하이킹", "사진 촬영"],
                "clothing": "가을옷, 두꺼운 자켓",
            },
            12: {
                "weather": "추움 (5~12°C)",
                "crowds": "보통",
                "price_level": "보통",
                "events": ["연말", "크리스마스", "일루미네이션"],
                "recommended_activities": ["일루미네이션", "온천", "실내 관광"],
                "clothing": "겨울옷, 코트",
            },
        }

        return characteristics.get(month, {})

    @staticmethod
    def find_cheapest_periods(
        year: int, duration_days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        가장 저렴한 여행 기간 찾기

        Args:
            year: 대상 연도
            duration_days: 여행 기간

        Returns:
            저렴한 기간 리스트
        """
        cheap_periods = []

        # 월별 기본 점수는 사용하지 않음 (season_info로 대체)

        current_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        while current_date <= end_date:
            # duration_days 기간의 평균 점수 계산
            period_scores = []
            period_end = current_date + timedelta(days=duration_days - 1)

            if period_end > end_date:
                break

            check_date = current_date
            while check_date <= period_end:
                season_info = DateCalculator.get_season_info(check_date)

                # 가격 영향도를 점수로 변환
                impact_scores = {"low": 1, "medium": 3, "high": 5, "very_high": 7}

                score = impact_scores.get(season_info["price_impact"], 3)
                period_scores.append(score)
                check_date += timedelta(days=1)

            avg_score = sum(period_scores) / len(period_scores)

            # 저렴한 기간만 추가 (평균 점수 3 이하)
            if avg_score <= 3:
                cheap_periods.append(
                    {
                        "start_date": current_date.strftime("%Y-%m-%d"),
                        "end_date": period_end.strftime("%Y-%m-%d"),
                        "duration_days": duration_days,
                        "avg_score": avg_score,
                        "price_level": "저렴" if avg_score <= 2 else "보통",
                        "season": DateCalculator.get_season_info(current_date)[
                            "season"
                        ],
                        "description": f"{current_date.month}월 여행 추천 기간",
                    }
                )

            current_date += timedelta(days=1)

        # 점수 낮은 순 정렬
        cheap_periods.sort(key=lambda x: x["avg_score"])

        return cheap_periods[:20]  # 상위 20개만 반환
