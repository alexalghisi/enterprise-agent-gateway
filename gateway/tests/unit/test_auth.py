from collections.abc import Callable

import pytest

from gateway.domain.errors import ForbiddenError
from gateway.security.auth import ApiKeyAuthenticator, CallerSessionSigner, Principal

PRINCIPAL = Principal(tenant_id="acme", agent_id="voice")


class TestApiKeyAuthenticator:
    def test_resolves_principal_for_known_key(self) -> None:
        assert ApiKeyAuthenticator({"secret": PRINCIPAL}).authenticate("secret") == PRINCIPAL

    @pytest.mark.parametrize("key", [None, "", "wrong"])
    def test_rejects_unknown_or_missing_key(self, key: str | None) -> None:
        with pytest.raises(ForbiddenError):
            ApiKeyAuthenticator({"secret": PRINCIPAL}).authenticate(key)


class TestCallerSessionSigner:
    signer = CallerSessionSigner("s3cret", ttl_seconds=60)

    def test_accepts_token_for_same_policy_before_expiry(self) -> None:
        token = self.signer.issue("acme", "HH-100234", now=1_000)
        self.signer.verify(token, "acme", "HH-100234", now=1_060)

    def test_rejects_expired_token(self) -> None:
        token = self.signer.issue("acme", "HH-100234", now=1_000)
        with pytest.raises(ForbiddenError, match="expired"):
            self.signer.verify(token, "acme", "HH-100234", now=1_061)

    @pytest.mark.parametrize(("tenant", "policy"), [("acme", "HH-999999"), ("other", "HH-100234")])
    def test_rejects_token_for_another_scope(self, tenant: str, policy: str) -> None:
        token = self.signer.issue("acme", "HH-100234", now=1_000)
        with pytest.raises(ForbiddenError):
            self.signer.verify(token, tenant, policy, now=1_000)

    @pytest.mark.parametrize(
        "mutate",
        [
            lambda token: token.replace("HH-100234", "HH-100877"),
            lambda token: token[:-1] + ("0" if token[-1] != "0" else "1"),
            lambda token: "garbage",
        ],
    )
    def test_rejects_tampered_token(self, mutate: Callable[[str], str]) -> None:
        token = mutate(self.signer.issue("acme", "HH-100234", now=1_000))
        with pytest.raises(ForbiddenError):
            self.signer.verify(token, "acme", "HH-100234", now=1_000)
