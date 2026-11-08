"""AWS Lambda entry point invoked by the one-off EventBridge schedules.

Handler: app.transactions.lambda_handler.handler
Events:  {"booking_id": "<uuid>"}  (set by EventBridgeScheduler.schedule_fee_release)
         {"type": "membership_expiry", "membership_id": "<uuid>"}

Terraform provisions the function (see app/integrations/scheduler.py). Raising lets
EventBridge retry on transient database errors; both handlers are idempotent.
"""

import asyncio
import os
from typing import Any
from uuid import UUID

# Each invocation runs its own event loop, so pooled connections must not be reused.
os.environ.setdefault("PASSIT_DATABASE_NULL_POOL", "true")

from app.memberships.renewal import handle_expiry  # noqa: E402
from app.transactions.release import handle_release  # noqa: E402


def handler(event: dict[str, Any], context: Any = None) -> dict[str, str]:
    if event.get("type") == "membership_expiry":
        return asyncio.run(handle_expiry(UUID(event["membership_id"])))
    return asyncio.run(handle_release(UUID(event["booking_id"])))
