from __future__ import annotations

from dataclasses import dataclass

from gateway.security.auth import ApiKeyAuthenticator
from gateway.services.idempotency import IdempotentExecutor
from gateway.services.tools import AgentTools


@dataclass(frozen=True)
class Container:
    tools: AgentTools
    authenticator: ApiKeyAuthenticator
    idempotency: IdempotentExecutor
