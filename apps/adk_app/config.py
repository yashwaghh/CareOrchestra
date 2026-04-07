"""Configuration management for CareOrchestra ADK application."""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class GoogleConfig:
    """Google Cloud configuration."""
    project_id: str = os.getenv("GCP_PROJECT_ID", "")
    location: str = os.getenv("GCP_LOCATION", "us-central1")
    bigquery_dataset: str = os.getenv("BIGQUERY_DATASET", "care_orchestra")


@dataclass
class GmailConfig:
    """Gmail integration configuration."""
    sender_email: str = os.getenv("GMAIL_SENDER_EMAIL", "")
    use_mock: bool = os.getenv("GMAIL_USE_MOCK", "true").lower() == "true"


@dataclass
class CalendarConfig:
    """Google Calendar integration configuration."""
    calendar_id: str = os.getenv("CALENDAR_ID", "primary")
    use_mock: bool = os.getenv("CALENDAR_USE_MOCK", "true").lower() == "true"
    # Path to a service-account JSON file, or a raw JSON string of the credentials.
    # When set, the scheduler will use this instead of Application Default Credentials.
    credentials_file: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    credentials_json: Optional[str] = os.getenv("GOOGLE_CREDENTIALS_JSON")


@dataclass
class Config:
    """Central configuration for CareOrchestra."""
    google_api_key: str = os.getenv("GOOGLE_API_KEY")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Add other keys as you need them
    postgres_url: str = os.getenv("DATABASE_URL")
    bigquery_project: str = os.getenv("GCP_PROJECT_ID")

def get_config() -> Config:
    """Helper function to return the config object."""
    return Config()