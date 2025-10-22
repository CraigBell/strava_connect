"""HTTP client helpers for Strava Connect."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping

import aiohttp

from .gear import normalize_bike, normalize_shoe

LOGGER = logging.getLogger(__name__)

BASE_URL = "https://www.strava.com/api/v3"


@dataclass(slots=True)
class RateLimitInfo:
    """Structured representation of Strava rate-limit headers."""

    short_limit: int | None = None
    long_limit: int | None = None
    short_usage: int | None = None
    long_usage: int | None = None

    @property
    def nearing_limit(self) -> bool:
        """Return True if current usage exceeds 90% of short quota."""
        if self.short_limit in (None, 0) or self.short_usage is None:
            return False
        return self.short_usage / self.short_limit >= 0.9


class StravaApiError(Exception):
    """Base Strava API error."""


class StravaUnauthorizedError(StravaApiError):
    """Raised when the API returns 401/403 (missing scopes or revoked token)."""


class StravaNotFoundError(StravaApiError):
    """Raised when requested resource is not found."""


class StravaRateLimitError(StravaApiError):
    """Raised when Strava reports that we hit the rate limit."""

    def __init__(self, message: str, rate_limit: RateLimitInfo | None = None):
        super().__init__(message)
        self.rate_limit = rate_limit


def _parse_header_pair(header_value: str | None) -> tuple[int | None, int | None]:
    """Parse comma separated header values into integers."""
    if not header_value:
        return (None, None)

    try:
        short, long = header_value.split(",")
        return int(short), int(long)
    except (ValueError, TypeError):
        return (None, None)


def _extract_rate_limit(headers: Mapping[str, str]) -> RateLimitInfo:
    """Create rate-limit info from response headers."""
    short_limit, long_limit = _parse_header_pair(headers.get("X-RateLimit-Limit"))
    short_usage, long_usage = _parse_header_pair(headers.get("X-RateLimit-Usage"))
    return RateLimitInfo(
        short_limit=short_limit,
        long_limit=long_limit,
        short_usage=short_usage,
        long_usage=long_usage,
    )


class StravaClient:
    """Small helper around Home Assistant's OAuth2 session."""

    def __init__(self, oauth_session):
        """Initialize client with an OAuth2Session instance."""
        self._session = oauth_session
        self._last_rate_limit: RateLimitInfo | None = None

    @property
    def last_rate_limit(self) -> RateLimitInfo | None:
        """Return the last seen rate-limit metadata."""
        return self._last_rate_limit

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_data: MutableMapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a Strava API request and return JSON payload."""
        url = f"{BASE_URL}{path}"
        LOGGER.debug("Strava API call %s %s", method.upper(), path)

        try:
            response = await self._session.async_request(
                method=method,
                url=url,
                json=json_data,
            )
        except aiohttp.ClientError as err:
            raise StravaApiError(f"Error communicating with Strava: {err}") from err

        self._last_rate_limit = _extract_rate_limit(response.headers)

        status = response.status
        if status == 429:
            LOGGER.warning("Strava rate limit reached (%s %s)", method.upper(), path)
            raise StravaRateLimitError(
                "Strava API rate limit reached", rate_limit=self._last_rate_limit
            )

        if status in (401, 403):
            LOGGER.warning(
                "Unauthorized Strava API response for %s %s (status=%s)",
                method.upper(),
                path,
                status,
            )
            raise StravaUnauthorizedError("Strava authorization failed")

        if status == 404:
            LOGGER.debug("Strava resource not found for %s %s", method.upper(), path)
            raise StravaNotFoundError("Strava resource not found")

        if status >= 400:
            text = await response.text()
            LOGGER.error(
                "Unexpected Strava API error for %s %s: HTTP %s, body=%s",
                method.upper(),
                path,
                status,
                text,
            )
            raise StravaApiError(f"Strava API error (HTTP {status})")

        try:
            return await response.json()
        except aiohttp.ContentTypeError:
            # Some PUT endpoints may return an empty body
            return {}

    async def async_get_athlete(self) -> dict[str, Any]:
        """Return athlete profile with normalized gear arrays."""
        payload = await self._request("GET", "/athlete")

        shoes = [normalize_shoe(item) for item in payload.get("shoes", [])]
        bikes = [normalize_bike(item) for item in payload.get("bikes", [])]

        return {
            "id": payload.get("id"),
            "firstname": payload.get("firstname"),
            "lastname": payload.get("lastname"),
            "profile": payload.get("profile"),
            "profile_medium": payload.get("profile_medium"),
            "bikes": bikes,
            "shoes": shoes,
        }

    async def async_get_activity(self, activity_id: str | int) -> dict[str, Any]:
        """Return detailed activity payload."""
        return await self._request("GET", f"/activities/{activity_id}")

    async def async_update_activity_gear(
        self, activity_id: str | int, gear_id: str
    ) -> dict[str, Any]:
        """Assign a gear item to an activity."""
        if not gear_id:
            raise ValueError("gear_id is required to update activity gear")

        return await self._request(
            "PUT", f"/activities/{activity_id}", json_data={"gear_id": gear_id}
        )
