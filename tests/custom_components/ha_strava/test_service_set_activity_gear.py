"""Tests for the set_activity_gear service."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_strava import _async_handle_set_activity_gear
from custom_components.ha_strava.api import (
    StravaNotFoundError,
    StravaRateLimitError,
    StravaUnauthorizedError,
)
from custom_components.ha_strava.const import (
    ATTR_ACTIVITY_ID,
    ATTR_SHOE_ID,
    ATTR_SHOE_NAME,
    CONF_ATTR_CATALOG_TIMESTAMP,
    CONF_ATTR_SHOES,
    CONF_GRANTED_SCOPES,
    DOMAIN,
    REQUIRED_STRAVA_SCOPES,
)


@pytest.mark.asyncio
async def test_set_activity_gear_success(hass: HomeAssistant):
    """Service should resolve shoe name and update activity gear."""
    async for hass_instance in hass:
        hass = hass_instance
        break

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="12345",
        data={
            CONF_GRANTED_SCOPES: REQUIRED_STRAVA_SCOPES,
        },
    )

    coordinator = MagicMock()
    coordinator.entry = entry
    coordinator.data = {
        "shoes_catalog": {
            CONF_ATTR_SHOES: [
                {"id": "shoe-1", "name": "Daily Trainer"},
            ],
            CONF_ATTR_CATALOG_TIMESTAMP: "2024-01-01T00:00:00Z",
        }
    }
    coordinator.client = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()

    hass.data[DOMAIN] = {entry.entry_id: coordinator}
    hass.bus.async_fire = MagicMock()

    call = ServiceCall(
        DOMAIN,
        "set_activity_gear",
        {
            ATTR_ACTIVITY_ID: "1234567890",
            ATTR_SHOE_NAME: "Daily Trainer",
        },
    )

    await _async_handle_set_activity_gear(hass, call)
    coordinator.client.async_update_activity_gear.assert_awaited_once_with(
        "1234567890", "shoe-1"
    )
    hass.bus.async_fire.assert_called_once()
    await hass.async_block_till_done()
    coordinator.async_request_refresh.assert_awaited()


@pytest.mark.asyncio
async def test_set_activity_gear_requires_scopes(hass: HomeAssistant):
    """Service should block when required scopes are missing."""
    async for hass_instance in hass:
        hass = hass_instance
        break

    entry = MockConfigEntry(domain=DOMAIN, unique_id="12345", data={})

    coordinator = MagicMock()
    coordinator.entry = entry
    coordinator.data = {"shoes_catalog": {CONF_ATTR_SHOES: []}}
    coordinator.client = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()

    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    hass.config_entries.flow.async_init = AsyncMock(return_value=None)

    call = ServiceCall(
        DOMAIN,
        "set_activity_gear",
        {ATTR_ACTIVITY_ID: "123", ATTR_SHOE_ID: "shoe-1"},
    )

    with pytest.raises(HomeAssistantError):
        await _async_handle_set_activity_gear(hass, call)

    hass.config_entries.flow.async_init.assert_awaited()
    coordinator.client.async_update_activity_gear.assert_not_called()


@pytest.mark.asyncio
async def test_set_activity_gear_handles_unauthorized(hass: HomeAssistant):
    """Service should prompt reauth on unauthorized responses."""
    async for hass_instance in hass:
        hass = hass_instance
        break

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="12345",
        data={CONF_GRANTED_SCOPES: REQUIRED_STRAVA_SCOPES},
    )

    coordinator = MagicMock()
    coordinator.entry = entry
    coordinator.data = {"shoes_catalog": {CONF_ATTR_SHOES: []}}
    coordinator.client = AsyncMock()
    coordinator.client.async_update_activity_gear.side_effect = StravaUnauthorizedError(
        "missing scope"
    )
    coordinator.async_request_refresh = AsyncMock()

    hass.data[DOMAIN] = {entry.entry_id: coordinator}
    hass.config_entries.flow.async_init = AsyncMock(return_value=None)

    call = ServiceCall(
        DOMAIN,
        "set_activity_gear",
        {ATTR_ACTIVITY_ID: "123", ATTR_SHOE_ID: "shoe-1"},
    )

    with pytest.raises(HomeAssistantError):
        await _async_handle_set_activity_gear(hass, call)

    hass.config_entries.flow.async_init.assert_awaited()


@pytest.mark.asyncio
async def test_set_activity_gear_handles_not_found(hass: HomeAssistant):
    """Service should surface a user error when activity is missing."""
    async for hass_instance in hass:
        hass = hass_instance
        break

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="12345",
        data={CONF_GRANTED_SCOPES: REQUIRED_STRAVA_SCOPES},
    )

    coordinator = MagicMock()
    coordinator.entry = entry
    coordinator.data = {"shoes_catalog": {CONF_ATTR_SHOES: []}}
    coordinator.client = AsyncMock()
    coordinator.client.async_update_activity_gear.side_effect = StravaNotFoundError(
        "not found"
    )
    coordinator.async_request_refresh = AsyncMock()

    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    call = ServiceCall(
        DOMAIN,
        "set_activity_gear",
        {ATTR_ACTIVITY_ID: "123", ATTR_SHOE_ID: "shoe-1"},
    )

    with pytest.raises(HomeAssistantError):
        await _async_handle_set_activity_gear(hass, call)


@pytest.mark.asyncio
async def test_set_activity_gear_handles_rate_limit(hass: HomeAssistant):
    """Service should surface rate-limit guidance."""
    async for hass_instance in hass:
        hass = hass_instance
        break

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="12345",
        data={CONF_GRANTED_SCOPES: REQUIRED_STRAVA_SCOPES},
    )

    coordinator = MagicMock()
    coordinator.entry = entry
    coordinator.data = {"shoes_catalog": {CONF_ATTR_SHOES: []}}
    coordinator.client = AsyncMock()
    coordinator.client.async_update_activity_gear.side_effect = StravaRateLimitError(
        "slow down"
    )
    coordinator.async_request_refresh = AsyncMock()

    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    call = ServiceCall(
        DOMAIN,
        "set_activity_gear",
        {ATTR_ACTIVITY_ID: "123", ATTR_SHOE_ID: "shoe-1"},
    )

    with pytest.raises(HomeAssistantError):
        await _async_handle_set_activity_gear(hass, call)
