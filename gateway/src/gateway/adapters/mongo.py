from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from gateway.domain.models import Claim, Escalation, Policy


class MongoPolicyRepository:
    def __init__(self, db: AsyncIOMotorDatabase[dict[str, Any]]) -> None:
        self._collection = db["policies"]

    async def get(self, tenant_id: str, policy_number: str) -> Policy | None:
        document = await self._collection.find_one(
            {"tenant_id": tenant_id, "policy_number": policy_number}, {"_id": 0}
        )
        return Policy.model_validate(document) if document else None


class MongoClaimRepository:
    def __init__(self, db: AsyncIOMotorDatabase[dict[str, Any]]) -> None:
        self._collection = db["claims"]

    async def add(self, claim: Claim) -> None:
        await self._collection.insert_one(claim.model_dump(mode="json"))

    async def get(self, tenant_id: str, claim_id: str) -> Claim | None:
        document = await self._collection.find_one(
            {"tenant_id": tenant_id, "claim_id": claim_id}, {"_id": 0}
        )
        return Claim.model_validate(document) if document else None


class MongoEscalationRepository:
    def __init__(self, db: AsyncIOMotorDatabase[dict[str, Any]]) -> None:
        self._collection = db["escalations"]

    async def add(self, escalation: Escalation) -> None:
        await self._collection.insert_one(escalation.model_dump(mode="json"))


async def ensure_indexes(db: AsyncIOMotorDatabase[dict[str, Any]]) -> None:
    await db["policies"].create_index([("tenant_id", 1), ("policy_number", 1)], unique=True)
    await db["claims"].create_index([("tenant_id", 1), ("claim_id", 1)], unique=True)
