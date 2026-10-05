import json
import logging

import pytest
from httpx import AsyncClient

PII_FRAGMENTS = ("Maria", "Schneider", "1987-04-12", "4111", "@example.com")


async def test_voice_agent_handles_a_water_damage_call(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="gateway.audit")

    verified = await client.post(
        "/v1/tools/verify-caller",
        json={"policy_number": "HH-100234", "date_of_birth": "1987-04-12"},
    )
    assert verified.json()["display_name"] == "M**** S********"
    caller = {"X-Caller-Session": verified.json()["session_token"]}

    policy = await client.get("/v1/tools/policies/HH-100234", headers=caller)
    assert "water_damage" in policy.json()["covered_claim_types"]

    filed = await client.post(
        "/v1/tools/claims",
        headers={**caller, "Idempotency-Key": "conv-7f3a-claim"},
        json={
            "policy_number": "HH-100234",
            "claim_type": "water_damage",
            "incident_date": "2026-01-20",
            "description": "Ceiling leak from upstairs flat, card 4111 1111 1111 1111 on file",
        },
    )
    assert filed.status_code == 201
    claim_id = filed.json()["claim_id"]

    status = await client.get(f"/v1/tools/claims/{claim_id}", headers=caller)
    assert status.json()["status"] == "received"

    handoff = await client.post(
        "/v1/tools/escalations",
        headers={"Idempotency-Key": "conv-7f3a-handoff"},
        json={
            "policy_number": "HH-100234",
            "reason": "caller asked for an adjuster",
            "summary": f"Water damage claim {claim_id} filed, caller wants a site visit",
        },
    )
    assert handoff.status_code == 201

    audit = [record.__dict__["fields"] for record in caplog.records]
    assert [entry["route"] for entry in audit] == [
        "/v1/tools/verify-caller",
        "/v1/tools/policies/{policy_number}",
        "/v1/tools/claims",
        "/v1/tools/claims/{claim_id}",
        "/v1/tools/escalations",
    ]
    assert {entry["tenant_id"] for entry in audit} == {"acme-insurance"}
    serialized = json.dumps(audit)
    assert not any(fragment in serialized for fragment in PII_FRAGMENTS)
