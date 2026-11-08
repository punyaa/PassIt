"""One-off fee-release and membership-expiry schedules.

At handover the booking gets `fee_release_at`, and the scheduler is asked to call the
release handler at that time. The handler (`app/transactions/release.py`) is idempotent,
so duplicate deliveries and the local sweep can never release a fee twice. Paid Plus
memberships get the same treatment at their period end (`app/memberships/renewal.py`).

Switch with PASSIT_SCHEDULER_BACKEND=local|eventbridge.

  local        No external call. A background sweep in the API process
               (PASSIT_LOCAL_RELEASE_SWEEP_SECONDS) releases due fees and expires due
               memberships; `python -m scripts.release_due_fees` and
               `python -m scripts.expire_memberships` do the same on demand.

  eventbridge  EventBridge Scheduler invokes the Lambda in
               `app/transactions/lambda_handler.py`, which dispatches on the event type.

Platform hand-off for EventBridge (see api/README.md, "AWS hand-off"):
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

    def schedule_membership_expiry(self, membership_id: UUID, at: datetime) -> None: ...


class LocalScheduler:
    def schedule_fee_release(self, booking_id: UUID, at: datetime) -> None:
        logger.info("fee release for %s due at %s (local sweep)", booking_id, at.isoformat())

    def schedule_membership_expiry(self, membership_id: UUID, at: datetime) -> None:
        logger.info(
            "membership expiry for %s due at %s (local sweep)", membership_id, at.isoformat()
        )


class EventBridgeScheduler:
    """AWS implementation, verified against the staging account."""

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
        self._create_one_off(
            f"release-{booking_id}", {"booking_id": str(booking_id)}, at
        )

    def schedule_membership_expiry(self, membership_id: UUID, at: datetime) -> None:
        self._create_one_off(
            f"membership-expiry-{membership_id}",
            {"type": "membership_expiry", "membership_id": str(membership_id)},
            at,
        )

    def _create_one_off(self, name: str, payload: dict, at: datetime) -> None:
        when = at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S")
        self.client.create_schedule(
            Name=name,
            GroupName=self.settings.scheduler_group_name,
            ScheduleExpression=f"at({when})",
            ScheduleExpressionTimezone="UTC",
            FlexibleTimeWindow={"Mode": "OFF"},
            Target={
                "Arn": self.settings.release_lambda_arn,
                "RoleArn": self.settings.scheduler_role_arn,
                "Input": json.dumps(payload),
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
