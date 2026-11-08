"""Expire every Plus membership whose period has ended (idempotent).

    uv run --directory api python -m scripts.expire_memberships

The API already runs this sweep in the background every
PASSIT_LOCAL_RELEASE_SWEEP_SECONDS; use this to force expiry during a demo or to
reconcile after an EventBridge outage.
"""

import asyncio

from app.memberships.renewal import expire_due_memberships


async def main() -> None:
    results = await expire_due_memberships()
    for result in results:
        print(f"{result['membership_id']}: {result['status']}")
    print(f"{sum(r['status'] == 'expired' for r in results)} membership(s) expired.")


if __name__ == "__main__":
    asyncio.run(main())
