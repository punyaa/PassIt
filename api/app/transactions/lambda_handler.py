"""AWS Lambda entry point invoked by the one-off EventBridge schedule.

Handler: app.transactions.lambda_handler.handler
Event:   {"booking_id": "<uuid>"}  (set by EventBridgeScheduler.schedule_fee_release)

Terraform provisions the function (see app/integrations/scheduler.py). Raising lets
EventBridge retry on transient database errors; the release itself is idempotent.

The function sits in the VPC with no route to SNS or SES, so it cannot send the
`fee.released` event itself. It returns the event in its result, and a Lambda destination
(on success) delivers the whole result to the events topic, where the mailer Lambda picks
the event out of it. A call that releases nothing returns no event, so nothing is sent.
"""

import asyncio
import os
from typing import Any
from uuid import UUID

# Each invocation runs its own event loop, so pooled connections must not be reused.
os.environ.setdefault("PASSIT_DATABASE_NULL_POOL", "true")

from app.transactions.release import handle_release  # noqa: E402


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    return asyncio.run(handle_release(UUID(event["booking_id"])))
