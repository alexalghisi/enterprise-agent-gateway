from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from gateway.domain.models import ClaimStatus, ClaimType

PolicyNumber = Field(pattern=r"^[A-Z]{2}-\d{6}$", examples=["HH-100234"])


class VerifyCallerRequest(BaseModel):
    policy_number: str = PolicyNumber
    date_of_birth: date


class VerifyCallerResponse(BaseModel):
    session_token: str
    display_name: str


class PolicyResponse(BaseModel):
    policy_number: str
    product: str
    holder: str
    covered_claim_types: list[ClaimType]
    valid_from: date
    valid_until: date
    deductible_eur: int


class FileClaimRequest(BaseModel):
    policy_number: str = PolicyNumber
    claim_type: ClaimType
    incident_date: date
    description: str = Field(min_length=10, max_length=2000)


class ClaimResponse(BaseModel):
    claim_id: str
    policy_number: str
    claim_type: ClaimType
    incident_date: date
    status: ClaimStatus


class EscalationRequest(BaseModel):
    policy_number: str | None = Field(default=None, pattern=r"^[A-Z]{2}-\d{6}$")
    reason: str = Field(min_length=3, max_length=200)
    summary: str = Field(min_length=10, max_length=4000)


class EscalationResponse(BaseModel):
    escalation_id: str


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
