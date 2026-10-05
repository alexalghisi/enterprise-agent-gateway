from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis

from gateway.adapters.memory import (
    InMemoryClaimRepository,
    InMemoryEscalationRepository,
    InMemoryIdempotencyStore,
    InMemoryPolicyRepository,
    SystemClock,
    UuidGenerator,
)
from gateway.adapters.mongo import (
    MongoClaimRepository,
    MongoEscalationRepository,
    MongoPolicyRepository,
    ensure_indexes,
)
from gateway.adapters.redis_store import RedisIdempotencyStore
from gateway.config import Settings
from gateway.container import Container
from gateway.ports import (
    ClaimRepository,
    EscalationRepository,
    IdempotencyStore,
    PolicyRepository,
)
from gateway.security.auth import ApiKeyAuthenticator, CallerSessionSigner
from gateway.seed import DEMO_POLICIES
from gateway.services.idempotency import IdempotentExecutor
from gateway.services.tools import AgentTools


def assemble(
    settings: Settings,
    policies: PolicyRepository,
    claims: ClaimRepository,
    escalations: EscalationRepository,
    idempotency: IdempotencyStore,
) -> Container:
    tools = AgentTools(
        policies=policies,
        claims=claims,
        escalations=escalations,
        sessions=CallerSessionSigner(settings.session_secret, settings.session_ttl_seconds),
        clock=SystemClock(),
        ids=UuidGenerator(),
    )
    return Container(
        tools=tools,
        authenticator=ApiKeyAuthenticator(settings.api_keys),
        idempotency=IdempotentExecutor(idempotency, settings.idempotency_ttl_seconds),
    )


def in_memory_container(settings: Settings) -> Container:
    return assemble(
        settings,
        InMemoryPolicyRepository(DEMO_POLICIES if settings.seed_demo_data else ()),
        InMemoryClaimRepository(),
        InMemoryEscalationRepository(),
        InMemoryIdempotencyStore(),
    )


@asynccontextmanager
async def build_container(settings: Settings) -> AsyncIterator[Container]:
    if settings.mongo_url is None:
        yield in_memory_container(settings)
        return
    mongo: AsyncIOMotorClient[dict[str, object]] = AsyncIOMotorClient(settings.mongo_url)
    redis = Redis.from_url(settings.redis_url) if settings.redis_url else None
    try:
        db = mongo[settings.mongo_database]
        await ensure_indexes(db)
        if settings.seed_demo_data:
            for policy in DEMO_POLICIES:
                await db["policies"].replace_one(
                    {"tenant_id": policy.tenant_id, "policy_number": policy.policy_number},
                    policy.model_dump(mode="json"),
                    upsert=True,
                )
        yield assemble(
            settings,
            MongoPolicyRepository(db),
            MongoClaimRepository(db),
            MongoEscalationRepository(db),
            RedisIdempotencyStore(redis) if redis else InMemoryIdempotencyStore(),
        )
    finally:
        mongo.close()
        if redis is not None:
            await redis.aclose()
