from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping
from dataclasses import dataclass

from gateway.domain.errors import ForbiddenError


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    agent_id: str


class ApiKeyAuthenticator:
    def __init__(self, keys: Mapping[str, Principal]) -> None:
        self._keys = {self._digest(key): principal for key, principal in keys.items()}

    @staticmethod
    def _digest(key: str) -> bytes:
        return hashlib.sha256(key.encode()).digest()

    def authenticate(self, api_key: str | None) -> Principal:
        if api_key:
            candidate = self._digest(api_key)
            for digest, principal in self._keys.items():
                if hmac.compare_digest(candidate, digest):
                    return principal
        raise ForbiddenError("Invalid or missing API key")


class CallerSessionSigner:
    def __init__(self, secret: str, ttl_seconds: int) -> None:
        self._secret = secret.encode()
        self._ttl_seconds = ttl_seconds

    def _signature(self, payload: str) -> str:
        return hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()

    def issue(self, tenant_id: str, policy_number: str, now: int) -> str:
        payload = f"{tenant_id}|{policy_number}|{now + self._ttl_seconds}"
        return f"{payload}|{self._signature(payload)}"

    def verify(self, token: str, tenant_id: str, policy_number: str, now: int) -> None:
        payload, _, signature = token.rpartition("|")
        if not payload or not hmac.compare_digest(signature, self._signature(payload)):
            raise ForbiddenError("Caller session is invalid")
        token_tenant, token_policy, expires_at = payload.split("|")
        if (token_tenant, token_policy) != (tenant_id, policy_number):
            raise ForbiddenError("Caller is not verified for this policy")
        if int(expires_at) < now:
            raise ForbiddenError("Caller session has expired")
