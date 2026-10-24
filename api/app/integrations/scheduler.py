"""One-off fee-release schedules.

At handover the booking gets `fee_release_at`, and the scheduler is asked to call the
release handler at that time. The handler (`app/transactions/release.py`) is idempotent,
so duplicate deliveries and the local sweep can never release a fee twice.

Switch with PASSIT_SCHEDULER_BACKEND=local|eventbridge.

  local        No external call. A background sweep in the API process
               (PASSIT_LOCAL_RELEASE_SWEEP_SECONDS) releases due fees, and
               `python -m scripts.release_due_fees` does the same on demand.

  eventbridge  EventBridge Scheduler invokes the Lambda in
               `app/transactions/lambda_handler.py`.

P1 hand-off for EventBridge (see api/README.md, "AWS hand-off"):
  1. Package the API image as a Lambda (or a zip of `app/`) with handler
     `app.transactions.lambda_handler.handler`, with RDS network access and
     PASSIT_DATABASE_URL set.
  2. Create an IAM role EventBridge Scheduler can assume with lambda:InvokeFunction on it.
  3. Grant the ECS task role scheduler:CreateSchedule and iam:PassRole on that role.
  4. `uv add --project api boto3`, set PASSIT_RELEASE_LAMBDA_ARN and
     PASSIT_SCHEDULER_ROLE_ARN, then PASSIT_SCHEDULER_BACKEND=eventbridge.
  5. Keep the local sweep enabled as a safety net; it is idempotent with the Lambda.
"""

import json
import logging
from datetime import UTC, datetime
from functools import lru_cache
from typing import Protocol
from uuid import UUID

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class ReleaseScheduler(Protocol):
    def schedule_fee_release(self, booking_id: UUID, at: datetime) -> None: ...


class LocalScheduler:
    def schedule_fee_release(self, booking_id: UUID, at: datetime) -> None:
        logger.info("fee release for %s due at %s (local sweep)", booking_id, at.isoformat())


class EventBridgeScheduler:
    """AWS implementation. UNVERIFIED until P1 runs it against real resources."""

    def __init__(self, settings: Settings) -> None:
        if not (settings.release_lambda_arn and settings.scheduler_role_arn):
            raise RuntimeError(
                "PASSIT_RELEASE_LAMBDA_ARN and PASSIT_SCHEDULER_ROLE_ARN are required "
                "when PASSIT_SCHEDULER_BACKEND=eventbridge"
            )
        try:
            import boto3  # noqa: PLC0415 - optional dependency until AWS is provisioned
        except ImportError as error:
            raise RuntimeError("Add boto3: `uv add --project api boto3`") from error
        session = boto3.Session(profile_name=settings.aws_profile or None)
        self.client = session.client("scheduler", region_name=settings.aws_region)
        self.settings = settings

    def schedule_fee_release(self, booking_id: UUID, at: datetime) -> None:
        when = at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S")
        self.client.create_schedule(
            Name=f"release-{booking_id}",
            GroupName=self.settings.scheduler_group_name,
            ScheduleExpression=f"at({when})",
            ScheduleExpressionTimezone="UTC",
            FlexibleTimeWindow={"Mode": "OFF"},
            Target={
                "Arn": self.settings.release_lambda_arn,
                "RoleArn": self.settings.scheduler_role_arn,
                "Input": json.dumps({"booking_id": str(booking_id)}),
                "RetryPolicy": {"MaximumRetryAttempts": 10},
            },
            ActionAfterCompletion="DELETE",
        )


@lru_cache
def get_scheduler() -> ReleaseScheduler:
    settings = get_settings()
    if settings.scheduler_backend == "eventbridge":
        return EventBridgeScheduler(settings)
    return LocalScheduler()
