from datetime import UTC, date, datetime
from typing import Any

import fakeredis
from mongomock_motor import AsyncMongoMockClient
from motor.motor_asyncio import AsyncIOMotorDatabase

from gateway.adapters.mongo import (
    MongoClaimRepository,
    MongoEscalationRepository,
    MongoPolicyRepository,
    ensure_indexes,
)
from gateway.adapters.redis_store import RedisIdempotencyStore
from gateway.domain.models import Claim, ClaimStatus, ClaimType, Escalation
from gateway.seed import DEMO_POLICIES, DEMO_TENANT

CLAIM = Claim(
    claim_id="clm_1",
    tenant_id=DEMO_TENANT,
    policy_number="HH-100234",
    claim_type=ClaimType.THEFT,
    incident_date=date(2026, 2, 2),
    description="Bike stolen from the basement",
    status=ClaimStatus.RECEIVED,
    created_at=datetime(2026, 2, 3, tzinfo=UTC),
)


async def test_mongo_repositories_round_trip() -> None:
    db: AsyncIOMotorDatabase[dict[str, Any]] = AsyncMongoMockClient()["gateway"]
    await ensure_indexes(db)
    policy = DEMO_POLICIES[0]
    await db["policies"].insert_one(policy.model_dump(mode="json"))

    assert await MongoPolicyRepository(db).get(DEMO_TENANT, policy.policy_number) == policy
    assert await MongoPolicyRepository(db).get("other", policy.policy_number) is None

    claims = MongoClaimRepository(db)
    await claims.add(CLAIM)
    assert await claims.get(DEMO_TENANT, "clm_1") == CLAIM
    assert await claims.get("other", "clm_1") is None

    escalation = Escalation(
        escalation_id="esc_1",
        tenant_id=DEMO_TENANT,
        policy_number=None,
        reason="complaint",
        summary="Caller asked for a supervisor",
        created_at=datetime(2026, 2, 3, tzinfo=UTC),
    )
    await MongoEscalationRepository(db).add(escalation)
    assert await db["escalations"].count_documents({"escalation_id": "esc_1"}) == 1


async def test_redis_idempotency_store_lifecycle() -> None:
    store = RedisIdempotencyStore(fakeredis.FakeAsyncRedis())

    assert await store.reserve("k", ttl_seconds=60)
    assert not await store.reserve("k", ttl_seconds=60)
    assert await store.load("k") is None

    await store.save("k", '{"id": 1}', ttl_seconds=60)
    assert await store.load("k") == '{"id": 1}'

    await store.release("k")
    assert await store.reserve("k", ttl_seconds=60)
