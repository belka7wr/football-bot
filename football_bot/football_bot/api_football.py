"""Async client for Bzzoiro Sports Data football events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx


class FootballApiError(RuntimeError):
    """Raised when the sports API returns an unusable response."""


@dataclass(frozen=True)
class Fixture:
    """Football match data used by the Telegram bot."""

    fixture_id: int | None
    kickoff: datetime | None
    home_team: str
    away_team: str
    league_name: str
    country: str | None
    status: str
    venue: str | None

    @staticmethod
    def _name(value: Any) -> str | None:
        if isinstance(value, str):
            return value.strip() or None

        if isinstance(value, dict):
            for key in ("name", "title", "short_name"):
                result = value.get(key)
                if result:
                    return str(result).strip()

        return None

    @staticmethod
    def _datetime(value: Any) -> datetime | None:
        if not isinstance(value, str):
            return None

        try:
            return datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError:
            return None

    @classmethod
    def from_api_response(
        cls,
        payload: dict[str, Any],
        timezone_name: str,
    ) -> "Fixture":
        fixture_id = payload.get("id")
        if not isinstance(fixture_id, int):
            fixture_id = None

        home_team = (
            cls._name(payload.get("home_team"))
            or cls._name(payload.get("home"))
            or cls._name(payload.get("homeTeam"))
            or "Unknown"
        )

        away_team = (
            cls._name(payload.get("away_team"))
            or cls._name(payload.get("away"))
            or cls._name(payload.get("awayTeam"))
            or "Unknown"
        )

        league_value = (
            payload.get("league")
            or payload.get("competition")
            or payload.get("tournament")
        )

        league_name = cls._name(league_value) or "Unknown competition"

        country = None

        if isinstance(league_value, dict):
            country = (
                cls._name(league_value.get("country"))
                or cls._name(league_value.get("country_name"))
            )

        if country is None:
            country = (
                cls._name(payload.get("country"))
                or cls._name(payload.get("country_name"))
            )

        kickoff = None

        # Try all common Bzzoiro/API date fields.
        for key in (
            "event_date",
            "kickoff",
            "kickoff_at",
            "start_time",
            "start_at",
            "datetime",
            "date",
        ):
            kickoff = cls._datetime(payload.get(key))
            if kickoff is not None:
                break

        if kickoff is not None:
            try:
                if kickoff.tzinfo is None:
                    kickoff = kickoff.replace(tzinfo=ZoneInfo("UTC"))

                kickoff = kickoff.astimezone(
                    ZoneInfo(timezone_name)
                )
            except Exception:
                pass

        status_value = payload.get("status") or "notstarted"

        if isinstance(status_value, dict):
            status_value = (
                status_value.get("name")
                or status_value.get("short")
                or status_value.get("long")
                or "notstarted"
            )

        status = str(status_value)

        venue = (
            cls._name(payload.get("venue"))
            or cls._name(payload.get("stadium"))
        )

        return cls(
            fixture_id=fixture_id,
            kickoff=kickoff,
            home_team=home_team,
            away_team=away_team,
            league_name=league_name,
            country=country,
            status=status,
            venue=venue,
        )


class ApiFootballClient:
    """Client for the Bzzoiro Sports Data API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://sports.bzzoiro.com/api/v2",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    async def get_fixtures(
        self,
        fixture_date: date,
        timezone_name: str,
    ) -> list[Fixture]:
        """Return football events for a calendar date."""

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(
                    20.0,
                    connect=10.0,
                ),
            ) as client:
                response = await client.get(
                    "/events/",
                    params={
                        "date_from": fixture_date.isoformat(),
                        "date_to": fixture_date.isoformat(),
                        "limit": 200,
                        "offset": 0,
                    },
                    headers={
                        "Authorization": f"Token {self._api_key}",
                        "Accept": "application/json",
                    },
                )

                response.raise_for_status()
                body = response.json()

        except httpx.HTTPStatusError as error:
            raise FootballApiError(
                f"Sports API returned HTTP "
                f"{error.response.status_code}."
            ) from error

        except httpx.HTTPError as error:
            raise FootballApiError(
                "Sports API request failed."
            ) from error

        except ValueError as error:
            raise FootballApiError(
                "Sports API returned invalid JSON."
            ) from error

        if not isinstance(body, dict):
            raise FootballApiError(
                "Sports API returned an unexpected response."
            )

        events = body.get("results")

        if not isinstance(events, list):
            events = body.get("events")

        if not isinstance(events, list):
            events = body.get("data")

        if not isinstance(events, list):
            raise FootballApiError(
                "Sports API returned no event list."
            )

        return [
            Fixture.from_api_response(
                event,
                timezone_name,
            )
            for event in events
            if isinstance(event, dict)
        ]
