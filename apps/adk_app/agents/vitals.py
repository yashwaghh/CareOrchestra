"""Vitals Agent - Analyzes vital signs and detects abnormal patterns."""


class VitalsAgent:
    """
    Analyzes vital signs:
    - Reads vital history (BP, heart rate, glucose, oxygen, etc.)
    - Detects abnormal values
    - Identifies trends (improving, worsening, stable)
    - Flags concerning patterns for escalation
    """

    def __init__(self):
        """Initialize vitals agent."""
        pass

    # -------------------------------
    # INTERNAL: Fetch vitals (from ADK state / DB later)
    # -------------------------------
    async def _fetch_vitals(self, patient_id: str):
        """
        For now, simulate DB fetch.
        Later replace with BigQuery using patient_id.
        """
        return [
            {"bp_systolic": 150, "bp_diastolic": 95, "glucose": 180, "spo2": 96, "heart_rate": 90},
            {"bp_systolic": 145, "bp_diastolic": 92, "glucose": 170, "spo2": 97, "heart_rate": 88},
            {"bp_systolic": 138, "bp_diastolic": 88, "glucose": 160, "spo2": 98, "heart_rate": 85},
        ]

    # -------------------------------
    # RULES (can later move to risk_rules/vitals_rules.py)
    # -------------------------------
    def _apply_rules(self, vitals):
        issues = []
        latest = vitals[0]

        # Blood Pressure
        if latest["bp_systolic"] > 140 or latest["bp_diastolic"] > 90:
            issues.append({"type": "blood_pressure", "level": "high"})

        # Glucose
        if latest["glucose"] > 140:
            issues.append({"type": "glucose", "level": "high"})

        # Oxygen
        if latest["spo2"] < 95:
            issues.append({"type": "spo2", "level": "low"})

        # Heart Rate
        if latest["heart_rate"] > 100:
            issues.append({"type": "heart_rate", "level": "high"})

        return issues

    # -------------------------------
    # ANOMALY DETECTION
    # -------------------------------
    def _detect_anomalies(self, vitals):
        anomalies = []

        if len(vitals) < 2:
            return anomalies

        latest = vitals[0]
        prev = vitals[1]

        if abs(latest["glucose"] - prev["glucose"]) > 20:
            anomalies.append("sudden glucose change")

        if abs(latest["bp_systolic"] - prev["bp_systolic"]) > 20:
            anomalies.append("sudden BP change")

        return anomalies

    # -------------------------------
    # TREND CALCULATION
    # -------------------------------
    def _calculate_trend(self, values):
        if len(values) < 2:
            return "insufficient_data"

        if values[-1] > values[0]:
            return "increasing"
        elif values[-1] < values[0]:
            return "decreasing"
        return "stable"

    async def analyze_vitals(self, patient_id: str) -> dict:
        """
        Analyze patient vitals.
        """
        # ✅ 1. Query recent vitals
        vitals = await self._fetch_vitals(patient_id)

        if not vitals:
            return {"status": "no_data"}

        latest = vitals[0]

        # ✅ 2. Apply rules
        issues = self._apply_rules(vitals)

        # ✅ 3. Detect anomalies
        anomalies = self._detect_anomalies(vitals)

        # ✅ 4. Identify trends
        trends = {
            "glucose": self._calculate_trend(
                [v["glucose"] for v in reversed(vitals)]
            ),
            "bp_systolic": self._calculate_trend(
                [v["bp_systolic"] for v in reversed(vitals)]
            ),
        }

        # ✅ 5. Final result
        status = "normal"
        if issues or anomalies:
            status = "alert"

        return {
            "status": status,
            "patient_id": patient_id,
            "latest_vitals": latest,
            "issues": issues,
            "anomalies": anomalies,
            "trends": trends
        }

    async def check_trend(self, patient_id: str, vital_type: str) -> dict:
        """
        Check trend for specific vital over time.
        """
        # ✅ 1. Query historical vitals
        vitals = await self._fetch_vitals(patient_id)

        values = [v[vital_type] for v in reversed(vitals) if vital_type in v]

        # ✅ 2. Compute trend
        trend = self._calculate_trend(values)

        # ✅ 3. Assess risk
        risk = "normal"
        if trend == "increasing":
            risk = "warning"
        elif trend == "decreasing":
            risk = "improving"

        return {
            "vital_type": vital_type,
            "trend": trend,
            "risk": risk
        }