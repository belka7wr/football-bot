"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ConfigurationError(ValueError):
    """Raised when required bot configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the Telegram bot."""

    telegram_bot_token: str
    sports_api_token: str
    sports_api_base_url: str = "https://sports.bzzoiro.com/api/v2"
    timezone_name: str = "Europe/Moscow"

    @property
    def timezone(self) -> tzinfo:
        """Return the configured timezone."""

        try:
            return ZoneInfo(self.timezone_name)
        except ZoneInfoNotFoundError as error:
            raise ConfigurationError(
                f"Invalid timezone: {self.timezone_name}"
            ) from error

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from environment variables."""

        telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        sports_api_token = os.getenv("SPORTS_API_TOKEN", "").strip()

        missing = []

        if not telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")

        if not sports_api_token:
            missing.append("SPORTS_API_TOKEN")

        if missing:
            raise ConfigurationError(
                "Missing required environment variable(s): "
                + ", ".join(missing)
            )

        settings = cls(
            telegram_bot_token=telegram_bot_token,
            sports_api_token=sports_api_token,
            sports_api_base_url=(
                os.getenv(
                    "SPORTS_API_BASE_URL",
                    "https://sports.bzzoiro.com/api/v2",
                ).strip()
                or "https://sports.bzzoiro.com/api/v2"
            ).rstrip("/"),
            timezone_name=(
                os.getenv("BOT_TIMEZONE", "Europe/Moscow").strip()
                or "Europe/Moscow"
            ),
        )

        # Validate timezone during startup.
        _ = settings.timezone

        return settings
