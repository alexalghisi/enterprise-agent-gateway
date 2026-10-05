from __future__ import annotations

from redis.asyncio import Redis

_PENDING = "__pending__"


class RedisIdempotencyStore:
    def __init__(self, client: Redis, namespace: str = "idem") -> None:
        self._client = client
        self._namespace = namespace

    def _key(self, key: str) -> str:
        return f"{self._namespace}:{key}"

    async def reserve(self, key: str, ttl_seconds: int) -> bool:
        return bool(await self._client.set(self._key(key), _PENDING, nx=True, ex=ttl_seconds))

    async def save(self, key: str, payload: str, ttl_seconds: int) -> None:
        await self._client.set(self._key(key), payload, ex=ttl_seconds)

    async def load(self, key: str) -> str | None:
        value = await self._client.get(self._key(key))
        if value is None:
            return None
        text = value.decode() if isinstance(value, bytes) else str(value)
        return None if text == _PENDING else text

    async def release(self, key: str) -> None:
        await self._client.delete(self._key(key))
