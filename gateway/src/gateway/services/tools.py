from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import date

from gateway.domain.errors import CoverageError, NotFoundError, VerificationFailedError
from gateway.domain.models import Claim, ClaimStatus, ClaimType, Escalation, Policy
from gateway.ports import (
    ClaimRepository,
    Clock,
    EscalationRepository,
    IdGenerator,
    PolicyRepository,
)
from gateway.security.auth import CallerSessionSigner
from gateway.security.pii import mask_name, redact


@dataclass(frozen=True)
class VerifiedCaller:
    session_token: str
    display_name: str


@dataclass(frozen=True)
class PolicySummary:
    policy_number: str
    product: str
    holder: str
    covered_claim_types: list[ClaimType]
    valid_from: date
    valid_until: date
    deductible_eur: int


class AgentTools:
    def __init__(
        self,
        policies: PolicyRepository,
        claims: ClaimRepository,
        escalations: EscalationRepository,
        sessions: CallerSessionSigner,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._policies = policies
        self._claims = claims
        self._escalations = escalations
        self._sessions = sessions
        self._clock = clock
        self._ids = ids

    def _timestamp(self) -> int:
        return int(self._clock.now().timestamp())

    async def _policy(self, tenant_id: str, policy_number: str) -> Policy:
        policy = await self._policies.get(tenant_id, policy_number)
        if policy is None:
            raise NotFoundError(f"Policy {policy_number} not found")
        return policy

    async def _verified_policy(self, tenant_id: str, policy_number: str, token: str) -> Policy:
        self._sessions.verify(token, tenant_id, policy_number, self._timestamp())
        return await self._policy(tenant_id, policy_number)

    async def verify_caller(
        self, tenant_id: str, policy_number: str, date_of_birth: date
    ) -> VerifiedCaller:
        policy = await self._policies.get(tenant_id, policy_number)
        expected = policy.customer.date_of_birth.isoformat() if policy else ""
        if policy is None or not hmac.compare_digest(expected, date_of_birth.isoformat()):
            raise VerificationFailedError("Policy number and date of birth do not match")
        return VerifiedCaller(
            session_token=self._sessions.issue(tenant_id, policy_number, self._timestamp()),
            display_name=mask_name(policy.customer.full_name),
        )

    async def get_policy(self, tenant_id: str, policy_number: str, token: str) -> PolicySummary:
        policy = await self._verified_policy(tenant_id, policy_number, token)
        return PolicySummary(
            policy_number=policy.policy_number,
            product=policy.product,
            holder=mask_name(policy.customer.full_name),
            covered_claim_types=sorted(policy.covered_claim_types),
            valid_from=policy.valid_from,
            valid_until=policy.valid_until,
            deductible_eur=policy.deductible_eur,
        )

    async def file_claim(
        self,
        tenant_id: str,
        policy_number: str,
        token: str,
        claim_type: ClaimType,
        incident_date: date,
        description: str,
    ) -> Claim:
        policy = await self._verified_policy(tenant_id, policy_number, token)
        now = self._clock.now()
        if incident_date > now.date():
            raise CoverageError("Incident date cannot be in the future")
        if not policy.covers(claim_type, incident_date):
            raise CoverageError(
                f"{claim_type.value} on {incident_date.isoformat()} is not covered by this policy"
            )
        claim = Claim(
            claim_id=self._ids.new_id("clm"),
            tenant_id=tenant_id,
            policy_number=policy_number,
            claim_type=claim_type,
            incident_date=incident_date,
            description=redact(description),
            status=ClaimStatus.RECEIVED,
            created_at=now,
        )
        await self._claims.add(claim)
        return claim

    async def claim_status(self, tenant_id: str, claim_id: str, token: str) -> Claim:
        claim = await self._claims.get(tenant_id, claim_id)
        if claim is None:
            raise NotFoundError(f"Claim {claim_id} not found")
        self._sessions.verify(token, tenant_id, claim.policy_number, self._timestamp())
        return claim

    async def escalate(
        self, tenant_id: str, policy_number: str | None, reason: str, summary: str
    ) -> Escalation:
        escalation = Escalation(
            escalation_id=self._ids.new_id("esc"),
            tenant_id=tenant_id,
            policy_number=policy_number,
            reason=redact(reason),
            summary=redact(summary),
            created_at=self._clock.now(),
        )
        await self._escalations.add(escalation)
        return escalation
