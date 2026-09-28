import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    import anthropic
except ImportError:
    anthropic = None

import openai

from app.config.settings import settings
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class TrendDirection(Enum):
    UP = "up"
    DOWN = "down"
    STABLE = "stable"


@dataclass
class PriceTrend:
    current_price: float
    trend_direction: TrendDirection
    price_change_percent: float
    predicted_price: Optional[float] = None
    confidence: float = 0.0


@dataclass
class RouteAnalysis:
    route: str
    total_duration: str
    stops: int
    price_efficiency: float
    convenience_score: float
    recommendation_score: float


@dataclass
class FlightAnalysis:
    price_trends: List[PriceTrend]
    route_analysis: List[RouteAnalysis]
    best_deal: Optional[Dict[str, Any]] = None
    recommendations: List[str] = None


@dataclass
class PriceAlert:
    flight_id: str
    threshold_price: float
    user_id: str
    alert_type: str
    created_at: datetime
    is_active: bool = True


class LLMService:
    """LLM 기반 분석 서비스"""

    def __init__(self, cache_service: CacheService = None):
        """LLM 클라이언트 초기화"""
        self.client = self._initialize_client()
        self.model = settings.LLM_MODEL
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.temperature = settings.LLM_TEMPERATURE
        self.cache_service = cache_service or CacheService()
        self.cache_ttl = 300  # 5분
        self.price_history = {}
        self.price_alerts = []

    def _initialize_client(self):
        """LLM 클라이언트 초기화"""
        if settings.LLM_PROVIDER == "azure_openai":
            if not settings.AZURE_OPENAI_API_KEY or not settings.AZURE_OPENAI_ENDPOINT:
                return None

            return openai.AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_version=settings.AZURE_OPENAI_API_VERSION,
            )
        elif settings.LLM_PROVIDER == "openai":
            if not settings.OPENAI_API_KEY:
                return None
            return openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        elif settings.LLM_PROVIDER == "anthropic":
            if not settings.ANTHROPIC_API_KEY or anthropic is None:
                return None
            return anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        else:
            return None

    async def analyze_flights(
        self, flights_data: List[Dict], context: Dict = None
    ) -> Dict[str, Any]:
        """항공편 데이터 분석"""
        try:
            if not self.client:
                return await self._get_dummy_analysis(flights_data)

            if len(flights_data) > settings.MAX_FLIGHTS_PER_ANALYSIS:
                flights_data = flights_data[: settings.MAX_FLIGHTS_PER_ANALYSIS]

            analysis_results = []
            for flight in flights_data:
                efficiency_result = await self.calculate_efficiency_score(
                    flight, context
                )
                analysis_results.append(efficiency_result)

            return {
                "success": True,
                "results": analysis_results,
                "analysis_timestamp": datetime.now().isoformat(),
                "model_used": self.model,
                "context": context or {},
            }
        except Exception as e:
            logger.error(f"항공편 분석 오류:{str(e)}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "analysis_timestamp": datetime.now().isoformat(),
            }

    async def calculate_efficiency_score(
        self, flight_data: Dict, context: Dict = None
    ) -> Dict[str, Any]:
        """항공편의 효율성 점수 계산"""

        try:
            if not self.client:
                return await self._get_dummy_efficiency_score(flight_data)

            from app.utils.prompts.efficiency_prompts import EfficiencyPromptBuilder

            prompt_builder = EfficiencyPromptBuilder()
            prompt = prompt_builder.build_efficiency_prompt(flight_data, context)

            response = await self._call_llm(prompt)
            parsed_response = self._parse_efficiency_response(response)

            parsed_response.update(
                {
                    "flight_id": flight_data.get("id", "unknown"),
                    "analysis_timestamp": datetime.now().isoformat(),
                    "model_used": self.model,
                }
            )

            return parsed_response

        except Exception as e:
            logger.error(f"효율성 점수 계산 실패: {str(e)}")
            return self._get_fallback_analysis(flight_data)

    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """LLM 호출"""
        try:
            if settings.LLM_PROVIDER == "azure_openai":
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                return response.choices[0].message.content

            elif settings.LLM_PROVIDER == "anthropic":
                if anthropic is None:
                    raise ImportError("anthropic 라이브러리가 설치되지 않았습니다.")
                response = await self.client.messages.create(
                    model="claude-3-7-sonnet-20250219",
                    max_tokens=self.max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text
            else:
                response = await self.client.chat.completions.create(
                    model="gpt-4.1",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM API 호출 실패: {str(e)}")
            raise

    async def _parse_efficiency_response(self, response: str) -> Dict[str, Any]:
        """효율적인 답변 파싱"""
        try:
            if response.strip().startswith("{"):
                parsed = json.loads(response)
                return {
                    "efficiency_score": parsed.get("efficiency_score", 0),
                    "summary": parsed.get("summary", "분석 결과 없음"),
                    "breakdown": parsed.get("breakdown", {}),
                    "recommendations": parsed.get("recommendations", ""),
                }
            else:
                return {
                    "efficiency_score": 75,
                    "summary": response[:200],
                    "breakdown": {},
                    "recommendations": "",
                }

        except json.JSONDecodeError:
            logger.warning("LLM 응답 파싱 실패, 기본값 사용")
        return {
            "efficiency_score": 75,
            "summary": "분석 결과를 파싱할 수 없습니다.",
            "breakdown": {},
            "recommendations": "",
        }

    def _parse_price_response(self, response: str) -> Dict[str, Any]:
        """가격 분석 응답 파싱"""
        try:
            if response.strip().startswith("{"):
                parsed = json.loads(response)
                return {
                    "success": True,
                    "factors": parsed.get("factors", []),
                    "summary": parsed.get("summary", ""),
                    "price_prediction": parsed.get("price_prediction", ""),
                    "booking_advice": parsed.get("booking_advice", ""),
                }
            else:
                return {
                    "success": True,
                    "factors": [],
                    "summary": response[:200],
                    "price_prediction": "",
                    "booking_advice": "",
                }

        except json.JSONDecodeError:
            return {"success": False, "error": "응답 파싱 실패", "factors": [], "summary": ""}

    async def _get_dummy_analysis(self, flights_data: List[Dict]) -> Dict[str, Any]:
        """LLM 클라이언트가 없을 때 더미 분석 결과 반환"""
        results = []
        for flight in flights_data:
            results.append(
                {
                    "flight_id": flight.get("id", "unknown"),
                    "efficiency_score": 75,
                    "summary": "LLM 서비스 없이 기본 분석 수행",
                    "breakdown": {
                        "price_score": 70,
                        "time_score": 80,
                        "convenience_score": 75,
                    },
                    "recommendations": "항공편 예약을 고려해보세요.",
                }
            )

        return {
            "success": True,
            "results": results,
            "analysis_timestamp": datetime.now().isoformat(),
            "model_used": "dummy",
            "context": {},
        }

    async def _get_dummy_efficiency_score(self, flight_data: Dict) -> Dict[str, Any]:
        """더미 효율성 점수 반환"""
        return {
            "flight_id": flight_data.get("id", "unknown"),
            "efficiency_score": 75,
            "summary": "LLM 서비스 없이 기본 효율성 점수 계산",
            "breakdown": {"price_score": 70, "time_score": 80, "convenience_score": 75},
            "recommendations": "적절한 항공편입니다.",
            "analysis_timestamp": datetime.now().isoformat(),
            "model_used": "dummy",
        }

    def _get_fallback_analysis(self, flight_data: Dict) -> Dict[str, Any]:
        """오류 시 폴백 분석 결과 반환"""
        return {
            "flight_id": flight_data.get("id", "unknown"),
            "efficiency_score": 50,
            "summary": "분석 중 오류가 발생했습니다.",
            "breakdown": {},
            "recommendations": "다시 시도해주세요.",
            "analysis_timestamp": datetime.now().isoformat(),
            "model_used": "fallback",
        }

    def _get_cache_key(self, query: str, flight_data: List[Dict]) -> str:
        """캐시 키 생성"""
        flight_ids = [f.get("id", "") for f in flight_data]
        return f"{query}:{':'.join(flight_ids)}"

    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """캐시 유효성 검사"""
        return (datetime.now() - timestamp).total_seconds() < self.cache_ttl

    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """캐시에서 데이터 조회"""
        try:
            cached_data = self.cache_service.get_cache(f"llm:{cache_key}")
            if cached_data:
                logger.info(f"캐시에서 데이터 반환: {cache_key}")
                return cached_data
            return None
        except Exception as e:
            logger.error(f"캐시 조회 실패: {e}")
            return None

    def _set_cache(self, cache_key: str, data: Dict) -> None:
        """캐시에 데이터 저장"""
        try:
            self.cache_service.set_cache(f"llm:{cache_key}", data, self.cache_ttl)
            logger.info(f"캐시에 데이터 저장: {cache_key}")
        except Exception as e:
            logger.error(f"캐시 저장 실패: {e}")

    def _update_price_history(self, flight_data: List[Dict]) -> None:
        """가격 히스토리 업데이트"""
        for flight in flight_data:
            flight_id = flight.get("id")
            price_info = flight.get("price", {})
            current_price = (
                price_info.get("total", 0) if isinstance(price_info, dict) else 0
            )

            if flight_id:
                if flight_id not in self.price_history:
                    self.price_history[flight_id] = []

                self.price_history[flight_id].append(
                    {"price": current_price, "timestamp": datetime.now()}
                )

                cutoff_date = datetime.now() - timedelta(days=30)
                self.price_history[flight_id] = [
                    entry
                    for entry in self.price_history[flight_id]
                    if entry["timestamp"] > cutoff_date
                ]

    def _analyze_price_trends(self, flight_data: List[Dict]) -> List[PriceTrend]:
        """가격 트렌드 분석"""
        trends = []

        for flight in flight_data:
            flight_id = flight.get("id")
            price_info = flight.get("price", {})
            current_price = (
                price_info.get("total", 0) if isinstance(price_info, dict) else 0
            )

            if (
                flight_id in self.price_history
                and len(self.price_history[flight_id]) > 1
            ):
                history = self.price_history[flight_id]

                recent_prices = [entry["price"] for entry in history[-7:]]
                avg_old_price = (
                    sum(recent_prices[:-1]) / len(recent_prices[:-1])
                    if len(recent_prices) > 1
                    else current_price
                )

                price_change = (
                    ((current_price - avg_old_price) / avg_old_price) * 100
                    if avg_old_price > 0
                    else 0
                )

                if price_change > 5:
                    trend_direction = TrendDirection.UP
                elif price_change < -5:
                    trend_direction = TrendDirection.DOWN
                else:
                    trend_direction = TrendDirection.STABLE

                if len(recent_prices) >= 3:
                    trend_slope = (recent_prices[-1] - recent_prices[-3]) / 2
                    predicted_price = current_price + trend_slope
                else:
                    predicted_price = None

                trends.append(
                    PriceTrend(
                        current_price=current_price,
                        trend_direction=trend_direction,
                        price_change_percent=price_change,
                        predicted_price=predicted_price,
                        confidence=0.7 if len(recent_prices) >= 5 else 0.4,
                    )
                )
            else:
                trends.append(
                    PriceTrend(
                        current_price=current_price,
                        trend_direction=TrendDirection.STABLE,
                        price_change_percent=0.0,
                        confidence=0.1,
                    )
                )

        return trends

    def _analyze_routes(self, flight_data: List[Dict]) -> List[RouteAnalysis]:
        """경로 분석 및 최적화"""
        route_analyses = []

        for flight in flight_data:
            itinerary = flight.get("itineraries", [{}])[0]
            segments = itinerary.get("segments", [])

            if not segments:
                continue

            route = f"{segments[0].get('departure', {}).get('iataCode', '')} -> {segments[-1].get('arrival', {}).get('iataCode', '')}"
            stops = len(segments) - 1

            total_duration = itinerary.get("duration", "N/A")

            price_info = flight.get("price", {})
            price = price_info.get("total", 0) if isinstance(price_info, dict) else 0
            duration_minutes = self._parse_duration(total_duration)
            price_efficiency = (1 / price) * 1000 if price > 0 else 0

            convenience_score = (100 - stops * 20) - (duration_minutes / 60 * 2)
            convenience_score = max(0, convenience_score)

            recommendation_score = (price_efficiency * 0.4) + (convenience_score * 0.6)

            route_analyses.append(
                RouteAnalysis(
                    route=route,
                    total_duration=total_duration,
                    stops=stops,
                    price_efficiency=price_efficiency,
                    convenience_score=convenience_score,
                    recommendation_score=recommendation_score,
                )
            )

        return sorted(
            route_analyses, key=lambda x: x.recommendation_score, reverse=True
        )

    def _parse_duration(self, duration_str: str) -> int:
        if not duration_str or not duration_str.startswith("PT"):
            return 0

        duration_str = duration_str[2:]
        hours = 0
        minutes = 0

        if "H" in duration_str:
            hours_str = duration_str.split("H")[0]
            hours = int(hours_str) if hours_str.isdigit() else 0
            duration_str = duration_str.split("H")[1]

        if "M" in duration_str:
            minutes_str = duration_str.split("M")[0]
            minutes = int(minutes_str) if minutes_str.isdigit() else 0

        return hours * 60 + minutes

    async def analyze_flights_advanced(
        self, query: str, flight_data: List[Dict]
    ) -> FlightAnalysis:
        """고급 항공편 분석"""
        try:
            cache_key = self._get_cache_key(query, flight_data)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return FlightAnalysis(**cached_result)

            self._update_price_history(flight_data)

            price_trends = self._analyze_price_trends(flight_data)
            route_analysis = self._analyze_routes(flight_data)

            best_deal = None
            if route_analysis:
                best_route = route_analysis[0]
                best_deal = {
                    "route": best_route.route,
                    "score": best_route.recommendation_score,
                    "reason": f"높은 편의성({best_route.convenience_score:.1f})과 가격 효율성({best_route.price_efficiency:.2f})을 보입니다.",
                }

            recommendations = await self._generate_recommendations(
                query, flight_data, price_trends, route_analysis
            )

            result = FlightAnalysis(
                price_trends=price_trends,
                route_analysis=route_analysis,
                best_deal=best_deal,
                recommendations=recommendations,
            )

            self._set_cache(
                cache_key,
                {
                    "price_trends": [trend.__dict__ for trend in result.price_trends],
                    "route_analysis": [
                        route.__dict__ for route in result.route_analysis
                    ],
                    "best_deal": result.best_deal,
                    "recommendations": result.recommendations,
                },
            )

            return result

        except Exception as e:
            logger.error(f"고급 항공편 분석 실패: {e}")
            raise

    async def _generate_recommendations(
        self,
        query: str,
        flight_data: List[Dict],
        price_trends: List[PriceTrend],
        route_analysis: List[RouteAnalysis],
    ) -> List[str]:
        """LLM을 통한 맞춤형 추천 생성"""
        try:
            if not self.client:
                return ["LLM 서비스를 사용할 수 없어 기본 추천을 제공합니다."]

            trend_summary = self._summarize_trends(price_trends)
            route_summary = self._summarize_routes(route_analysis)

            prompt = f"""
            사용자 검색 쿼리: {query}

            가격 트렌드 분석:
            {trend_summary}

            경로 분석:
            {route_summary}

            위 분석을 바탕으로 사용자에게 도움이 될 구체적인 추천사항을 3-5개의 짧은 문장으로 제공해주세요.
            예약 시기, 대안 경로, 가격 절약 팁 등을 포함해주세요.
            """

            response = await self._call_llm(prompt)
            return [rec.strip() for rec in response.split("\n") if rec.strip()]

        except Exception as e:
            logger.error(f"추천 생성 실패: {e}")
            return ["항공편 데이터를 분석했지만 추천 생성에 실패했습니다."]

    def _summarize_trends(self, trends: List[PriceTrend]) -> str:
        """가격 트렌드 요약"""
        if not trends:
            return "가격 트렌드 데이터가 없습니다."

        up_trends = [t for t in trends if t.trend_direction == TrendDirection.UP]
        down_trends = [t for t in trends if t.trend_direction == TrendDirection.DOWN]
        stable_trends = [
            t for t in trends if t.trend_direction == TrendDirection.STABLE
        ]

        avg_price = sum(t.current_price for t in trends) / len(trends)

        return f"""
        - 평균 가격: ${avg_price:.2f}
        - 상승 트렌드: {len(up_trends)}개 항공편
        - 하락 트렌드: {len(down_trends)}개 항공편
        - 안정 트렌드: {len(stable_trends)}개 항공편
        """

    def _summarize_routes(self, routes: List[RouteAnalysis]) -> str:
        """경로 분석 요약"""
        if not routes:
            return "경로 분석 데이터가 없습니다."

        direct_flights = [r for r in routes if r.stops == 0]
        one_stop = [r for r in routes if r.stops == 1]
        multi_stop = [r for r in routes if r.stops > 1]

        best_route = routes[0] if routes else None

        summary = f"""
        - 총 {len(routes)}개 경로 분석
        - 직항: {len(direct_flights)}개, 1회 경유: {len(one_stop)}개, 다회 경유: {len(multi_stop)}개
        """

        if best_route:
            summary += f"- 최고 추천 경로: {best_route.route} (점수: {best_route.recommendation_score:.1f})"

        return summary

    def create_price_alert(
        self,
        flight_id: str,
        threshold_price: float,
        user_id: str,
        alert_type: str = "price_drop",
    ) -> PriceAlert:
        """가격 알림 생성"""
        alert = PriceAlert(
            flight_id=flight_id,
            threshold_price=threshold_price,
            user_id=user_id,
            alert_type=alert_type,
            created_at=datetime.now(),
        )
        self.price_alerts.append(alert)
        return alert

    def check_price_alerts(self, flight_data: List[Dict]) -> List[Dict]:
        """가격 알림 확인"""
        triggered_alerts = []

        for flight in flight_data:
            flight_id = flight.get("id")
            price_info = flight.get("price", {})
            current_price = (
                price_info.get("total", 0) if isinstance(price_info, dict) else 0
            )

            for alert in self.price_alerts:
                if alert.flight_id == flight_id and alert.is_active:
                    if (
                        alert.alert_type == "price_drop"
                        and current_price <= alert.threshold_price
                    ):
                        triggered_alerts.append(
                            {
                                "alert": alert,
                                "flight": flight,
                                "message": f"가격이 ${alert.threshold_price}보다 낮아졌습니다! 현재 가격: ${current_price}",
                            }
                        )
                        alert.is_active = False

        return triggered_alerts

    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 정보"""
        try:
            return {
                "service_type": "llm",
                "cache_backend": "CacheService",
                "ttl_seconds": self.cache_ttl,
                "cache_service_stats": "Use CacheService.get_cache_statistics() for detailed stats"
            }
        except Exception as e:
            logger.error(f"캐시 통계 조회 실패: {e}")
            return {"error": str(e)}
