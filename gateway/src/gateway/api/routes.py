from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Response, status

from gateway.api.dependencies import CallerSession, ContainerDep, IdempotencyKey, PrincipalDep
from gateway.api.schemas import (
    ClaimResponse,
    EscalationRequest,
    EscalationResponse,
    FileClaimRequest,
    PolicyResponse,
    VerifyCallerRequest,
    VerifyCallerResponse,
)
from gateway.container import Container
from gateway.domain.models import Claim

router = APIRouter(prefix="/v1/tools", tags=["agent tools"])

REPLAYED_HEADER = "Idempotent-Replayed"


def _claim_response(claim: Claim) -> ClaimResponse:
    return ClaimResponse.model_validate(claim, from_attributes=True)


async def _run_idempotent(
    container: Container,
    response: Response,
    key: str,
    operation: Callable[[], Awaitable[str]],
) -> str:
    payload, replayed = await container.idempotency.run(key, operation)
    response.headers[REPLAYED_HEADER] = str(replayed).lower()
    return payload


@router.post("/verify-caller", response_model=VerifyCallerResponse)
async def verify_caller(
    body: VerifyCallerRequest, principal: PrincipalDep, container: ContainerDep
) -> VerifyCallerResponse:
    caller = await container.tools.verify_caller(
        principal.tenant_id, body.policy_number, body.date_of_birth
    )
    return VerifyCallerResponse(
        session_token=caller.session_token, display_name=caller.display_name
    )


@router.get("/policies/{policy_number}", response_model=PolicyResponse)
async def get_policy(
    policy_number: str, session: CallerSession, principal: PrincipalDep, container: ContainerDep
) -> PolicyResponse:
    summary = await container.tools.get_policy(principal.tenant_id, policy_number, session)
    return PolicyResponse.model_validate(summary, from_attributes=True)


@router.post("/claims", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
async def file_claim(
    body: FileClaimRequest,
    response: Response,
    session: CallerSession,
    idempotency_key: IdempotencyKey,
    principal: PrincipalDep,
    container: ContainerDep,
) -> ClaimResponse:
    async def operation() -> str:
        claim = await container.tools.file_claim(
            principal.tenant_id,
            body.policy_number,
            session,
            body.claim_type,
            body.incident_date,
            body.description,
        )
        return _claim_response(claim).model_dump_json()

    payload = await _run_idempotent(
        container, response, f"{principal.tenant_id}:claims:{idempotency_key}", operation
    )
    return ClaimResponse.model_validate_json(payload)


@router.get("/claims/{claim_id}", response_model=ClaimResponse)
async def claim_status(
    claim_id: str, session: CallerSession, principal: PrincipalDep, container: ContainerDep
) -> ClaimResponse:
    claim = await container.tools.claim_status(principal.tenant_id, claim_id, session)
    return _claim_response(claim)


@router.post("/escalations", response_model=EscalationResponse, status_code=status.HTTP_201_CREATED)
async def escalate(
    body: EscalationRequest,
    response: Response,
    idempotency_key: IdempotencyKey,
    principal: PrincipalDep,
    container: ContainerDep,
) -> EscalationResponse:
    async def operation() -> str:
        escalation = await container.tools.escalate(
            principal.tenant_id, body.policy_number, body.reason, body.summary
        )
        return EscalationResponse(escalation_id=escalation.escalation_id).model_dump_json()

    payload = await _run_idempotent(
        container, response, f"{principal.tenant_id}:escalations:{idempotency_key}", operation
    )
    return EscalationResponse.model_validate_json(payload)
