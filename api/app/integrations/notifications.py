"""Publishing booking and release events.

Switch with PASSIT_NOTIFICATIONS_BACKEND=log|sns.

  log  Writes one log line per event (type and booking id only, never an email address).
       The default, and what runs locally and in tests.

  sns  Publishes the event as JSON to the SNS topic in PASSIT_EVENTS_TOPIC_ARN. The mailer
       Lambda (infra/lambdas/mailer) is subscribed to it and sends the emails through SES.
       The ECS task role needs sns:Publish on the topic.

Publishing is best effort. A booking change has already committed when its event is
published, so a failure here is logged and never surfaces to the person using the site.
The fee-release Lambda cannot reach SNS (it sits in the VPC without a NAT Gateway); its
result is delivered to the same topic by a Lambda destination instead, see
app/transactions/lambda_handler.py.
"""

import json
import logging
from functools import lru_cache
from typing import Any, Protocol

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class EventPublisher(Protocol):
    def publish(self, event: dict[str, Any]) -> None: ...


class LogPublisher:
    def publish(self, event: dict[str, Any]) -> None:
        logger.info("event %s for booking %s", event["type"], event["booking"]["id"])


class SnsPublisher:
    def __init__(self, settings: Settings) -> None:
        if not settings.events_topic_arn:
            raise RuntimeError(
                "PASSIT_EVENTS_TOPIC_ARN is required when PASSIT_NOTIFICATIONS_BACKEND=sns"
            )
        import boto3  # noqa: PLC0415 - only needed when the sns backend is selected

        session = boto3.Session(profile_name=settings.aws_profile or None)
        self.client = session.client("sns", region_name=settings.aws_region)
        self.topic_arn = settings.events_topic_arn

    def publish(self, event: dict[str, Any]) -> None:
        self.client.publish(
            TopicArn=self.topic_arn,
            Message=json.dumps(event),
            # Lets a subscriber filter by event type without parsing the message.
            MessageAttributes={"eventType": {"DataType": "String", "StringValue": event["type"]}},
        )


@lru_cache
def get_publisher() -> EventPublisher:
    settings = get_settings()
    if settings.notifications_backend == "sns":
        return SnsPublisher(settings)
    return LogPublisher()


def publish_event(event: dict[str, Any]) -> None:
    try:
        get_publisher().publish(event)
    except Exception:  # best effort, see the module docstring
        logger.exception("could not publish %s", event.get("type"))
