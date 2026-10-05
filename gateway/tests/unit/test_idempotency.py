import asyncio

import pytest

from gateway.adapters.memory import InMemoryIdempotencyStore
from gateway.domain.errors import ConflictError
from gateway.services.idempotency import IdempotentExecutor


@pytest.fixture
def executor() -> IdempotentExecutor:
    return IdempotentExecutor(InMemoryIdempotencyStore(), ttl_seconds=60)


async def test_replays_stored_result(executor: IdempotentExecutor) -> None:
    calls = 0

    async def operation() -> str:
        nonlocal calls
        calls += 1
        return f"result-{calls}"

    assert await executor.run("key", operation) == ("result-1", False)
    assert await executor.run("key", operation) == ("result-1", True)
    assert calls == 1


async def test_releases_key_when_operation_fails(executor: IdempotentExecutor) -> None:
    async def failing() -> str:
        raise RuntimeError("downstream timeout")

    async def succeeding() -> str:
        return "ok"

    with pytest.raises(RuntimeError):
        await executor.run("key", failing)
    assert await executor.run("key", succeeding) == ("ok", False)


async def test_rejects_concurrent_duplicate(executor: IdempotentExecutor) -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow() -> str:
        started.set()
        await release.wait()
        return "done"

    first = asyncio.create_task(executor.run("key", slow))
    await started.wait()
    with pytest.raises(ConflictError):
        await executor.run("key", slow)
    release.set()
    assert await first == ("done", False)
