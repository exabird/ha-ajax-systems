"""AWS SQS Listener for Ajax Systems real-time events."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Event types from Ajax Enterprise API
EVENT_TYPE_ALARM = "ALARM"
EVENT_TYPE_ARM = "ARM"
EVENT_TYPE_DISARM = "DISARM"
EVENT_TYPE_NIGHT_MODE = "NIGHT_MODE"
EVENT_TYPE_DEVICE_STATE = "DEVICE_STATE"
EVENT_TYPE_DEVICE_TRIGGERED = "DEVICE_TRIGGERED"
EVENT_TYPE_MALFUNCTION = "MALFUNCTION"
EVENT_TYPE_TAMPER = "TAMPER"
EVENT_TYPE_BATTERY_LOW = "BATTERY_LOW"
EVENT_TYPE_CONNECTION_LOST = "CONNECTION_LOST"
EVENT_TYPE_CONNECTION_RESTORED = "CONNECTION_RESTORED"


@dataclass
class AjaxSqsEvent:
    """Representation of an Ajax SQS event."""

    event_id: str
    event_type: str
    hub_id: str
    timestamp: datetime
    device_id: str | None = None
    device_type: str | None = None
    room_name: str | None = None
    group_id: str | None = None
    armed_state: str | None = None
    triggered: bool | None = None
    raw_data: dict[str, Any] | None = None

    @classmethod
    def from_sqs_message(cls, message: dict[str, Any]) -> AjaxSqsEvent:
        """Create an AjaxSqsEvent from an SQS message body."""
        body = message.get("body", message)
        if isinstance(body, str):
            body = json.loads(body)

        # Parse timestamp
        timestamp_str = body.get("timestamp", body.get("eventTime"))
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                timestamp = datetime.now()
        else:
            timestamp = datetime.now()

        return cls(
            event_id=body.get("eventId", body.get("id", "")),
            event_type=body.get("eventType", body.get("type", "UNKNOWN")),
            hub_id=body.get("hubId", body.get("objectId", "")),
            timestamp=timestamp,
            device_id=body.get("deviceId", body.get("sourceObjectId")),
            device_type=body.get("deviceType", body.get("sourceObjectType")),
            room_name=body.get("roomName", body.get("room")),
            group_id=body.get("groupId"),
            armed_state=body.get("armState", body.get("state")),
            triggered=body.get("triggered", body.get("alarm")),
            raw_data=body,
        )


class AjaxSqsListener:
    """AWS SQS listener for Ajax Systems events.

    Uses long polling to efficiently receive real-time events from Ajax Cloud.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        queue_url: str,
        aws_access_key: str,
        aws_secret_key: str,
        region: str = "eu-west-1",
        hub_id: str | None = None,
    ) -> None:
        """Initialize the SQS listener."""
        self._hass = hass
        self._queue_url = queue_url
        self._aws_access_key = aws_access_key
        self._aws_secret_key = aws_secret_key
        self._region = region
        self._hub_id = hub_id

        self._running = False
        self._task: asyncio.Task | None = None
        self._callbacks: list[Callable[[AjaxSqsEvent], None]] = []
        self._sqs_client = None

    def register_callback(self, callback: Callable[[AjaxSqsEvent], None]) -> None:
        """Register a callback for received events."""
        self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[AjaxSqsEvent], None]) -> None:
        """Unregister a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def _get_sqs_client(self):
        """Get or create the SQS client."""
        if self._sqs_client is None:
            try:
                # Try to import aiobotocore for async AWS operations
                from aiobotocore.session import get_session

                session = get_session()
                self._sqs_client = await session.create_client(
                    "sqs",
                    region_name=self._region,
                    aws_access_key_id=self._aws_access_key,
                    aws_secret_access_key=self._aws_secret_key,
                ).__aenter__()
            except ImportError:
                _LOGGER.error(
                    "aiobotocore is not installed. "
                    "Please install it with: pip install aiobotocore"
                )
                raise
        return self._sqs_client

    async def start(self) -> None:
        """Start the SQS listener."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        _LOGGER.info("SQS listener started for queue: %s", self._queue_url)

    async def stop(self) -> None:
        """Stop the SQS listener."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        if self._sqs_client:
            await self._sqs_client.__aexit__(None, None, None)
            self._sqs_client = None

        _LOGGER.info("SQS listener stopped")

    async def _poll_loop(self) -> None:
        """Main polling loop using long polling."""
        consecutive_errors = 0
        max_consecutive_errors = 5

        while self._running:
            try:
                client = await self._get_sqs_client()

                # Long polling with 20 second wait (AWS maximum)
                response = await client.receive_message(
                    QueueUrl=self._queue_url,
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=20,  # Long polling
                    AttributeNames=["All"],
                    MessageAttributeNames=["All"],
                )

                messages = response.get("Messages", [])

                for message in messages:
                    await self._process_message(client, message)

                consecutive_errors = 0

            except asyncio.CancelledError:
                raise
            except Exception as err:
                consecutive_errors += 1
                _LOGGER.error("Error polling SQS: %s", err)

                if consecutive_errors >= max_consecutive_errors:
                    _LOGGER.error(
                        "Too many consecutive errors, stopping SQS listener"
                    )
                    self._running = False
                    break

                # Exponential backoff
                await asyncio.sleep(min(2 ** consecutive_errors, 60))

    async def _process_message(self, client, message: dict[str, Any]) -> None:
        """Process a single SQS message."""
        try:
            event = AjaxSqsEvent.from_sqs_message(message)

            # Filter by hub_id if specified
            if self._hub_id and event.hub_id != self._hub_id:
                _LOGGER.debug(
                    "Ignoring event for hub %s (listening for %s)",
                    event.hub_id,
                    self._hub_id,
                )
            else:
                _LOGGER.debug(
                    "Received event: type=%s, hub=%s, device=%s",
                    event.event_type,
                    event.hub_id,
                    event.device_id,
                )

                # Notify callbacks
                for callback in self._callbacks:
                    try:
                        callback(event)
                    except Exception as err:
                        _LOGGER.error("Error in event callback: %s", err)

            # Delete message from queue after processing
            receipt_handle = message.get("ReceiptHandle")
            if receipt_handle:
                await client.delete_message(
                    QueueUrl=self._queue_url,
                    ReceiptHandle=receipt_handle,
                )

        except Exception as err:
            _LOGGER.error("Error processing SQS message: %s", err)

    @property
    def is_running(self) -> bool:
        """Return True if listener is running."""
        return self._running
