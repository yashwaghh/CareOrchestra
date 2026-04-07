"""Google Calendar integration for appointment scheduling."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from google.auth import default as google_auth_default

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _build_service(credentials_file: Optional[str] = None,
                   credentials_json: Optional[str] = None):
    """Build an authenticated Google Calendar API service.

    Credential resolution order:
    1. ``credentials_json`` – raw JSON string of a service-account key.
    2. ``credentials_file`` – path to a service-account JSON key file
       (also honoured when the ``GOOGLE_APPLICATION_CREDENTIALS`` env var
       points at the same file).
    3. Application Default Credentials (``gcloud auth application-default``).
    """
    if credentials_json:
        info = json.loads(credentials_json)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=_SCOPES
        )
    elif credentials_file:
        creds = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=_SCOPES
        )
    else:
        creds, _ = google_auth_default(scopes=_SCOPES)

    return build("calendar", "v3", credentials=creds, cache_discovery=False)


class CalendarScheduler:
    """Service for scheduling appointments in Google Calendar."""

    def __init__(
        self,
        calendar_id: str = "primary",
        use_mock: bool = True,
        credentials_file: Optional[str] = None,
        credentials_json: Optional[str] = None,
    ):
        """
        Initialize calendar scheduler.

        Args:
            calendar_id: Calendar ID (default: primary)
            use_mock: Use mock mode for testing without actual Calendar API
            credentials_file: Path to a service-account JSON key file.
            credentials_json: Raw JSON string of a service-account key.
        """
        self.calendar_id = calendar_id
        self.use_mock = use_mock
        self._credentials_file = credentials_file
        self._credentials_json = credentials_json
        self._service = None

        if not use_mock:
            self._service = _build_service(credentials_file, credentials_json)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _format_rfc3339(self, dt: datetime) -> str:
        """Return an RFC-3339 timestamp string (UTC, with Z suffix)."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def schedule_appointment(
        self,
        patient_name: str,
        provider_name: str,
        appointment_time: datetime,
        duration_minutes: int = 30,
        description: str = "",
    ) -> str:
        """
        Schedule an appointment in calendar.

        Args:
            patient_name: Patient name
            provider_name: Provider/doctor name
            appointment_time: Appointment datetime
            duration_minutes: Duration of appointment
            description: Appointment description

        Returns:
            Appointment event ID
        """
        if self.use_mock:
            event_id = f"mock_event_{appointment_time.timestamp()}"
            logger.debug("[MOCK] Scheduling appointment at %s", self._format_rfc3339(appointment_time))
            return event_id

        end_time = appointment_time + timedelta(minutes=duration_minutes)
        event = {
            "summary": f"Appointment: {patient_name} with {provider_name}",
            "description": description,
            "start": {"dateTime": self._format_rfc3339(appointment_time), "timeZone": "UTC"},
            "end": {"dateTime": self._format_rfc3339(end_time), "timeZone": "UTC"},
        }
        try:
            created = (
                self._service.events()
                .insert(calendarId=self.calendar_id, body=event)
                .execute()
            )
            event_id: str = created.get("id", "")
            logger.info("Created calendar event %s", event_id)
            return event_id
        except HttpError as exc:
            logger.error("Failed to create calendar event: %s", exc)
            return ""

    async def schedule_followup(
        self,
        patient_id: str,
        followup_date: datetime,
        followup_type: str,
        notes: str = "",
    ) -> str:
        """
        Schedule a follow-up reminder.

        Args:
            patient_id: Patient identifier
            followup_date: Follow-up datetime
            followup_type: Type of follow-up (medication_review, vitals_check, lab_results)
            notes: Additional notes

        Returns:
            Event ID
        """
        if self.use_mock:
            event_id = f"mock_followup_{followup_date.timestamp()}"
            logger.debug("[MOCK] Scheduling follow-up of type %s", followup_type)
            return event_id

        end_time = followup_date + timedelta(minutes=30)
        event = {
            "summary": f"Follow-up ({followup_type}): Patient {patient_id}",
            "description": notes,
            "start": {"dateTime": self._format_rfc3339(followup_date), "timeZone": "UTC"},
            "end": {"dateTime": self._format_rfc3339(end_time), "timeZone": "UTC"},
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 60},
                    {"method": "popup", "minutes": 15},
                ],
            },
        }
        try:
            created = (
                self._service.events()
                .insert(calendarId=self.calendar_id, body=event)
                .execute()
            )
            event_id: str = created.get("id", "")
            logger.info("Created follow-up event %s", event_id)
            return event_id
        except HttpError as exc:
            logger.error("Failed to create follow-up event: %s", exc)
            return ""

    async def get_available_slots(
        self,
        provider_id: str,
        start_date: datetime,
        end_date: datetime,
        duration_minutes: int = 30,
    ) -> list:
        """
        Get available appointment slots by querying the calendar for busy periods.

        Args:
            provider_id: Provider identifier (used for logging)
            start_date: Start of date range
            end_date: End of date range
            duration_minutes: Required slot duration

        Returns:
            List of available ISO-8601 datetime strings (UTC)
        """
        if self.use_mock:
            return [
                "2025-04-10 10:00",
                "2025-04-10 14:00",
                "2025-04-11 09:00",
            ]

        body = {
            "timeMin": self._format_rfc3339(start_date),
            "timeMax": self._format_rfc3339(end_date),
            "items": [{"id": self.calendar_id}],
        }
        try:
            freebusy = self._service.freebusy().query(body=body).execute()
        except HttpError as exc:
            logger.error("Freebusy query failed: %s", exc)
            return []

        busy_periods = freebusy.get("calendars", {}).get(self.calendar_id, {}).get("busy", [])

        # Pre-parse busy period timestamps once to avoid repeated parsing in the inner loop.
        parsed_busy = [
            (
                datetime.fromisoformat(b["start"].replace("Z", "+00:00")),
                datetime.fromisoformat(b["end"].replace("Z", "+00:00")),
            )
            for b in busy_periods
        ]

        slots = []
        slot_delta = timedelta(minutes=duration_minutes)
        cursor = start_date if start_date.tzinfo else start_date.replace(tzinfo=timezone.utc)
        end_date_tz = end_date if end_date.tzinfo else end_date.replace(tzinfo=timezone.utc)

        while cursor + slot_delta <= end_date_tz:
            slot_end = cursor + slot_delta
            overlap = any(
                cursor < b_end and slot_end > b_start
                for b_start, b_end in parsed_busy
            )
            if not overlap:
                slots.append(cursor.strftime("%Y-%m-%d %H:%M"))
            cursor += slot_delta

        return slots

    async def cancel_appointment(self, event_id: str) -> bool:
        """
        Cancel a scheduled appointment.

        Args:
            event_id: Calendar event ID

        Returns:
            Success status
        """
        if self.use_mock:
            logger.debug("[MOCK] Cancelling appointment: %s", event_id)
            return True

        try:
            self._service.events().delete(
                calendarId=self.calendar_id, eventId=event_id
            ).execute()
            logger.info("Deleted calendar event %s", event_id)
            return True
        except HttpError as exc:
            logger.error("Failed to delete calendar event %s: %s", event_id, exc)
            return False
