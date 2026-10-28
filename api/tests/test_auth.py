import httpx
import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_JWT_SECRET, Settings
from tests.conftest import Actor

pytestmark = pytest.mark.anyio

CREDENTIALS = {"email": "Ada@Example.com", "password": "correct horse battery"}


async def signup(client: httpx.AsyncClient, **overrides: str) -> httpx.Response:
    return await client.post(
        "/auth/signup", json={**CREDENTIALS, "display_name": "Ada", **overrides}
    )


async def test_signup_starts_a_cookie_session(client: httpx.AsyncClient) -> None:
    response = await signup(client)
    assert response.status_code == 201
    assert response.json()["display_name"] == "Ada"
    set_cookie = response.headers["set-cookie"].lower()
    assert "passit_session=" in set_cookie and "httponly" in set_cookie

    me = await client.get("/auth/me")
    assert me.status_code == 200
    assert me.json() == {
        **response.json(),
        "email": "ada@example.com",
        "bio": None,
        "avatar_url": None,
    }  # stored lower-cased


async def test_password_is_hashed_never_stored(client: httpx.AsyncClient, sql) -> None:
    await signup(client)
    (stored,) = sql("SELECT password_hash FROM users")[0]
    assert stored.startswith("$argon2id$") and CREDENTIALS["password"] not in stored


async def test_duplicate_email_is_rejected_case_insensitively(client: httpx.AsyncClient) -> None:
    assert (await signup(client)).status_code == 201
    again = await signup(client, email="ADA@example.com")
    assert again.status_code == 409


async def test_short_password_is_rejected(client: httpx.AsyncClient) -> None:
    assert (await signup(client, password="short")).status_code == 422


async def test_login_with_correct_password(client: httpx.AsyncClient) -> None:
    await signup(client)
    client.cookies.clear()
    response = await client.post("/auth/session", json=CREDENTIALS)
    assert response.status_code == 200
    assert (await client.get("/auth/me")).status_code == 200


async def test_wrong_password_and_unknown_email_look_identical(client: httpx.AsyncClient) -> None:
    await signup(client)
    client.cookies.clear()
    wrong = await client.post("/auth/session", json={**CREDENTIALS, "password": "not the one"})
    unknown = await client.post("/auth/session", json={**CREDENTIALS, "email": "no@example.com"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


async def test_accounts_without_a_real_hash_cannot_log_in(client: httpx.AsyncClient, sql) -> None:
    # A placeholder hash, like the seed accounts.
    sql(
        "INSERT INTO users (email, password_hash, display_name) "
        "VALUES ('seeded@example.com', 'seed-account-no-password', 'Seeded')"
    )
    response = await client.post(
        "/auth/session", json={"email": "seeded@example.com", "password": "anything at all"}
    )
    assert response.status_code == 401


async def test_logout_clears_the_cookie(client: httpx.AsyncClient) -> None:
    await signup(client)
    assert (await client.delete("/auth/session")).status_code == 204
    assert (await client.get("/auth/me")).status_code == 401


async def test_me_requires_a_session(client: httpx.AsyncClient) -> None:
    assert (await client.get("/auth/me")).status_code == 401


async def test_bearer_token_still_works(client: httpx.AsyncClient, make_user) -> None:
    actor: Actor = make_user("Grace")
    me = await client.get("/auth/me", headers=actor.headers)
    assert me.status_code == 200 and me.json()["display_name"] == "Grace"


def test_default_jwt_secret_is_refused_outside_development() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="staging", jwt_secret=DEFAULT_JWT_SECRET)
    Settings(environment="staging", jwt_secret="x" * 64)
    Settings(environment="development", jwt_secret=DEFAULT_JWT_SECRET)
