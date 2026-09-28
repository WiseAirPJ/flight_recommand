"""Cache inspection and maintenance, separate from application cache storage.

These synchronous operations run in FastAPI's worker thread pool or Celery workers.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import redis

from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class CacheAdminService:
    def __init__(self, cache_service=None):
        self.cache = cache_service if cache_service is not None else CacheService()

    @property
    def is_connected(self):
        return self.cache.is_connected

    @property
    def redis_client(self):
        return self.cache.redis_client

    def get_cache_status(self) -> Dict[str, Any]:
        """
        캐시 시스템 전반 상태 조회

        Returns:
            캐시 상태 정보 딕셔너리
        """
        if not self.is_connected:
            return {
                "cache_type": "memory",
                "status": "degraded",
                "total_keys": len(self.cache.memory_summary()["keys"]),
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
                if ttl >= 0:
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
            return self.cache.memory_summary()["keys"]

        patterns = [
            "monthly_cheapest:*",
            "flight_search:*",
            "duration_search:*",
            "cheapest_dates:*",
            "airport_info:*",
            "llm:*",
            "regional_lowest_prices*",
            "date_info:*",
            "exchange_rate:*",
            "airport_search:*",
            "cache_statistics*",
            "performance_metrics:*",
            "holidays:*",
            "popular_routes:*",
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

    def get_cache_statistics(self) -> Dict[str, Any]:
        """캐시 사용 통계 조회"""
        if not self.is_connected:
            return {
                "cache_type": "memory",
                "total_keys": len(self.cache.memory_summary()["keys"]),
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
        keys = self.cache.memory_summary()["keys"]
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
            except Exception:
                sample_data[sample_key] = "데이터 파싱 실패"

        return {
            "keys": limited_keys,
            "total": len(all_keys),
            "pattern": search_pattern,
            "sample_data": sample_data,
        }

    def get_cache_keys(
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

    def delete_cache_key(self, key: str) -> bool:
        return self.cache.delete_cache(key)

    def cleanup_expired_cache(self) -> Dict[str, Any]:
        # Redis owns expiration via SETEX. Payload fields (including expires_at)
        # are application data and must never be interpreted as cache metadata.
        return {
            "cleaned_count": self.cache.cleanup_expired(),
            "cache_type": "redis" if self.is_connected else "memory",
            "cleaned_at": datetime.now().isoformat(),
        }

    def get_memory_usage(self) -> Dict[str, Any]:
        """메모리 사용량 상세 조회"""
        if not self.is_connected:
            summary = self.cache.memory_summary()
            total_keys = len(summary["keys"])
            memory_size = summary["size_bytes"]
            return {
                "cache_type": "memory",
                "total_size_bytes": memory_size,
                "total_keys": total_keys,
                "avg_size_per_key": (memory_size / total_keys if total_keys else 0),
            }

        try:
            info = self.redis_client.info("memory")

            # 키별 메모리 사용량 추정
            app_keys = self._get_app_cache_keys()
            key_sizes = {}

            for key in app_keys[:10]:  # 상위 10개만 샘플링 (성능 최적화)
                try:
                    # MEMORY USAGE may return None when a sampled key expires.
                    memory_usage = self.redis_client.memory_usage(key)
                    if memory_usage is not None:
                        key_sizes[key] = memory_usage
                except (
                    redis.exceptions.ResponseError,
                    redis.exceptions.ConnectionError,
                ) as e:
                    # Fallback when MEMORY USAGE is unavailable.
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
            suggestions.append(
                "캐시 키가 너무 많습니다. 만료 시간을 단축하거나 정리 주기를 늘려보세요."
            )

        used_memory = memory_info.get("used_memory", 0)
        if used_memory > 1024 * 1024 * 1024:  # 1GB 이상
            suggestions.append("메모리 사용량이 높습니다. 캐시 정책을 검토해보세요.")

        return suggestions

    def get_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
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
            recommendations.append(
                "연결된 클라이언트가 많습니다. 커넥션 풀 설정을 확인해보세요."
            )

        return recommendations

    def health_check(self) -> Dict[str, Any]:
        """캐시 서비스 헬스 체크"""
        health_info = {
            "redis_connected": self.is_connected,
            "timestamp": datetime.now().isoformat(),
        }

        if self.is_connected:
            try:
                # 기본 동작 테스트
                test_key = f"cache_health:{uuid4().hex}"
                test_value = {"test": True, "timestamp": datetime.now().isoformat()}

                # 쓰기 테스트
                self.redis_client.setex(test_key, 60, json.dumps(test_value))

                # 읽기 테스트
                retrieved = self.redis_client.get(test_key)
                read_success = retrieved == json.dumps(test_value)

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
                    "memory_keys": len(self.cache.memory_summary()["keys"]),
                }
            )

        return health_info
