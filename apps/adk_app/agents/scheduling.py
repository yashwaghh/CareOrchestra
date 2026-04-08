import asyncio
import datetime
import logging
import os
import uuid
from typing import List, TypedDict, Dict, Any

from ..tools.bigquery_tools.client import BigQueryClient
from ..tools.calendar_tools.scheduler import CalendarScheduler

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Typed Schemas (CRITICAL for Gemini)
# ─────────────────────────────────────────────

class Slot(TypedDict):
    id: str
    doctor: str
    time: str
    duration: int
    location: str

# UPDATED: This must exactly match the BigQuery table columns in setup.ps1
class Appointment(TypedDict):
    appointment_id: str
    patient_id: str
    provider_id: str        # Added
    provider_name: str
    appointment_type: str   # Added
    scheduled_at: str
    location: str
    notes: str              # Added
    created_at: str
    cancelled: bool         # Added
    completed: bool


# ─────────────────────────────────────────────
# Global clients
# ─────────────────────────────────────────────

_bq_client = BigQueryClient(
    project_id=os.getenv("GCP_PROJECT_ID"),
    dataset_id="careorchestra"
)

_calendar_scheduler = CalendarScheduler(use_mock=True)


# ─────────────────────────────────────────────
# Scheduling Agent
# ─────────────────────────────────────────────

class SchedulingAgent:
    """
    Hospital API integration for critical patient scheduling.
    Mock now → Replace with real hospital API later.
    """

    async def get_available_slots(self, urgent: bool = False) -> List[Slot]:
        """
        Returns available appointment slots.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        today = now.date()
        tomorrow = today + datetime.timedelta(days=1)

        slots: List[Slot] = [
            {
                "id": "slot_1",
                "doctor": "Dr. Sarah Johnson (Cardiologist)",
                "time": now.replace(hour=9, minute=0, second=0, microsecond=0).isoformat(),
                "duration": 30,
                "location": "Emergency Clinic A"
            },
            {
                "id": "slot_2",
                "doctor": "Dr. Michael Chen (Internal Medicine)",
                "time": now.replace(hour=10, minute=30, second=0, microsecond=0).isoformat(),
                "duration": 45,
                "location": "Urgent Care B"
            },
            {
                "id": "slot_3",
                "doctor": "Dr. Emily Rodriguez (ER Physician)",
                "time": datetime.datetime.combine(
                    tomorrow,
                    datetime.time(hour=8, minute=0),
                    tzinfo=datetime.timezone.utc
                ).isoformat(),
                "duration": 30,
                "location": "Main ER"
            }
        ]

        logger.info(f"[Hospital API Mock] Returning {len(slots)} slots")
        return slots

    async def book_slot(
        self,
        patient_id: str,
        slot_id: str,
        doctor_note: str = ""
    ) -> Dict[str, Any]:
        """
        Books a slot → writes to BigQuery + blocks calendar.
        """

        # Fetch slots
        slots = await self.get_available_slots()
        slot = next((s for s in slots if s["id"] == slot_id), None)

        if not slot:
            return {"status": "error", "error": "Invalid slot ID"}

        # ─────────────────────────────────────────
        # Create appointment record (UPDATED TO MATCH SCHEMA)
        # ─────────────────────────────────────────

        appointment: Appointment = {
            "appointment_id": f"apt_{uuid.uuid4()}",
            "patient_id": patient_id,
            "provider_id": slot_id,  
            "provider_name": slot["doctor"],
            "appointment_type": "Urgent Care",
            "scheduled_at": slot["time"],
            "location": slot["location"],
            "notes": doctor_note,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "cancelled": False,
            "completed": False
        }

        # ─────────────────────────────────────────
        # Insert into BigQuery
        # ─────────────────────────────────────────

        success = await _bq_client.insert("appointments", [appointment])

        if not success:
            logger.error("[Scheduling] Failed to insert appointment")
            return {"status": "error", "error": "Failed to log appointment"}

        # ─────────────────────────────────────────
        # Safe datetime parsing
        # ─────────────────────────────────────────

        try:
            appointment_time = datetime.datetime.fromisoformat(
                slot["time"].replace("Z", "+00:00")
            )
        except Exception:
            logger.error(f"[Scheduling] Invalid datetime format: {slot['time']}")
            return {"status": "error", "error": "Invalid time format"}

        # ─────────────────────────────────────────
        # Calendar scheduling
        # ─────────────────────────────────────────

        calendar_event_id = await _calendar_scheduler.schedule_appointment(
            patient_name=patient_id,
            provider_name=slot["doctor"],
            appointment_time=appointment_time,
            duration_minutes=slot["duration"],
            description=f"Critical patient {patient_id}: {doctor_note}"
        )

        logger.info(
            f"[Hospital API] Booked {patient_id} → {slot['doctor']} @ {slot['time']}"
        )

        return {
            "status": "confirmed",
            "appointment": appointment,
            "calendar_event_id": calendar_event_id
        }