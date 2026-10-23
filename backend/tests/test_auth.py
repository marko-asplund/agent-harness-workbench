"""Token verification tests; no Supabase project or external network required."""

import asyncio
import importlib

import httpx
import pytest

auth_module = importlib.import_module("app.auth")


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://auth.example.test/")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "public-test-key")
    original_client = httpx.AsyncClient

    def install(handler):
        transport = httpx.MockTransport(handler)
        monkeypatch.setattr(
            auth_module.httpx,
            "AsyncClient",
            lambda **kwargs: original_client(transport=transport, **kwargs),
        )

    return install


def authenticate(headers):
    return asyncio.run(auth_module.authenticate(headers))


def test_valid_token_uses_verified_identity(provider):
    def verify(request):
        assert str(request.url) == "https://auth.example.test/auth/v1/user"
        assert request.headers["authorization"] == "Bearer valid-token"
        assert request.headers["apikey"] == "public-test-key"
        return httpx.Response(
            200, json={"id": "verified-user", "email": "a@example.test"}
        )

    provider(verify)
    user = authenticate({b"authorization": b"Bearer valid-token"})
    assert user == {"identity": "verified-user", "display_name": "a@example.test"}


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {b"authorization": b"Basic abc"},
        {b"authorization": b"Bearer "},
        {b"x-api-key": b"alice-local-token"},
    ],
)
def test_missing_credentials_never_contact_provider(provider, headers):
    def unexpected(request):
        pytest.fail("Invalid credentials must not trigger provider calls")

    provider(unexpected)
    with pytest.raises(auth_module.Auth.exceptions.HTTPException) as error:
        authenticate(headers)
    assert error.value.status_code == 401


@pytest.mark.parametrize(
    "status, expected", [(401, 401), (403, 401), (429, 503), (500, 503)]
)
def test_provider_rejections(provider, status, expected):
    provider(lambda request: httpx.Response(status))
    with pytest.raises(auth_module.Auth.exceptions.HTTPException) as error:
        authenticate({b"authorization": b"Bearer rejected"})
    assert error.value.status_code == expected


def test_network_failure_fails_closed(provider):
    def unavailable(request):
        raise httpx.ConnectError("offline", request=request)

    provider(unavailable)
    with pytest.raises(auth_module.Auth.exceptions.HTTPException) as error:
        authenticate({b"authorization": b"Bearer valid"})
    assert error.value.status_code == 503


@pytest.mark.parametrize("body", [{}, {"id": None}, {"id": ""}, [], {"id": 123}])
def test_missing_identity_is_rejected(provider, body):
    provider(lambda request: httpx.Response(200, json=body))
    with pytest.raises(auth_module.Auth.exceptions.HTTPException) as error:
        authenticate({b"authorization": b"Bearer valid"})
    assert error.value.status_code == 401


def test_missing_configuration_fails_closed(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    with pytest.raises(auth_module.Auth.exceptions.HTTPException) as error:
        authenticate({b"authorization": b"Bearer valid"})
    assert error.value.status_code == 503
