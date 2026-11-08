"""Shared fixtures. Database tests run against a real PostgreSQL 16 because the booking
guarantee lives in an exclusion constraint that no mock can reproduce.

    PASSIT_TEST_DATABASE_URL   default postgresql+psycopg://passit:passit@localhost:5432/passit_test
    PASSIT_REQUIRE_DB_TESTS=1  fail instead of skip when PostgreSQL is unreachable (CI)
"""

import os
import tempfile
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass
from uuid import UUID

TEST_DATABASE_URL = os.environ.get(
    "PASSIT_TEST_DATABASE_URL", "postgresql+psycopg://passit:passit@localhost:5432/passit_test"
)
# Must be set before the app (and its cached settings) are imported.
os.environ.update(
    PASSIT_DATABASE_URL=TEST_DATABASE_URL,
    PASSIT_DATABASE_NULL_POOL="true",
    PASSIT_LOCAL_RELEASE_SWEEP_SECONDS="0",
    PASSIT_STORAGE_BACKEND="local",
    PASSIT_SCHEDULER_BACKEND="local",
    PASSIT_LOCAL_MEDIA_DIR=tempfile.mkdtemp(prefix="passit-media-"),
    PASSIT_BEDROCK_MODEL_ID="",
    PASSIT_LLM_API_URL="",
    PASSIT_JWT_SECRET="test-secret-test-secret-test-secret",
)

import httpx  # noqa: E402
import psycopg  # noqa: E402
import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402

from alembic import command  # noqa: E402
from app.auth.dependencies import issue_access_token  # noqa: E402
from app.main import app  # noqa: E402

TABLES = (
    "meetup_events, meetups, saved_listings, reviews, checklists, media, ledger_entries, "
    "bookings, availability, listings, users"
)


def _libpq_url(url: str, dbname: str | None = None) -> str:
    plain = url.replace("postgresql+psycopg://", "postgresql://")
    if dbname:
        plain = plain.rsplit("/", 1)[0] + f"/{dbname}"
    return plain


@pytest.fixture(scope="session")
def database() -> Iterator[str]:
    """Create a fresh test database and migrate it to head once per session."""
    dbname = TEST_DATABASE_URL.rsplit("/", 1)[1]
    try:
        with psycopg.connect(
            _libpq_url(TEST_DATABASE_URL, "postgres"), autocommit=True, connect_timeout=3
        ) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{dbname}" WITH (FORCE)')
            admin.execute(f'CREATE DATABASE "{dbname}"')
    except psycopg.OperationalError as error:
        if os.environ.get("PASSIT_REQUIRE_DB_TESTS") == "1":
            raise
        pytest.skip(f"PostgreSQL unavailable at {TEST_DATABASE_URL}: {error}")
    config = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    config.set_main_option(
        "script_location", os.path.join(os.path.dirname(__file__), "..", "alembic")
    )
    command.upgrade(config, "head")
    yield _libpq_url(TEST_DATABASE_URL)


@pytest.fixture
def db_url(database: str) -> str:
    with psycopg.connect(database, autocommit=True) as conn:
        conn.execute(f"TRUNCATE {TABLES} CASCADE")
    return database


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client(db_url: str) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test/v1") as http:
        yield http


@dataclass
class Actor:
    id: UUID
    name: str
    headers: dict[str, str]


@pytest.fixture
def make_user(db_url: str) -> Callable[[str], Actor]:
    def factory(name: str) -> Actor:
        with psycopg.connect(db_url, autocommit=True) as conn:
            user_id = conn.execute(
                "INSERT INTO users (email, password_hash, display_name) "
                "VALUES (%s, 'not-a-real-hash', %s) RETURNING id",
                (f"{name.lower()}-{os.urandom(4).hex()}@example.test", name),
            ).fetchone()[0]
        token = issue_access_token(user_id)
        return Actor(user_id, name, {"authorization": f"Bearer {token}"})

    return factory


@pytest.fixture
def sql(db_url: str) -> Callable[..., list[tuple]]:
    """Run a query against the test database and return all rows."""

    def run(query: str, *params: object) -> list[tuple]:
        with psycopg.connect(db_url, autocommit=True) as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall() if cursor.description else []

    return run
