import json
import logging
import time

from redis.asyncio import Redis

log = logging.getLogger(__name__)


class BaseProvider:
    def __init__(self, name: str, redis: Redis):
        self.name = name
        self.redis = redis

    def _cache_key(self, **filters) -> str:
        return f'neocities:{self.name}:cache:v1:{json.dumps(filters, sort_keys=True)}'

    def _lock_key(self, **filters) -> str:
        return f'neocities:{self.name}:lock:v1:{json.dumps(filters, sort_keys=True)}'

    async def get_cached(self, **filters) -> list[dict] | None:
        try:
            data = await self.redis.get(self._cache_key(**filters))
            if data:
                return json.loads(data).get('sites')
        except Exception as exc:
            log.error('Redis get error: %s', exc)
        return None

    async def is_expired(self, ttl_seconds: float, **filters) -> bool:
        try:
            data = await self.redis.get(self._cache_key(**filters))
            if not data:
                return True
            return (time.time() - json.loads(data).get('timestamp', 0)) > ttl_seconds
        except Exception as exc:
            log.error('Redis check error: %s', exc)
            return True

    async def store_sites(self, sites: list[dict], **filters):
        try:
            await self.redis.set(
                self._cache_key(**filters),
                json.dumps({'sites': sites, 'timestamp': time.time()}),
            )
        except Exception as exc:
            log.error('Redis store error: %s', exc)

    async def refresh(self, **filters) -> list[dict] | None:
        lock_key = self._lock_key(**filters)
        try:
            if not await self.redis.set(lock_key, '1', nx=True, ex=60):
                return await self.get_cached(**filters)
            try:
                sites = await self._fetch(**filters)
                if sites:
                    await self.store_sites(sites, **filters)
                    log.info('%s: cached %d sites filters=%s', self.name, len(sites), filters)
                    return sites
                log.warning('%s: fetch returned nothing filters=%s — backing off 5m', self.name, filters)
                await self._store_backoff(**filters)
                return None
            finally:
                await self.redis.delete(lock_key)
        except Exception as exc:
            log.error('%s: refresh error: %s', self.name, exc)
            return None

    async def _store_backoff(self, backoff: int = 300, **filters):
        try:
            await self.redis.set(
                self._cache_key(**filters),
                json.dumps({'sites': [], 'timestamp': time.time()}),
                ex=backoff,
            )
        except Exception as exc:
            log.error('Redis backoff store error: %s', exc)

    async def _fetch(self, **filters) -> list[dict] | None:
        raise NotImplementedError
