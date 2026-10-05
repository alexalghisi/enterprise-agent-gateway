from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from gateway.security.auth import Principal

DEMO_API_KEYS = "demo-key:acme-insurance:voice-agent"


def _parse_api_keys(raw: str) -> dict[str, Principal]:
    keys: dict[str, Principal] = {}
    for entry in filter(None, (item.strip() for item in raw.split(","))):
        key, tenant_id, agent_id = entry.split(":")
        keys[key] = Principal(tenant_id=tenant_id, agent_id=agent_id)
    return keys


@dataclass(frozen=True)
class Settings:
    api_keys: Mapping[str, Principal]
    session_secret: str
    session_ttl_seconds: int = 900
    idempotency_ttl_seconds: int = 86_400
    mongo_url: str | None = None
    mongo_database: str = "gateway"
    redis_url: str | None = None
    seed_demo_data: bool = True

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> Settings:
        return cls(
            api_keys=_parse_api_keys(env.get("GATEWAY_API_KEYS", DEMO_API_KEYS)),
            session_secret=env.get("GATEWAY_SESSION_SECRET", "change-me"),
            session_ttl_seconds=int(env.get("GATEWAY_SESSION_TTL_SECONDS", "900")),
            idempotency_ttl_seconds=int(env.get("GATEWAY_IDEMPOTENCY_TTL_SECONDS", "86400")),
            mongo_url=env.get("GATEWAY_MONGO_URL") or None,
            mongo_database=env.get("GATEWAY_MONGO_DATABASE", "gateway"),
            redis_url=env.get("GATEWAY_REDIS_URL") or None,
            seed_demo_data=env.get("GATEWAY_SEED_DEMO_DATA", "true").lower() == "true",
        )
