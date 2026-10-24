"""Release every rental fee whose hold period has ended (idempotent).

    uv run --directory api python -m scripts.release_due_fees

The API already runs this sweep in the background every
PASSIT_LOCAL_RELEASE_SWEEP_SECONDS; use this to force a release during a demo or to
reconcile after an EventBridge outage.
"""

import asyncio

from app.transactions.release import release_due_fees


async def main() -> None:
    results = await release_due_fees()
    for result in results:
        print(f"{result['booking_id']}: {result['status']}")
    print(f"{sum(r['status'] == 'released' for r in results)} fee(s) released.")


if __name__ == "__main__":
    asyncio.run(main())
