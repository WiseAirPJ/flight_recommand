import logging
from typing import Dict

logger = logging.getLogger(__name__)


class EfficiencyPromptBuilder:
    """효율성 점수 계산을 위한 프롬프트"""

    EFFICIENCY_SCORE_PROMPT_TEMPLATE = """
당신은 여행 효율성 전문 분석가입니다.
다음 항공편의 여행 효율 점수를 100점 만점으로 계산하고, 그 근거를 제시해주세요.

 **평가 기준**
1. 시간 효율성 (40%): 출발/도착 시간의 합리성
   - 오전 출발 (8-11시): 높은 점수
   - 저녁 도착 (18-21시): 높은 점수
   - 새벽/심야 시간대: 낮은 점수

2. 가격 대비 가치 (35%): 다른 옵션 대비 가격 경쟁력
   - 시장 평균 대비 저렴: 높은 점수
   - 시장 평균 대비 비쌈: 낮은 점수

3. 편의성 (25%): 경유 횟수, 총 소요시간
   - 직항: 높은 점수
   - 1회 경유: 보통 점수
   - 2회 이상 경유: 낮은 점수

**항공편 정보**
{flight_data}

**컨텍스트 정보**
{context}

**요청사항**
다음 JSON 형식으로 정확히 응답해주세요:

{{
    "efficiency_score": 점수(0-100 정수),
    "summary": "한 문장으로 이 항공편의 핵심 특징 요약",
    "breakdown": {{
        "time_score": 시간효율성점수(0-100),
        "price_score": 가격점수(0-100),
        "convenience_score": 편의성점수(0-100)
    }},
    "recommendations": "예약 권장사항 또는 주의사항"
}}

JSON 형식만 응답하고, 다른 텍스트는 포함하지 마세요.
"""

    def build_efficiency_prompt(self, flight_data: Dict, context: Dict = None) -> str:
        """효율성 분석 프롬프트 생성"""
        formatted_flight = self._format_flight_data(flight_data)
        formatted_context = self._format_context(context or {})

        return self.EFFICIENCY_SCORE_PROMPT_TEMPLATE.format(
            flight_data=formatted_flight, context=formatted_context
        )

    def _format_flight_data(self, flight_data: Dict) -> str:
        """항공편 데이터 포맷팅"""
        try:
            price_info = flight_data.get("price", {})
            price = price_info.get("total", "정보 없음")
            currency = price_info.get("currency", "KRW")

            itineraries = flight_data.get("itineraries", [])

            formatted = f"가격: {price} {currency}\n"

            for i, itinerary in enumerate(itineraries):
                formatted += f"\n{i + 1}번째 여정:\n"
                formatted += (
                    f"  총 소요시간: {itinerary.get('duration', '정보 없음')}\n"
                )

                segments = itinerary.get("segments", [])
                for j, segment in enumerate(segments):
                    departure = segment.get("departure", {})
                    arrival = segment.get("arrival", {})

                    formatted += f"  구간 {j + 1}: {departure.get('iataCode', '')} → {arrival.get('iataCode', '')}\n"
                    formatted += f"    출발: {departure.get('at', '정보 없음')}\n"
                    formatted += f"    도착: {arrival.get('at', '정보 없음')}\n"
                    formatted += (
                        f"    항공사: {segment.get('carrierCode', '정보 없음')}\n"
                    )

            return formatted

        except Exception as e:
            logger.error(f"항공편 데이터 포맷팅 실패: {str(e)}")
            return f"항공편 데이터: {str(flight_data)}"

    def _format_context(self, context: Dict) -> str:
        """컨텍스트 정보 포맷팅"""
        if not context:
            return "추가 컨텍스트 없음"

        formatted = ""
        if "travel_preferences" in context:
            prefs = context["travel_preferences"]
            formatted += f"여행 선호도: {prefs}\n"

        if "date_info" in context:
            date_info = context["date_info"]
            formatted += f"날짜 정보: {date_info}\n"

        if "comparison_flights" in context:
            flights_count = len(context["comparison_flights"])
            formatted += f"비교 대상: {flights_count}개 항공편\n"

        return formatted if formatted else "추가 컨텍스트 없음"
