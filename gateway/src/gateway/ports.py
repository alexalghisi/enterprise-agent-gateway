from __future__ import annotations

from datetime import datetime
from typing import Protocol

from gateway.domain.models import Claim, Escalation, Policy


class PolicyRepository(Protocol):
    async def get(self, tenant_id: str, policy_number: str) -> Policy | None: ...


class ClaimRepository(Protocol):
    async def add(self, claim: Claim) -> None: ...

    async def get(self, tenant_id: str, claim_id: str) -> Claim | None: ...


class EscalationRepository(Protocol):
    async def add(self, escalation: Escalation) -> None: ...


class IdempotencyStore(Protocol):
    async def reserve(self, key: str, ttl_seconds: int) -> bool: ...

    async def save(self, key: str, payload: str, ttl_seconds: int) -> None: ...

    async def load(self, key: str) -> str | None: ...

    async def release(self, key: str) -> None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new_id(self, prefix: str) -> str: ...
