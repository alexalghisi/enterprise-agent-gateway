from datetime import date

import pytest

from gateway.adapters.memory import InMemoryClaimRepository, InMemoryEscalationRepository
from gateway.domain.errors import (
    CoverageError,
    ForbiddenError,
    NotFoundError,
    VerificationFailedError,
)
from gateway.domain.models import ClaimStatus, ClaimType
from gateway.seed import DEMO_TENANT
from gateway.services.tools import AgentTools

ACTIVE = "HH-100234"
EXPIRED = "HH-100877"


async def verified(tools: AgentTools, policy: str = ACTIVE) -> str:
    dob = date(1987, 4, 12) if policy == ACTIVE else date(1979, 11, 3)
    return (await tools.verify_caller(DEMO_TENANT, policy, dob)).session_token


class TestVerifyCaller:
    async def test_returns_session_and_masked_name(self, tools: AgentTools) -> None:
        caller = await tools.verify_caller(DEMO_TENANT, ACTIVE, date(1987, 4, 12))
        assert caller.display_name == "M**** S********"
        assert caller.session_token

    @pytest.mark.parametrize(
        ("tenant", "policy", "dob"),
        [
            (DEMO_TENANT, ACTIVE, date(1990, 1, 1)),
            (DEMO_TENANT, "HH-000000", date(1987, 4, 12)),
            ("other-tenant", ACTIVE, date(1987, 4, 12)),
        ],
    )
    async def test_rejects_mismatch_without_revealing_which_field(
        self, tools: AgentTools, tenant: str, policy: str, dob: date
    ) -> None:
        with pytest.raises(VerificationFailedError, match="do not match"):
            await tools.verify_caller(tenant, policy, dob)


class TestGetPolicy:
    async def test_returns_summary_for_verified_caller(self, tools: AgentTools) -> None:
        summary = await tools.get_policy(DEMO_TENANT, ACTIVE, await verified(tools))
        assert summary.product == "Home Contents Plus"
        assert summary.covered_claim_types == [
            ClaimType.FIRE,
            ClaimType.THEFT,
            ClaimType.WATER_DAMAGE,
        ]

    async def test_requires_session_for_that_policy(self, tools: AgentTools) -> None:
        other_session = await verified(tools, EXPIRED)
        with pytest.raises(ForbiddenError):
            await tools.get_policy(DEMO_TENANT, ACTIVE, other_session)


class TestFileClaim:
    async def test_stores_claim_with_redacted_description(
        self, tools: AgentTools, claims: InMemoryClaimRepository
    ) -> None:
        claim = await tools.file_claim(
            DEMO_TENANT,
            ACTIVE,
            await verified(tools),
            ClaimType.WATER_DAMAGE,
            date(2026, 3, 10),
            "Pipe burst, reach me at maria.schneider@example.com",
        )
        assert claim.claim_id == "clm_0001"
        assert claim.status is ClaimStatus.RECEIVED
        stored = await claims.get(DEMO_TENANT, claim.claim_id)
        assert stored is not None
        assert stored.description == "Pipe burst, reach me at [EMAIL]"

    @pytest.mark.parametrize(
        ("claim_type", "incident", "reason"),
        [
            (ClaimType.GLASS, date(2026, 3, 10), "not covered"),
            (ClaimType.THEFT, date(2024, 12, 31), "not covered"),
            (ClaimType.THEFT, date(2026, 3, 16), "future"),
        ],
    )
    async def test_rejects_claims_outside_coverage(
        self, tools: AgentTools, claim_type: ClaimType, incident: date, reason: str
    ) -> None:
        with pytest.raises(CoverageError, match=reason):
            await tools.file_claim(
                DEMO_TENANT, ACTIVE, await verified(tools), claim_type, incident, "x" * 20
            )

    async def test_rejects_claim_on_expired_policy(self, tools: AgentTools) -> None:
        with pytest.raises(CoverageError):
            await tools.file_claim(
                DEMO_TENANT,
                EXPIRED,
                await verified(tools, EXPIRED),
                ClaimType.GLASS,
                date(2026, 1, 5),
                "Windscreen cracked on the highway",
            )


class TestClaimStatus:
    async def test_returns_claim_for_policy_holder(self, tools: AgentTools) -> None:
        session = await verified(tools)
        claim = await tools.file_claim(
            DEMO_TENANT, ACTIVE, session, ClaimType.FIRE, date(2026, 3, 1), "Kitchen fire damage"
        )
        assert await tools.claim_status(DEMO_TENANT, claim.claim_id, session) == claim

    async def test_hides_claim_from_other_callers(self, tools: AgentTools) -> None:
        claim = await tools.file_claim(
            DEMO_TENANT,
            ACTIVE,
            await verified(tools),
            ClaimType.FIRE,
            date(2026, 3, 1),
            "Kitchen fire damage",
        )
        with pytest.raises(ForbiddenError):
            await tools.claim_status(DEMO_TENANT, claim.claim_id, await verified(tools, EXPIRED))

    async def test_unknown_claim(self, tools: AgentTools) -> None:
        with pytest.raises(NotFoundError):
            await tools.claim_status(DEMO_TENANT, "clm_missing", await verified(tools))


async def test_escalation_redacts_free_text(
    tools: AgentTools, escalations: InMemoryEscalationRepository
) -> None:
    await tools.escalate(DEMO_TENANT, ACTIVE, "angry caller", "Caller gave card 4111111111111111")
    assert escalations.items[0].summary == "Caller gave card [CARD]"
