from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request

from gateway.container import Container
from gateway.security.auth import Principal


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_principal(
    request: Request,
    container: ContainerDep,
    x_api_key: Annotated[str | None, Header()] = None,
) -> Principal:
    principal = container.authenticator.authenticate(x_api_key)
    request.state.principal = principal
    return principal


PrincipalDep = Annotated[Principal, Depends(get_principal)]
CallerSession = Annotated[str, Header(alias="X-Caller-Session")]
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)]
