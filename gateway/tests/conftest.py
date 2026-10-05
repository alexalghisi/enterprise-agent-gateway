from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from gateway.adapters.memory import (
    InMemoryClaimRepository,
    InMemoryEscalationRepository,
    InMemoryPolicyRepository,
)
from gateway.config import Settings
from gateway.main import create_app
from gateway.security.auth import CallerSessionSigner, Principal
from gateway.seed import DEMO_POLICIES, DEMO_TENANT
from gateway.services.tools import AgentTools
from gateway.wiring import in_memory_container

API_KEY = "test-key"
NOW = datetime(2026, 3, 15, 10, 30, tzinfo=UTC)


class FixedClock:
    def __init__(self, now: datetime = NOW) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current


class SequentialIds:
    def __init__(self) -> None:
        self._counter = 0

    def new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter:04d}"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        api_keys={API_KEY: Principal(tenant_id=DEMO_TENANT, agent_id="test-agent")},
        session_secret="test-secret",
        session_ttl_seconds=600,
    )


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture
def claims() -> InMemoryClaimRepository:
    return InMemoryClaimRepository()


@pytest.fixture
def escalations() -> InMemoryEscalationRepository:
    return InMemoryEscalationRepository()


@pytest.fixture
def sessions() -> CallerSessionSigner:
    return CallerSessionSigner("test-secret", ttl_seconds=600)


@pytest.fixture
def tools(
    claims: InMemoryClaimRepository,
    escalations: InMemoryEscalationRepository,
    sessions: CallerSessionSigner,
    clock: FixedClock,
) -> AgentTools:
    return AgentTools(
        policies=InMemoryPolicyRepository(DEMO_POLICIES),
        claims=claims,
        escalations=escalations,
        sessions=sessions,
        clock=clock,
        ids=SequentialIds(),
    )


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings, in_memory_container(settings))
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=transport, base_url="http://gateway", headers={"X-Api-Key": API_KEY}
        ) as http,
    ):
        yield http
