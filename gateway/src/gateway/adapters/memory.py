from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime

from gateway.domain.models import Claim, Escalation, Policy


class InMemoryPolicyRepository:
    def __init__(self, policies: Iterable[Policy] = ()) -> None:
        self._policies = {(p.tenant_id, p.policy_number): p for p in policies}

    async def get(self, tenant_id: str, policy_number: str) -> Policy | None:
        return self._policies.get((tenant_id, policy_number))


class InMemoryClaimRepository:
    def __init__(self) -> None:
        self._claims: dict[tuple[str, str], Claim] = {}

    async def add(self, claim: Claim) -> None:
        self._claims[(claim.tenant_id, claim.claim_id)] = claim

    async def get(self, tenant_id: str, claim_id: str) -> Claim | None:
        return self._claims.get((tenant_id, claim_id))


class InMemoryEscalationRepository:
    def __init__(self) -> None:
        self.items: list[Escalation] = []

    async def add(self, escalation: Escalation) -> None:
        self.items.append(escalation)


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self._entries: dict[str, tuple[str | None, float]] = {}
        self._lock = asyncio.Lock()

    def _alive(self, key: str) -> bool:
        entry = self._entries.get(key)
        return entry is not None and entry[1] > time.monotonic()

    async def reserve(self, key: str, ttl_seconds: int) -> bool:
        async with self._lock:
            if self._alive(key):
                return False
            self._entries[key] = (None, time.monotonic() + ttl_seconds)
            return True

    async def save(self, key: str, payload: str, ttl_seconds: int) -> None:
        self._entries[key] = (payload, time.monotonic() + ttl_seconds)

    async def load(self, key: str) -> str | None:
        return self._entries[key][0] if self._alive(key) else None

    async def release(self, key: str) -> None:
        self._entries.pop(key, None)


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class UuidGenerator:
    def new_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"
