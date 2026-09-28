import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import redis

from app.config.settings import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis 기반 캐시 관리 서비스"""

    def __init__(self):
        """캐시 서비스 초기화"""
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                username=settings.REDIS_USERNAME,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )

            self.redis_client.ping()
            self.is_connected = True
            logger.info("CacheService Redis 연결 성공")
        except Exception as e:
            logger.warning(f"Redis 연결 실패, 메모리 캐시로 대체: {str(e)}")
            self.redis_client = None
            self.is_connected = False
            self._memory_cache = {}  # 대체 메모리 캐시

        # 캐시 키 네이밍 규칙
        self.cache_keys = {
            "regional_prices": "regional_lowest_prices",
            "monthly_data": "monthly_cheapest:{origin}:{year}:{month:02d}",
            "cache_stats": "cache_statistics",
            "date_info": "date_info:{date}",
            "exchange_rate": "exchange_rate:KRW_JPY",
            "airport_search": "airport_search:{query}",
            "performance_metrics": "performance_metrics:{hour}",
        }

    async def get_cache_status(self) -> Dict[str, Any]:
        """
        캐시 시스템 전반 상태 조회

        Returns:
            캐시 상태 정보 딕셔너리
        """
        if not self.is_connected:
            return {
                "cache_type": "memory",
                "status": "degraded",
                "total_keys": len(self._memory_cache),
                "message": "Redis 연결 불가, 메모리 캐시 사용 중",
            }

        try:
            # Redis 기본 정보
            info = self.redis_client.info()

            # 애플리케이션 캐시 키들 조회
            app_keys = self._get_app_cache_keys()

            # 만료 시간별 키 분류
            active_keys = []
            expired_keys = []

            for key in app_keys:
                ttl = self.redis_client.ttl(key)
                if ttl > 0:
                    active_keys.append({"key": key, "ttl": ttl})
                elif ttl == -1:  # 만료 시간 없음
                    active_keys.append({"key": key, "ttl": "never"})
                else:  # ttl == -2 (키 존재하지 않음)
                    expired_keys.append(key)

            # 메모리 사용량 계산
            memory_usage = {
                "used_memory": info.get("used_memory_human", "N/A"),
                "used_memory_rss": info.get("used_memory_rss_human", "N/A"),
                "used_memory_peak": info.get("used_memory_peak_human", "N/A"),
                "memory_fragmentation_ratio": info.get("mem_fragmentation_ratio", 0),
            }

            return {
                "cache_type": "redis",
                "status": "healthy",
                "redis_version": info.get("redis_version", "unknown"),
                "total_keys": len(app_keys),
                "active_keys": len(active_keys),
                "expired_keys": len(expired_keys),
                "memory_usage": memory_usage,
                "uptime_seconds": info.get("uptime_in_seconds", 0),
                "last_updated": datetime.now().isoformat(),
                "key_details": {
                    "active": active_keys[:10],  # 상위 10개만
                    "expired": expired_keys[:5],  # 상위 5개만
                },
                "cache_coverage": {
                    "monthly_data": len(
                        [k for k in app_keys if "monthly_cheapest" in k]
                    ),
                    "regional_prices": 1 if "regional_lowest_prices" in app_keys else 0,
                    "date_info": len([k for k in app_keys if "date_info" in k]),
                    "other": len(
                        [
                            k
                            for k in app_keys
                            if not any(x in k for x in ["monthly", "regional", "date"])
                        ]
                    ),
                },
            }

        except Exception as e:
            logger.error(f"캐시 상태 조회 실패: {str(e)}")
            return {
                "cache_type": "redis",
                "status": "error",
                "error": str(e),
                "last_checked": datetime.now().isoformat(),
            }

    def _get_app_cache_keys(self) -> List[str]:
        """애플리케이션 관련 캐시 키들만 조회"""
        if not self.is_connected:
            return list(self._memory_cache.keys())

        patterns = [
            "monthly_cheapest:*",
            "regional_lowest_prices*",
            "date_info:*",
            "exchange_rate:*",
            "airport_search:*",
            "cache_statistics*",
            "performance_metrics:*",
        ]

        all_keys = set()
        for pattern in patterns:
            cursor = 0
            while True:
                cursor, keys = self.redis_client.scan(
                    cursor=cursor, match=pattern, count=100
                )
                all_keys.update(keys)
                if cursor == 0:
                    break

        return list(all_keys)

    def _import_celery_task(self):
        """Celery 태스크 모듈 임포트"""
        try:
            from app.tasks.monthly_data_collection import collect_monthly_cheapest_data

            return collect_monthly_cheapest_data
        except ImportError as e:
            logger.warning(f"Celery 태스크 모듈 로드 실패: {str(e)}")
            return None

    def _get_months_to_refresh(self):
        """갱신할 월 목록 반환"""
        today = datetime.now().date()
        return [
            (today.year, today.month),
            (
                today.year if today.month < 12 else today.year + 1,
                today.month + 1 if today.month < 12 else 1,
            ),
        ]

    def _should_refresh_cache(self, cache_key: str, force_update: bool) -> bool:
        """캐시 갱신이 필요한지 확인"""
        if force_update:
            return True

        if self.is_connected:
            cached_data = self.redis_client.get(cache_key)
            if not cached_data:
                return True
            try:
                cache_info = json.loads(cached_data)
                expires_at = datetime.fromisoformat(cache_info.get("expires_at", ""))
                return datetime.now() > expires_at
            except (json.JSONDecodeError, ValueError):
                return True
        else:
            return cache_key not in self._memory_cache

    async def refresh_cache(
        self,
        regions: Optional[List[str]] = None,
        force_update: bool = False,
        origin: str = "ICN",
    ) -> Dict[str, Any]:
        """캐시 데이터 갱신"""
        collect_monthly_cheapest_data = self._import_celery_task()
        if not collect_monthly_cheapest_data:
            return {
                "success": False,
                "message": "백그라운드 태스크 시스템을 사용할 수 없습니다",
                "data": {"error": "celery_unavailable"},
            }

        try:
            refresh_info = {
                "started_at": datetime.now().isoformat(),
                "origin": origin,
                "regions": regions or "all",
                "force_update": force_update,
                "tasks_created": [],
            }

            for year, month in self._get_months_to_refresh():
                cache_key = self.cache_keys["monthly_data"].format(
                    origin=origin, year=year, month=month
                )

                if self._should_refresh_cache(cache_key, force_update):
                    task = collect_monthly_cheapest_data.delay(year, month, origin)
                    refresh_info["tasks_created"].append(
                        {
                            "task_id": task.id,
                            "year": year,
                            "month": month,
                            "cache_key": cache_key,
                        }
                    )
                    logger.info(f"캐시 갱신 태스크 생성: {year}-{month:02d}")

            return {
                "success": True,
                "message": f"{len(refresh_info['tasks_created'])}개 갱신 태스크 생성",
                "data": refresh_info,
            }

        except Exception as e:
            logger.error(f"캐시 갱신 실패: {str(e)}")
            return {
                "success": False,
                "message": f"캐시 갱신 실패: {str(e)}",
                "data": {},
            }

    async def get_cache_statistics(self) -> Dict[str, Any]:
        """캐시 사용 통계 조회"""
        if not self.is_connected:
            return {
                "cache_type": "memory",
                "total_keys": len(self._memory_cache),
                "hit_rate": "N/A",
                "message": "메모리 캐시 사용 중",
            }

        try:
            # Redis 정보에서 통계 추출
            info = self.redis_client.info()

            # 캐시 히트율 계산 (Redis 기본 통계 활용)
            keyspace_hits = info.get("keyspace_hits", 0)
            keyspace_misses = info.get("keyspace_misses", 0)
            total_requests = keyspace_hits + keyspace_misses

            hit_rate = (
                (keyspace_hits / total_requests * 100) if total_requests > 0 else 0
            )

            # 애플리케이션별 통계
            app_keys = self._get_app_cache_keys()
            key_types = {}
            for key in app_keys:
                key_type = key.split(":")[0]
                key_types[key_type] = key_types.get(key_type, 0) + 1

            return {
                "cache_hit_rate": round(hit_rate, 2),
                "total_requests": total_requests,
                "cache_hits": keyspace_hits,
                "cache_misses": keyspace_misses,
                "total_app_keys": len(app_keys),
                "key_distribution": key_types,
                "connected_clients": info.get("connected_clients", 0),
                "operations_per_second": info.get("instantaneous_ops_per_sec", 0),
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"캐시 통계 조회 실패: {str(e)}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def _get_memory_cache_keys(
        self, pattern: Optional[str], limit: int
    ) -> Dict[str, Any]:
        """메모리 캐시에서 키 조회"""
        keys = list(self._memory_cache.keys())
        if pattern:
            import fnmatch

            keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]
        return {"keys": keys[:limit], "total": len(keys), "sample_data": {}}

    def _get_redis_cache_keys(
        self, pattern: Optional[str], limit: int
    ) -> Dict[str, Any]:
        """레디스에서 키 조회"""
        search_pattern = pattern or "*"
        all_keys = []
        cursor = 0
        while True:
            cursor, keys = self.redis_client.scan(
                cursor=cursor, match=search_pattern, count=100
            )
            all_keys.extend(keys)
            if cursor == 0:
                break

        limited_keys = all_keys[:limit]
        sample_data = {}
        if limited_keys:
            try:
                sample_key = limited_keys[0]
                sample_value = self.redis_client.get(sample_key)
                if sample_value:
                    sample_data[sample_key] = json.loads(sample_value)
            except (json.JSONDecodeError, Exception):
                sample_data[sample_key] = "데이터 파싱 실패"

        return {
            "keys": limited_keys,
            "total": len(all_keys),
            "pattern": search_pattern,
            "sample_data": sample_data,
        }

    async def get_cache_keys(
        self, pattern: Optional[str] = None, limit: int = 100
    ) -> Dict[str, Any]:
        """캐시 키 목록 조회"""
        if not self.is_connected:
            return self._get_memory_cache_keys(pattern, limit)

        try:
            return self._get_redis_cache_keys(pattern, limit)
        except Exception as e:
            logger.error(f"캐시 키 조회 실패: {str(e)}")
            return {"keys": [], "total": 0, "error": str(e)}

    async def delete_cache_key(self, key: str) -> bool:
        """특정 캐시 키 삭제"""
        if not self.is_connected:
            return self._memory_cache.pop(key, None) is not None

        try:
            result = self.redis_client.delete(key)
            logger.info(f"캐시 키 '{key}' 삭제: {result}")
            return result > 0

        except Exception as e:
            logger.error(f"캐시 키 삭제 실패: {str(e)}")
            return False

    def _cleanup_memory_cache(self) -> int:
        """메모리 캐시 정리"""
        cleaned_count = 0
        current_time = datetime.now()
        expired_keys = []

        for key, value in self._memory_cache.items():
            if isinstance(value, dict) and "expires_at" in value:
                try:
                    expires_at = datetime.fromisoformat(value["expires_at"])
                    if current_time > expires_at:
                        expired_keys.append(key)
                except (ValueError, TypeError):
                    expired_keys.append(key)

        for key in expired_keys:
            del self._memory_cache[key]
            cleaned_count += 1

        while len(self._memory_cache) > 1000:
            oldest_key = next(iter(self._memory_cache))
            del self._memory_cache[oldest_key]
            cleaned_count += 1

        return cleaned_count

    def _cleanup_redis_cache(self) -> int:
        """레디스 캐시 정리"""
        cleaned_count = 0
        app_keys = self._get_app_cache_keys()

        for key in app_keys:
            try:
                data = self.redis_client.get(key)
                if data:
                    cache_info = json.loads(data)
                    expires_at_str = cache_info.get("expires_at")

                    if expires_at_str:
                        expires_at = datetime.fromisoformat(expires_at_str)
                        if datetime.now() > expires_at:
                            self.redis_client.delete(key)
                            cleaned_count += 1

            except (json.JSONDecodeError, ValueError, TypeError):
                self.redis_client.delete(key)
                cleaned_count += 1

        logger.info(f"만료된 캐시 {cleaned_count}개 정리 완료")
        return cleaned_count

    async def cleanup_expired_cache(self) -> Dict[str, Any]:
        """만료된 캐시 데이터 정리"""
        current_time = datetime.now()
        if not self.is_connected:
            cleaned_count = self._cleanup_memory_cache()
            return {
                "cleaned_count": cleaned_count,
                "cache_type": "memory",
                "cleaned_at": current_time.isoformat(),
            }

        try:
            cleaned_count = self._cleanup_redis_cache()
            return {
                "cleaned_count": cleaned_count,
                "cache_type": "redis",
                "cleaned_at": current_time.isoformat(),
            }
        except Exception as e:
            logger.error(f"캐시 정리 실패: {str(e)}")
            return {
                "cleaned_count": 0,
                "error": str(e),
                "cleaned_at": current_time.isoformat(),
            }

    async def get_memory_usage(self) -> Dict[str, Any]:
        """메모리 사용량 상세 조회"""
        if not self.is_connected:
            import sys

            memory_size = sys.getsizeof(self._memory_cache)
            return {
                "cache_type": "memory",
                "total_size_bytes": memory_size,
                "total_keys": len(self._memory_cache),
                "avg_size_per_key": (
                    memory_size / len(self._memory_cache) if self._memory_cache else 0
                ),
            }

        try:
            info = self.redis_client.info("memory")

            # 키별 메모리 사용량 추정
            app_keys = self._get_app_cache_keys()
            key_sizes = {}

            for key in app_keys[:10]:  # 상위 10개만 샘플링 (성능 최적화)
                try:
                    # DEBUG OBJECT 명령으로 메모리 사용량 조회
                    # 주의: 프로덕션에서는 성능에 영향을 줄 수 있음
                    memory_usage = self.redis_client.memory_usage(key)
                    key_sizes[key] = memory_usage
                except (
                    redis.exceptions.ResponseError,
                    redis.exceptions.ConnectionError,
                ) as e:
                    # DEBUG OBJECT를 지원하지 않는 Redis 버전
                    logger.warning(f"Redis memory_usage 명령 실패 ({key}): {e}")
                    try:
                        data = self.redis_client.get(key)
                        if data:
                            key_sizes[key] = len(data.encode("utf-8"))
                    except Exception as fallback_error:
                        logger.error(f"키 크기 측정 실패 ({key}): {fallback_error}")

            # 상위 사용량 키들
            top_keys = sorted(key_sizes.items(), key=lambda x: x[1], reverse=True)[:10]

            return {
                "cache_type": "redis",
                "total_memory": {
                    "used_memory": info.get("used_memory", 0),
                    "used_memory_human": info.get("used_memory_human", "N/A"),
                    "used_memory_rss": info.get("used_memory_rss", 0),
                    "used_memory_peak": info.get("used_memory_peak", 0),
                    "mem_fragmentation_ratio": info.get("mem_fragmentation_ratio", 0),
                },
                "app_cache_info": {
                    "total_app_keys": len(app_keys),
                    "sampled_keys": len(key_sizes),
                    "top_memory_keys": top_keys,
                    "avg_key_size": (
                        sum(key_sizes.values()) / len(key_sizes) if key_sizes else 0
                    ),
                },
                "optimization_suggestions": self._get_optimization_suggestions(
                    info, len(app_keys)
                ),
            }

        except Exception as e:
            logger.error(f"메모리 사용량 조회 실패: {str(e)}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def _get_optimization_suggestions(
        self, memory_info: Dict, app_key_count: int
    ) -> List[str]:
        """메모리 최적화 제안"""
        suggestions = []

        fragmentation_ratio = memory_info.get("mem_fragmentation_ratio", 1.0)
        if fragmentation_ratio > 1.5:
            suggestions.append("메모리 단편화가 높습니다. Redis 재시작을 고려해보세요.")

        if app_key_count > 10000:
            suggestions.append("캐시 키가 너무 많습니다. 만료 시간을 단축하거나 정리 주기를 늘려보세요.")

        used_memory = memory_info.get("used_memory", 0)
        if used_memory > 1024 * 1024 * 1024:  # 1GB 이상
            suggestions.append("메모리 사용량이 높습니다. 캐시 정책을 검토해보세요.")

        return suggestions

    async def get_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """성능 지표 조회"""
        # 실제 구현에서는 시계열 데이터베이스나 모니터링 시스템과 연동
        # 현재는 기본적인 Redis 통계를 반환

        if not self.is_connected:
            return {
                "cache_type": "memory",
                "message": "성능 지표는 Redis 연결 시에만 제공됩니다.",
            }

        try:
            info = self.redis_client.info()

            return {
                "period_hours": hours,
                "current_performance": {
                    "operations_per_second": info.get("instantaneous_ops_per_sec", 0),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "hit_rate": self._calculate_hit_rate(info),
                },
                "recommendations": self._get_performance_recommendations(info),
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def _calculate_hit_rate(self, info: Dict) -> float:
        """히트율 계산"""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0

    def _get_performance_recommendations(self, info: Dict) -> List[str]:
        """성능 개선 권장사항"""
        recommendations = []

        hit_rate = self._calculate_hit_rate(info)
        if hit_rate < 80:
            recommendations.append("캐시 히트율이 낮습니다. 캐시 전략을 검토해보세요.")

        clients = info.get("connected_clients", 0)
        if clients > 100:
            recommendations.append("연결된 클라이언트가 많습니다. 커넥션 풀 설정을 확인해보세요.")

        return recommendations

    async def warmup_cache(
        self, regions: Optional[List[str]] = None, months_ahead: int = 3
    ) -> Dict[str, Any]:
        """캐시 워밍업"""
        try:
            from app.tasks.monthly_data_collection import collect_monthly_cheapest_data
        except ImportError as e:
            logger.warning(f"Celery 태스크 모듈 로드 실패: {str(e)}")
            return {
                "success": False,
                "message": "백그라운드 태스크 시스템을 사용할 수 없습니다",
                "data": {"error": "celery_unavailable"},
            }

        try:
            warmup_info = {
                "started_at": datetime.now().isoformat(),
                "regions": regions or "all",
                "months_ahead": months_ahead,
                "tasks_created": [],
            }

            # 향후 몇 개월치 데이터 미리 준비
            today = datetime.now().date()

            for i in range(months_ahead):
                target_date = today.replace(day=1) + timedelta(days=32 * i)
                target_year = target_date.year
                target_month = target_date.month

                task = collect_monthly_cheapest_data.delay(
                    target_year, target_month, "ICN"
                )
                warmup_info["tasks_created"].append(
                    {"task_id": task.id, "year": target_year, "month": target_month}
                )

            return {
                "success": True,
                "message": f"{len(warmup_info['tasks_created'])}개 워밍업 태스크 생성",
                "data": warmup_info,
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"캐시 워밍업 실패: {str(e)}",
                "data": {},
            }

    async def health_check(self) -> Dict[str, Any]:
        """캐시 서비스 헬스 체크"""
        health_info = {
            "redis_connected": self.is_connected,
            "timestamp": datetime.now().isoformat(),
        }

        if self.is_connected:
            try:
                # 기본 동작 테스트
                test_key = "health_check_test"
                test_value = {"test": True, "timestamp": datetime.now().isoformat()}

                # 쓰기 테스트
                self.redis_client.setex(test_key, 60, json.dumps(test_value))

                # 읽기 테스트
                retrieved = self.redis_client.get(test_key)
                read_success = retrieved is not None

                # 삭제 테스트
                self.redis_client.delete(test_key)

                # Redis 정보 조회
                info = self.redis_client.info()

                health_info.update(
                    {
                        "read_write_test": read_success,
                        "redis_version": info.get("redis_version", "unknown"),
                        "uptime_seconds": info.get("uptime_in_seconds", 0),
                        "memory_usage": info.get("used_memory_human", "N/A"),
                        "connected_clients": info.get("connected_clients", 0),
                    }
                )

            except Exception as e:
                health_info.update({"redis_connected": False, "error": str(e)})
        else:
            health_info.update(
                {
                    "cache_type": "memory_fallback",
                    "memory_keys": len(self._memory_cache),
                }
            )

        return health_info

    # 헬퍼 메서드

    def set_cache(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """캐시 설정 (동기 버전)"""
        try:
            if self.is_connected:
                if isinstance(value, dict):
                    value_str = json.dumps(value, default=str)
                else:
                    value_str = str(value)

                return self.redis_client.setex(key, ttl_seconds, value_str)
            else:
                # 메모리 캐시
                if len(self._memory_cache) >= 1000:
                    oldest_key = next(iter(self._memory_cache))
                    del self._memory_cache[oldest_key]

                self._memory_cache[key] = {
                    "data": value,
                    "expires_at": (
                        datetime.now() + timedelta(seconds=ttl_seconds)
                    ).isoformat(),
                }
                return True

        except Exception as e:
            logger.error(f"캐시 설정 실패 {key}: {str(e)}")
            return False

    def get_cache(self, key: str) -> Optional[Any]:
        """캐시 조회 (동기 버전)"""
        try:
            if self.is_connected:
                value = self.redis_client.get(key)
                if value:
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
                return None
            else:
                # 메모리 캐시
                cached = self._memory_cache.get(key)
                if cached:
                    expires_at = datetime.fromisoformat(cached["expires_at"])
                    if datetime.now() < expires_at:
                        return cached["data"]
                    else:
                        # 만료된 캐시 삭제
                        del self._memory_cache[key]
                return None

        except Exception as e:
            logger.error(f"캐시 조회 실패 {key}: {str(e)}")
            return None

    def delete_cache(self, key: str) -> bool:
        """캐시 삭제 (동기 버전)"""
        try:
            if self.is_connected:
                result = self.redis_client.delete(key)
                return result > 0
            else:
                return self._memory_cache.pop(key, None) is not None
        except Exception as e:
            logger.error(f"캐시 삭제 실패 {key}: {str(e)}")
            return False

    def is_cache_valid(self, key: str) -> bool:
        """캐시 유효성 검사 (동기 버전)"""
        try:
            if self.is_connected:
                ttl = self.redis_client.ttl(key)
                return ttl > 0 or ttl == -1  # -1은 만료시간 없음을 의미
            else:
                cached = self._memory_cache.get(key)
                if cached:
                    expires_at = datetime.fromisoformat(cached["expires_at"])
                    return datetime.now() < expires_at
                return False
        except Exception as e:
            logger.error(f"캐시 유효성 검사 실패 {key}: {str(e)}")
            return False

    def clear_cache_pattern(self, pattern: str) -> int:
        """패턴에 맞는 캐시 삭제 (동기 버전)"""
        try:
            deleted_count = 0
            if self.is_connected:
                cursor = 0
                while True:
                    cursor, keys = self.redis_client.scan(
                        cursor=cursor, match=pattern, count=100
                    )
                    if keys:
                        deleted_count += self.redis_client.delete(*keys)
                    if cursor == 0:
                        break
            else:
                import fnmatch

                keys_to_delete = [
                    k for k in self._memory_cache.keys() if fnmatch.fnmatch(k, pattern)
                ]
                for key in keys_to_delete:
                    del self._memory_cache[key]
                    deleted_count += 1

            logger.info(f"패턴 '{pattern}'에 맞는 캐시 {deleted_count}개 삭제")
            return deleted_count
        except Exception as e:
            logger.error(f"패턴 캐시 삭제 실패 {pattern}: {str(e)}")
            return 0
