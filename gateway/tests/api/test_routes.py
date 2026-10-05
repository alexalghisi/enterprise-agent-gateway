from httpx import AsyncClient

VERIFY = {"policy_number": "HH-100234", "date_of_birth": "1987-04-12"}
CLAIM = {
    "policy_number": "HH-100234",
    "claim_type": "water_damage",
    "incident_date": "2025-11-02",
    "description": "Washing machine hose burst and flooded the hallway",
}


async def session(client: AsyncClient) -> str:
    response = await client.post("/v1/tools/verify-caller", json=VERIFY)
    assert response.status_code == 200
    token: str = response.json()["session_token"]
    return token


async def test_health(client: AsyncClient) -> None:
    assert (await client.get("/healthz")).json() == {"status": "ok"}


async def test_rejects_missing_api_key(client: AsyncClient) -> None:
    response = await client.post("/v1/tools/verify-caller", json=VERIFY, headers={"X-Api-Key": ""})
    assert response.status_code == 403
    assert response.json() == {
        "error": {"code": "forbidden", "message": "Invalid or missing API key"}
    }


async def test_failed_verification_maps_to_401(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/tools/verify-caller", json={**VERIFY, "date_of_birth": "2000-01-01"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "verification_failed"


async def test_validates_policy_number_format(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/tools/verify-caller", json={**VERIFY, "policy_number": "nope"}
    )
    assert response.status_code == 422


async def test_policy_lookup_requires_caller_session(client: AsyncClient) -> None:
    assert (await client.get("/v1/tools/policies/HH-100234")).status_code == 422
    response = await client.get(
        "/v1/tools/policies/HH-100234", headers={"X-Caller-Session": "forged"}
    )
    assert response.status_code == 403


async def test_file_claim_is_idempotent(client: AsyncClient) -> None:
    headers = {"X-Caller-Session": await session(client), "Idempotency-Key": "call-42-claim"}
    first = await client.post("/v1/tools/claims", json=CLAIM, headers=headers)
    second = await client.post("/v1/tools/claims", json=CLAIM, headers=headers)

    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert first.headers["Idempotent-Replayed"] == "false"
    assert second.headers["Idempotent-Replayed"] == "true"


async def test_file_claim_requires_idempotency_key(client: AsyncClient) -> None:
    headers = {"X-Caller-Session": await session(client)}
    response = await client.post("/v1/tools/claims", json=CLAIM, headers=headers)
    assert response.status_code == 422


async def test_uncovered_claim_returns_422_with_reason(client: AsyncClient) -> None:
    headers = {"X-Caller-Session": await session(client), "Idempotency-Key": "call-43-claim"}
    response = await client.post(
        "/v1/tools/claims", json={**CLAIM, "claim_type": "glass"}, headers=headers
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "not_covered"


async def test_every_response_carries_request_id(client: AsyncClient) -> None:
    response = await client.get("/healthz", headers={"X-Request-Id": "req-123"})
    assert response.headers["X-Request-Id"] == "req-123"
