from copy import deepcopy
from functools import wraps
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException

from app.services.cache_service import CacheService


def cached_response(
    cache_key_func: Callable[..., str],
    ttl_seconds: int = 900,
    cache_service: Optional[CacheService] = None,
):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_svc = cache_service or kwargs.get("cache_service")
            if not cache_svc:
                return await func(*args, **kwargs)

            cache_key = cache_key_func(*args, **kwargs)

            cached_result = deepcopy(cache_svc.get_cache(cache_key))
            if cached_result:
                if isinstance(cached_result, dict) and isinstance(
                    cached_result.get("data"), dict
                ):
                    cached_result["data"]["from_cache"] = True
                return {
                    "success": True,
                    "message": "조회 완료 (캐시됨)",
                    **cached_result,
                }

            result = await func(*args, **kwargs)

            if (
                isinstance(result, dict)
                and result.get("success")
                and not result.get("meta", {}).get("failed_searches")
            ):
                cache_svc.set_cache(cache_key, result, ttl_seconds)

            return result

        return wrapper

    return decorator


def handle_exceptions(error_message: str = "처리 중 오류가 발생했습니다"):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e)) from e
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"{error_message}: {str(e)}"
                )

        return wrapper

    return decorator


def enhance_response(enhancer_func: Callable[..., Dict[str, Any]]):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            if isinstance(result, dict) and result.get("success"):
                enhanced_data = enhancer_func(result, *args, **kwargs)
                result["data"] = enhanced_data

            return result

        return wrapper

    return decorator
