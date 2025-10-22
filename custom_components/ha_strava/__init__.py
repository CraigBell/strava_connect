"""Strava Home Assistant Custom Component"""

import json
import logging
from http import HTTPStatus

import aiohttp
import voluptuous as vol
from aiohttp.web import Request, Response, json_response
from homeassistant.components.http.view import HomeAssistantView
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntry
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .api import (
    StravaApiError,
    StravaNotFoundError,
    StravaRateLimitError,
    StravaUnauthorizedError,
)
from .const import (
    ATTR_ACTIVITY_ID,
    ATTR_SHOE_ID,
    ATTR_SHOE_NAME,
    CONF_ATTR_CATALOG_TIMESTAMP,
    CONF_ATTR_SHOES,
    CONF_CALLBACK_URL,
    CONF_GRANTED_SCOPES,
    DOMAIN,
    EVENT_ACTIVITY_GEAR_SET,
    REQUIRED_STRAVA_SCOPES,
    SERVICE_SET_ACTIVITY_GEAR,
    WEBHOOK_SUBSCRIPTION_URL,
)
from .coordinator import StravaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "camera"]

SERVICE_SET_ACTIVITY_GEAR_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ACTIVITY_ID): vol.Any(str, int),
        vol.Optional(ATTR_SHOE_ID): vol.Any(str, int),
        vol.Optional(ATTR_SHOE_NAME): str,
    }
)


def _missing_scopes(entry: ConfigEntry) -> set[str]:
    granted = set(entry.data.get(CONF_GRANTED_SCOPES, []))
    return set(REQUIRED_STRAVA_SCOPES) - granted


def _schedule_reauth(hass: HomeAssistant, entry: ConfigEntry) -> None:
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_REAUTH},
            data={**entry.data},
        )
    )


async def _async_handle_set_activity_gear(
    hass: HomeAssistant, call: ServiceCall
) -> None:
    domain_data = hass.data.get(DOMAIN)
    if not domain_data:
        raise HomeAssistantError("Strava Connect is not configured.")

    entry_id = call.data.get("config_entry_id")
    coordinator: StravaDataUpdateCoordinator | None = None

    if entry_id:
        coordinator = domain_data.get(entry_id)
    else:
        # Default to the first coordinator-like object stored for the domain
        for candidate in domain_data.values():
            if hasattr(candidate, "async_request_refresh"):
                coordinator = candidate
                break

    if coordinator is None:
        raise HomeAssistantError("No Strava Connect coordinator available.")

    entry = coordinator.entry
    missing = _missing_scopes(entry)
    if missing:
        _LOGGER.error(
            "Blocking set_activity_gear service; missing scopes: %s", sorted(missing)
        )
        _schedule_reauth(hass, entry)
        raise HomeAssistantError(
            "Strava authorization is missing required permissions. Please reauthorize the Strava Connect integration."
        )

    activity_id_raw = call.data[ATTR_ACTIVITY_ID]
    activity_id = str(activity_id_raw)
    shoe_id = call.data.get(ATTR_SHOE_ID)
    shoe_name = call.data.get(ATTR_SHOE_NAME)

    if shoe_id is not None and shoe_id != "":
        shoe_id = str(shoe_id)

    if not shoe_id and not shoe_name:
        raise ServiceValidationError("Provide shoe_id or shoe_name to set gear.")

    shoes_catalog = (coordinator.data or {}).get("shoes_catalog", {})
    shoes = shoes_catalog.get(CONF_ATTR_SHOES, [])

    resolved_shoe_name = shoe_name

    if shoe_name and not shoe_id:
        match = next((shoe for shoe in shoes if shoe.get("name") == shoe_name), None)
        if not match:
            raise HomeAssistantError(
                f"Shoe named '{shoe_name}' not found in the Strava catalog."
            )
        shoe_id = match.get("id")
        if not shoe_id:
            raise HomeAssistantError(
                f"Shoe '{shoe_name}' does not have a Strava id and cannot be assigned."
            )
    elif shoe_id and not shoe_name:
        match = next((shoe for shoe in shoes if shoe.get("id") == shoe_id), None)
        if match:
            resolved_shoe_name = match.get("name")

    if not shoe_id:
        raise ServiceValidationError("A valid shoe_id is required for this service.")

    try:
        await coordinator.client.async_update_activity_gear(activity_id, shoe_id)
    except StravaUnauthorizedError as err:
        _schedule_reauth(hass, entry)
        raise HomeAssistantError(
            "Strava authorization missing required permissions. Please reauthorize."
        ) from err
    except StravaNotFoundError as err:
        raise HomeAssistantError("Strava activity not found.") from err
    except StravaRateLimitError as err:
        raise HomeAssistantError("Strava rate limit reached. Try again later.") from err
    except StravaApiError as err:
        raise HomeAssistantError(f"Failed to update Strava activity: {err}") from err

    event_data = {
        ATTR_ACTIVITY_ID: activity_id,
        ATTR_SHOE_ID: shoe_id,
        ATTR_SHOE_NAME: resolved_shoe_name,
        CONF_ATTR_CATALOG_TIMESTAMP: shoes_catalog.get(CONF_ATTR_CATALOG_TIMESTAMP),
    }
    hass.bus.async_fire(EVENT_ACTIVITY_GEAR_SET, event_data)

    hass.async_create_task(coordinator.async_request_refresh())


class StravaWebhookView(HomeAssistantView):
    """
    API endpoint subscribing to Strava's Webhook in order to handle asynchronous updates
    of HA sensor entities
    Strava Webhook Doku: https://developers.strava.com/docs/webhooks/
    """

    url = "/api/strava/webhook"
    name = "api:strava:webhook"
    requires_auth = False
    cors_allowed = True

    def __init__(self, hass: HomeAssistant):
        """Init the view."""
        self.hass = hass

    async def get(self, request: Request) -> Response:
        """Handle the incoming webhook challenge."""
        _LOGGER.debug(
            f"Strava Endpoint got a GET request from {request.headers.get('Host', None)}"
        )
        challenge = request.query.get("hub.challenge")
        if challenge:
            return json_response({"hub.challenge": challenge})
        return Response(status=HTTPStatus.OK)

    async def post(self, request: Request) -> Response:
        """Handle incoming post request to trigger a data refresh."""
        request_host = request.headers.get("Host", None)
        _LOGGER.debug(
            f"Strava Webhook Endpoint received a POST request from: {request_host}"
        )

        try:
            data = await request.json()
            owner_id = data.get("owner_id")
        except json.JSONDecodeError:
            _LOGGER.error("Invalid JSON received in webhook")
            return Response(status=HTTPStatus.BAD_REQUEST)

        if not owner_id:
            _LOGGER.warning("Webhook received without owner_id")
            return Response(status=HTTPStatus.OK)

        # Find the coordinator for this user
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.unique_id == str(owner_id):
                coordinator: StravaDataUpdateCoordinator = self.hass.data[DOMAIN][
                    entry.entry_id
                ]
                self.hass.async_create_task(coordinator.async_request_refresh())
                break
        else:
            _LOGGER.warning(f"Webhook received for unknown user: {owner_id}")

        return Response(status=HTTPStatus.OK)


async def renew_webhook_subscription(
    hass: HomeAssistant,
    entry: ConfigEntry,
):
    """
    Subscribes to the Strava Webhook API.
    """
    try:
        ha_host = get_url(hass, allow_internal=False, allow_ip=False)
    except NoURLAvailableError:
        _LOGGER.error(
            "Your Home Assistant Instance does not seem to have a public URL."
            " The Strava Home Assistant integration requires a public URL"
        )
        return

    callback_url = f"{ha_host}/api/strava/webhook"
    websession = async_get_clientsession(hass, verify_ssl=False)

    # Check home assistant callback URL is available
    try:
        async with websession.get(url=callback_url) as response:
            response.raise_for_status()
            _LOGGER.debug(f"HA webhook available: {response}")
    except aiohttp.ClientError as err:
        _LOGGER.error(
            f"HA Callback URL for Strava Webhook not available: {err}"  # noqa:E501
        )
        return

    # Check for existing subscriptions
    try:
        async with websession.get(
            WEBHOOK_SUBSCRIPTION_URL,
            params={
                "client_id": entry.data[CONF_CLIENT_ID],
                "client_secret": entry.data[CONF_CLIENT_SECRET],
            },
        ) as response:
            response.raise_for_status()
            subscriptions = await response.json()

        # Delete any existing subscriptions for this app that are not the current one
        for sub in subscriptions:
            if sub["callback_url"] != callback_url:
                _LOGGER.debug(f"Deleting outdated webhook subscription: {sub['id']}")
                try:
                    async with websession.delete(
                        f"{WEBHOOK_SUBSCRIPTION_URL}/{sub['id']}",
                        data={
                            "client_id": entry.data[CONF_CLIENT_ID],
                            "client_secret": entry.data[CONF_CLIENT_SECRET],
                        },
                    ) as delete_response:
                        delete_response.raise_for_status()
                except aiohttp.ClientResponseError as err:
                    if err.status == 404:
                        _LOGGER.debug(
                            f"Webhook subscription {sub['id']} already deleted or doesn't exist"
                        )
                    else:
                        _LOGGER.warning(
                            f"Failed to delete webhook subscription {sub['id']}: {err}"
                        )
                except aiohttp.ClientError as err:
                    _LOGGER.warning(
                        f"Failed to delete webhook subscription {sub['id']}: {err}"
                    )

        if any(sub["callback_url"] == callback_url for sub in subscriptions):
            _LOGGER.debug("Webhook subscription is already up to date.")
            return

    except aiohttp.ClientError as err:
        _LOGGER.error(f"Error managing webhook subscriptions: {err}")
        return

    # Create a new subscription
    try:
        _LOGGER.debug(f"Creating new webhook subscription for {callback_url}")
        async with websession.post(
            WEBHOOK_SUBSCRIPTION_URL,
            data={
                CONF_CLIENT_ID: entry.data[CONF_CLIENT_ID],
                CONF_CLIENT_SECRET: entry.data[CONF_CLIENT_SECRET],
                CONF_CALLBACK_URL: callback_url,
                "verify_token": "HA_STRAVA",
            },
        ) as response:
            response.raise_for_status()
            new_sub = await response.json()

            mutable_data = {**entry.data}
            mutable_data[CONF_WEBHOOK_ID] = new_sub["id"]
            hass.config_entries.async_update_entry(entry, data=mutable_data)

    except aiohttp.ClientError as err:
        _LOGGER.error(f"Error creating webhook subscription: {err}")


async def async_setup(
    hass: HomeAssistant, config: dict
):  # pylint: disable=unused-argument
    """Set up the Strava component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Strava Home Assistant from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = StravaDataUpdateCoordinator(hass, entry=entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    missing = _missing_scopes(entry)
    if missing:
        _LOGGER.warning(
            "Strava Connect entry missing required scopes: %s", sorted(missing)
        )
        _schedule_reauth(hass, entry)

    if not hass.services.has_service(DOMAIN, SERVICE_SET_ACTIVITY_GEAR):

        async def handle_service(call: ServiceCall) -> None:
            await _async_handle_set_activity_gear(hass, call)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_ACTIVITY_GEAR,
            handle_service,
            schema=SERVICE_SET_ACTIVITY_GEAR_SCHEMA,
        )

    # Set up webhook
    hass.http.register_view(StravaWebhookView(hass))
    await renew_webhook_subscription(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Clean up webhook subscription
        if webhook_id := entry.data.get(CONF_WEBHOOK_ID):
            try:
                websession = async_get_clientsession(hass)
                async with websession.delete(
                    f"{WEBHOOK_SUBSCRIPTION_URL}/{webhook_id}",
                    data={
                        "client_id": entry.data[CONF_CLIENT_ID],
                        "client_secret": entry.data[CONF_CLIENT_SECRET],
                    },
                ) as response:
                    response.raise_for_status()
                    _LOGGER.debug("Successfully deleted webhook subscription")
            except aiohttp.ClientError as err:
                _LOGGER.error(f"Failed to delete webhook subscription: {err}")

        hass.data[DOMAIN].pop(entry.entry_id)

        if not hass.data[DOMAIN] and hass.services.has_service(
            DOMAIN, SERVICE_SET_ACTIVITY_GEAR
        ):
            hass.services.async_remove(DOMAIN, SERVICE_SET_ACTIVITY_GEAR)

    return unload_ok
