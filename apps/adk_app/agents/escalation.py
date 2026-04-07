"""Escalation Agent - Handles high-risk scenarios and alerts doctors."""

import datetime
import logging
import os

from ..tools.bigquery_tools.client import BigQueryClient
from ..tools.gmail_tools.alert_sender import GmailSender

logger = logging.getLogger(__name__)

_bq_client = BigQueryClient(
    project_id=os.getenv("GCP_PROJECT_ID"),
    dataset_id="careorchestra"
)


class EscalationAgent:
    """
    Manages critical alerts:
    - Identifies high-risk situations requiring immediate attention
    - Formats alerts for clinician consumption
    - Routes alerts to appropriate healthcare providers via email
    - Logs escalation events to BigQuery for audit purposes
    """

    def __init__(self):
        """Initialize escalation agent with Gmail sender."""
        self.gmail = GmailSender(
            sender_email=os.getenv(
                "ALERT_SENDER_EMAIL", "careorchestra-alerts@example.com"
            ),
            use_mock=os.getenv("GMAIL_USE_MOCK", "true").lower() != "false",
        )
        self.default_doctor_email = os.getenv(
            "DOCTOR_EMAIL", "doctor@example.com"
        )

    async def escalate_alert(
        self,
        patient_id: str,
        risk_level: str,
        alert_summary: dict,
    ) -> dict:
        """
        Escalate a patient alert to the appropriate healthcare provider.

        Fetches escalation contacts, sends an alert email, and logs the event
        to BigQuery for audit purposes.

        Args:
            patient_id: Patient identifier.
            risk_level: Risk level string (``"high"`` or ``"critical"``).
            alert_summary: Dict with findings, recommendations, and/or a
                plain-text ``summary`` field produced by upstream agents.

        Returns:
            Escalation status dict with delivery confirmation.
        """
        escalated_at = datetime.datetime.utcnow().isoformat()

        contacts = await self.get_escalation_contacts(patient_id)
        if not contacts:
            contacts = [self.default_doctor_email]

        alert_content = self._format_alert(patient_id, risk_level, alert_summary)

        success = await self.send_alert_to_doctor(
            contacts[0], patient_id, alert_content
        )

        status = "sent" if success else "failed"
        masked_id = patient_id[-4:] if len(patient_id) >= 4 else patient_id
        logger.info(
            f"[Escalation] patient=***{masked_id} risk={risk_level} status={status}"
        )

        # Persist escalation event to BigQuery for audit trail
        logged = await self._log_escalation(patient_id, risk_level, alert_content, contacts)

        return {
            "escalation_status": status,
            "patient_id": patient_id,
            "risk_level": risk_level,
            "contacts_notified": contacts,
            "escalated_at": escalated_at,
            "alert_preview": alert_content[:200],
            "logged": logged,
        }

    async def send_alert_to_doctor(
        self,
        doctor_email: str,
        patient_name: str,
        alert_content: str,
    ) -> bool:
        """
        Send an alert email to a doctor via GmailSender.

        Args:
            doctor_email: Doctor's email address.
            patient_name: Patient identifier or name for the email.
            alert_content: Formatted alert body.

        Returns:
            ``True`` if delivery succeeded (or mock mode is active).
        """
        try:
            return await self.gmail.send_alert(
                doctor_email, patient_name, alert_content
            )
        except Exception as exc:
            logger.error(f"[Escalation] Email delivery failed: {exc}")
            return False

    async def get_escalation_contacts(self, patient_id: str) -> list:
        """
        Return escalation contacts for a patient.

        Queries the ``escalation_contacts`` BigQuery table first; falls back
        to the ``DOCTOR_EMAIL`` environment variable if the table has no rows
        or does not exist.

        Args:
            patient_id: Patient identifier.

        Returns:
            List of email addresses to notify.
        """
        try:
            query = f"""
            SELECT contact_email
            FROM `{_bq_client.project_id}.{_bq_client.dataset_id}.escalation_contacts`
            WHERE patient_id = @patient_id
            ORDER BY priority ASC
            LIMIT 5
            """
            results = await _bq_client.query(query, {"patient_id": patient_id})
            emails = [r.get("contact_email", "") for r in results if r.get("contact_email")]
            if emails:
                return emails
        except Exception:
            # Table may not exist yet — fall through to env-var fallback
            pass

        contact = os.getenv("DOCTOR_EMAIL", self.default_doctor_email)
        return [contact] if contact else []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_alert(
        patient_id: str, risk_level: str, alert_summary: dict
    ) -> str:
        """Build a human-readable clinical alert message."""
        lines = [
            f"⚠️  CLINICAL ALERT — {risk_level.upper()} RISK",
            f"Patient ID : {patient_id}",
            f"Risk Level : {risk_level.upper()}",
            f"Generated  : {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            "",
        ]

        # Plain-text summary (e.g. from CoordinatorAgent)
        if alert_summary.get("summary"):
            lines += ["Summary:", alert_summary["summary"], ""]

        # Structured findings from AnalysisAgent / MonitoringAgent
        findings = alert_summary.get("findings", [])
        if findings:
            lines.append("Findings:")
            for f in findings:
                severity_tag = f.get("severity", "").upper()
                lines.append(
                    f"  [{severity_tag}] {f.get('code', '')} — {f.get('description', '')}"
                )
            lines.append("")

        # Recommendations
        recommendations = alert_summary.get("recommendations", [])
        if recommendations:
            lines.append("Recommended Actions:")
            for rec in recommendations:
                lines.append(f"  • {rec}")
            lines.append("")

        lines.append("— CareOrchestra Automated Alert System —")
        return "\n".join(lines)

    async def _log_escalation(
        self,
        patient_id: str,
        risk_level: str,
        alert_content: str,
        notified: list,
    ) -> bool:
        """Persist the escalation event to BigQuery for audit purposes."""
        try:
            row = {
                "patient_id": patient_id,
                "risk_level": risk_level,
                "alert_content": alert_content[:1000],  # BigQuery column size cap
                "contacts_notified": ", ".join(notified),
                "created_at": datetime.datetime.utcnow().isoformat(),
            }
            return await _bq_client.insert("escalation_logs", [row])
        except Exception as e:
            logger.error(f"Failed to log escalation: {e}")
            return False
