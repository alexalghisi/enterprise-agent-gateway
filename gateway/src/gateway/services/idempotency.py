from __future__ import annotations

from collections.abc import Awaitable, Callable

from gateway.domain.errors import ConflictError
from gateway.ports import IdempotencyStore


class IdempotentExecutor:
    def __init__(self, store: IdempotencyStore, ttl_seconds: int) -> None:
        self._store = store
        self._ttl_seconds = ttl_seconds

    async def run(self, key: str, operation: Callable[[], Awaitable[str]]) -> tuple[str, bool]:
        if not await self._store.reserve(key, self._ttl_seconds):
            stored = await self._store.load(key)
            if stored is None:
                raise ConflictError("A request with this idempotency key is still in progress")
            return stored, True
        try:
            result = await operation()
        except Exception:
            await self._store.release(key)
            raise
        await self._store.save(key, result, self._ttl_seconds)
        return result, False
