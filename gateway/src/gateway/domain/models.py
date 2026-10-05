from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ClaimType(StrEnum):
    WATER_DAMAGE = "water_damage"
    THEFT = "theft"
    FIRE = "fire"
    GLASS = "glass"
    LIABILITY = "liability"


class ClaimStatus(StrEnum):
    RECEIVED = "received"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class Customer(Frozen):
    customer_id: str
    full_name: str
    date_of_birth: date
    email: str
    phone: str


class Policy(Frozen):
    policy_number: str
    tenant_id: str
    customer: Customer
    product: str
    covered_claim_types: frozenset[ClaimType]
    valid_from: date
    valid_until: date
    deductible_eur: int = Field(ge=0)

    def covers(self, claim_type: ClaimType, on: date) -> bool:
        return claim_type in self.covered_claim_types and self.valid_from <= on <= self.valid_until


class Claim(Frozen):
    claim_id: str
    tenant_id: str
    policy_number: str
    claim_type: ClaimType
    incident_date: date
    description: str
    status: ClaimStatus
    created_at: datetime


class Escalation(Frozen):
    escalation_id: str
    tenant_id: str
    policy_number: str | None
    reason: str
    summary: str
    created_at: datetime
