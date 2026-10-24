"""Prepare a k6 contention run (B1): one listing plus N borrowers with session tokens.

    uv run --directory api python -m scripts.contention_setup --borrowers 50 > /tmp/k6.env
    set -a; source /tmp/k6.env; set +a
    k6 run -e BASE_URL=http://localhost:8000 scripts/loadtest/contention.js

Run against the same database the target API uses. Afterwards, verify in SQL that only
one confirmed booking exists for the listing (the k6 script also asserts one 201).
"""

import argparse
import asyncio
from datetime import timedelta
from uuid import uuid4

from app.auth.dependencies import issue_access_token
from app.core.db import get_sessionmaker
from app.models import User
from scripts.inprocess import api_client


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--borrowers", type=int, default=50)
    args = parser.parse_args()

    suffix = uuid4().hex[:8]
    async with get_sessionmaker()() as db:
        users = [
            User(
                email=f"contention-{suffix}-{index}@passit.test",
                password_hash="load-test-account-no-password",
                display_name=f"Load test {index}",
            )
            for index in range(args.borrowers + 1)
        ]
        db.add_all(users)
        await db.commit()
    lender, borrowers = users[0], users[1:]
    tokens = [issue_access_token(user.id, timedelta(hours=6)) for user in users]

    async with api_client() as client:
        response = await client.post(
            "/listings",
            json={
                "title": f"Contention target {suffix}",
                "category": "Load test",
                "condition": "Good",
                "price_day": "10.00",
                "price_week": "50.00",
                "deposit": "20.00",
                "mrt_station": "Clementi",
            },
            headers={"authorization": f"Bearer {tokens[0]}"},
        )
        response.raise_for_status()

    print(f"LISTING_ID={response.json()['id']}")
    print(f"TOKENS={','.join(tokens[1:])}")
    print(f"# lender {lender.id}; {len(borrowers)} borrowers")


if __name__ == "__main__":
    asyncio.run(main())
