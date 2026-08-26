"""
Application Settings and Configuration Loader.
Uses pydantic for robust environment variable validation.
"""
from pathlib import Path
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Root directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env if present
load_dotenv(BASE_DIR / ".env")


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str = Field(
        default="",
        alias="TELEGRAM_BOT_TOKEN",
        description="Bot token from @BotFather"
    )
    telegram_channel_id: str = Field(
        default="@your_channel_username",
        alias="TELEGRAM_CHANNEL_ID",
        description="Channel username with @ or numeric chat id"
    )

    # Gemini
    gemini_api_key: str = Field(
        default="",
        alias="GEMINI_API_KEY",
        description="Google Gemini API key"
    )
    gemini_model: str = Field(
        default="gemini-3.1-flash-lite",
        alias="GEMINI_MODEL",
        description="Model name for JSON extraction"
    )

    # Operational rules
    daily_max_jobs: int = Field(
        default=15,
        alias="DAILY_MAX_JOBS",
        description="Maximum total new jobs to post per day"
    )
    max_jobs_per_message: int = Field(
        default=15,
        alias="MAX_JOBS_PER_MESSAGE",
        description="Maximum number of jobs per message block"
    )
    deduplication_days: int = Field(
        default=7,
        alias="DEDUPLICATION_DAYS",
        description="Window in days to filter out previously posted jobs"
    )
    daily_schedule_time: str = Field(
        default="09:00",
        alias="DAILY_SCHEDULE_TIME",
        description="Daily execution time (HH:MM)"
    )

    # Paths
    database_path: str = Field(
        default="data/jobs.db",
        alias="DATABASE_PATH",
        description="Relative or absolute path to SQLite database"
    )
    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Logging level"
    )

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def db_full_path(self) -> Path:
        p = Path(self.database_path)
        if not p.is_absolute():
            return BASE_DIR / p
        return p

    @property
    def logs_dir(self) -> Path:
        logs_path = BASE_DIR / "logs"
        logs_path.mkdir(parents=True, exist_ok=True)
        return logs_path

    @field_validator("max_jobs_per_message")
    @classmethod
    def validate_max_jobs(cls, v: int) -> int:
        if v < 1:
            return 1
        if v > 25:
            return 25
        return v


# Global singleton instance
settings = Settings()
