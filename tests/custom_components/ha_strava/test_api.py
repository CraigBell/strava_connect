"""Tests for the Strava API helper."""

from unittest.mock import AsyncMock

import pytest

from custom_components.ha_strava.api import StravaClient, StravaRateLimitError


class MockResponse:
    """Minimal aiohttp response stub."""

    def __init__(self, *, status=200, json_data=None, headers=None):
        self.status = status
        self._json_data = json_data or {}
        self.headers = headers or {}

    async def json(self):
        return self._json_data

    async def text(self):
        return ""

    def raise_for_status(self):
        if self.status >= 400:
            raise Exception(f"HTTP {self.status}")


@pytest.mark.asyncio
async def test_get_athlete_normalizes_gear():
    """Athlete response should be normalized for shoes and bikes."""
    mock_session = AsyncMock()
    mock_session.async_request.return_value = MockResponse(
        json_data={
            "id": 42,
            "firstname": "Craig",
            "shoes": [
                {
                    "id": "shoe-1",
                    "name": "Daily Trainer",
                    "brand_name": "BrandA",
                    "model_name": "ModelX",
                    "distance": 1234.5,
                    "primary": True,
                    "retired": False,
                }
            ],
            "bikes": [
                {
                    "id": "bike-1",
                    "name": "Road Bike",
                    "brand_name": "BrandB",
                    "model_name": "ModelY",
                    "distance": 5000,
                }
            ],
        }
    )

    client = StravaClient(mock_session)
    athlete = await client.async_get_athlete()

    assert athlete["shoes"][0]["distance_m"] == 1234
    assert athlete["shoes"][0]["strava_url"].endswith("shoe-1")
    assert athlete["bikes"][0]["distance_m"] == 5000


@pytest.mark.asyncio
async def test_update_activity_gear_payload():
    """Updating gear should send only the gear_id payload."""
    mock_session = AsyncMock()
    mock_session.async_request.return_value = MockResponse()

    client = StravaClient(mock_session)

    await client.async_update_activity_gear("123", "shoe-1")

    mock_session.async_request.assert_awaited_once()
    kwargs = mock_session.async_request.call_args.kwargs
    assert kwargs["method"] == "PUT"
    assert kwargs["json"] == {"gear_id": "shoe-1"}


@pytest.mark.asyncio
async def test_rate_limit_raises_error():
    """429 responses should raise a StravaRateLimitError."""
    mock_session = AsyncMock()
    mock_session.async_request.return_value = MockResponse(
        status=429,
        headers={
            "X-RateLimit-Limit": "600,30000",
            "X-RateLimit-Usage": "600,25000",
        },
    )

    client = StravaClient(mock_session)

    with pytest.raises(StravaRateLimitError):
        await client.async_get_activity("123")
