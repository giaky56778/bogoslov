import asyncio
import time
import uuid
from dataclasses import dataclass

from cachetools import TTLCache

from settings import TTL, TTL_CHECKED, MAX_CACHE_SIZE

@dataclass
class CachedSearchResult:
    params: dict[str, str]
    result: list[dict[str, object]]

search_result_cache: TTLCache = TTLCache(maxsize=MAX_CACHE_SIZE, ttl=TTL)

async def get_search_result(name: str) -> CachedSearchResult:
    try:
        cached = search_result_cache[name]
    except KeyError:
        raise ValueError('name not found: expired data or not found')

    search_result_cache[name] = cached  # re-set to refresh the TTL
    return cached

async def store_search_result(params: dict[str, str], result: list[dict[str, object]]) -> str:
    name = f"{time.time_ns()}_{uuid.uuid4().hex[:8]}"
    search_result_cache[name] = CachedSearchResult(params=params, result=result)
    return name

async def purge_expired_search_results():
    while True:
        await asyncio.sleep(TTL_CHECKED)
        search_result_cache.expire()
