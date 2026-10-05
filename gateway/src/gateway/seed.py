from __future__ import annotations

from datetime import date

from gateway.domain.models import ClaimType, Customer, Policy

DEMO_TENANT = "acme-insurance"

DEMO_POLICIES: tuple[Policy, ...] = (
    Policy(
        policy_number="HH-100234",
        tenant_id=DEMO_TENANT,
        customer=Customer(
            customer_id="cus_01",
            full_name="Maria Schneider",
            date_of_birth=date(1987, 4, 12),
            email="maria.schneider@example.com",
            phone="+49 30 1234567",
        ),
        product="Home Contents Plus",
        covered_claim_types=frozenset({ClaimType.WATER_DAMAGE, ClaimType.THEFT, ClaimType.FIRE}),
        valid_from=date(2025, 1, 1),
        valid_until=date(2027, 12, 31),
        deductible_eur=150,
    ),
    Policy(
        policy_number="HH-100877",
        tenant_id=DEMO_TENANT,
        customer=Customer(
            customer_id="cus_02",
            full_name="Jonas Weber",
            date_of_birth=date(1979, 11, 3),
            email="jonas.weber@example.com",
            phone="+49 89 7654321",
        ),
        product="Glass & Liability Basic",
        covered_claim_types=frozenset({ClaimType.GLASS, ClaimType.LIABILITY}),
        valid_from=date(2024, 6, 1),
        valid_until=date(2025, 5, 31),
        deductible_eur=0,
    ),
)
