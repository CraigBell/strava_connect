"""Camera for Strava."""

from __future__ import annotations

import io
import logging
import os
import pickle
from datetime import timedelta
from hashlib import md5

import aiofiles
import aiohttp
from homeassistant.components.camera import Camera
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_IMG_UPDATE_INTERVAL_SECONDS,
    CONF_IMG_UPDATE_INTERVAL_SECONDS_DEFAULT,
    CONF_MAX_NB_IMAGES,
    CONF_PHOTOS,
    CONF_PHOTOS_ENTITY,
    CONFIG_URL_DUMP_FILENAME,
    DOMAIN,
    MAX_NB_ACTIVITIES,
)
from .coordinator import StravaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

_DEFAULT_IMAGE_URL = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/"
    "No_image_available_600_x_450.svg/1280px-No_image_available_600_x_450.svg.png"
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Camera that displays images from Strava."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    athlete_id = config_entry.unique_id
    default_enabled = config_entry.options.get(CONF_PHOTOS, False)

    url_cam = UrlCam(
        coordinator, default_enabled=default_enabled, athlete_id=athlete_id
    )
    await url_cam.setup_pickle_urls()
    async_add_entities([url_cam])

    async def image_update_listener(_):
        await url_cam.rotate_img()

    img_update_interval_seconds = int(
        config_entry.options.get(
            CONF_IMG_UPDATE_INTERVAL_SECONDS,
            CONF_IMG_UPDATE_INTERVAL_SECONDS_DEFAULT,
        )
    )

    async_track_time_interval(
        hass, image_update_listener, timedelta(seconds=img_update_interval_seconds)
    )


class UrlCam(CoordinatorEntity, Camera):
    """A camera that cycles through a list of image URLs."""

    _attr_name = CONF_PHOTOS_ENTITY
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: StravaDataUpdateCoordinator,
        athlete_id: str,
        default_enabled=True,
    ):
        """Initialize the camera."""
        super().__init__(coordinator)
        Camera.__init__(self)
        self._athlete_id = athlete_id
        self._attr_unique_id = f"{CONF_PHOTOS_ENTITY}_{self._athlete_id}"
        self._url_dump_filepath = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"{self._athlete_id}_{CONFIG_URL_DUMP_FILENAME}",
        )
        self._urls = {}
        self._url_index = 0
        self._attr_entity_registry_enabled_default = default_enabled

    async def setup_pickle_urls(self):
        """Load image URLs from pickle file."""
        if os.path.exists(self._url_dump_filepath):
            await self._load_pickle_urls()
        else:
            await self._store_pickle_urls()

    async def _load_pickle_urls(self):
        try:
            async with aiofiles.open(self._url_dump_filepath, "rb") as file:
                self._urls = pickle.load(io.BytesIO(await file.read()))
        except (OSError, pickle.PickleError) as err:
            _LOGGER.error(f"Error loading pickled URLs: {err}")

    async def _store_pickle_urls(self):
        try:
            async with aiofiles.open(self._url_dump_filepath, "wb") as file:
                await file.write(pickle.dumps(self._urls))
        except (OSError, pickle.PickleError) as err:
            _LOGGER.error(f"Error storing pickled URLs: {err}")

    async def async_camera_image(
        self,
        width: int | None = None,
        height: int | None = None,  # pylint: disable=unused-argument
    ) -> bytes | None:
        """Return the image for the current URL."""
        if not self._urls:
            return await _return_default_img()

        url = list(self._urls.values())[self._url_index]["url"]
        try:
            async with aiohttp.ClientSession() as session, session.get(
                url=url, timeout=10
            ) as response:
                if response.status == 200:
                    return await response.read()
        except aiohttp.ClientError as err:
            _LOGGER.error(f"Error fetching image from {url}: {err}")
        return await _return_default_img()

    async def rotate_img(self):
        """Rotate to the next image."""
        if self._urls:
            self._url_index = (self._url_index + 1) % len(self._urls)
            self.async_write_ha_state()

    @property
    def state(self):  # pylint: disable=overridden-final-method
        """Return the current image URL."""
        if not self._urls:
            return _DEFAULT_IMAGE_URL
        return list(self._urls.values())[self._url_index]["url"]

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if not self._urls:
            return {"img_url": _DEFAULT_IMAGE_URL}
        return {"img_url": list(self._urls.values())[self._url_index]["url"]}

    async def _update_urls(self):
        if self.coordinator.data and self.coordinator.data.get("images"):
            # Get the 30 most recent activities
            activities = self.coordinator.data.get("activities", [])
            recent_activity_ids = set()

            if activities:
                # Sort activities by date and take the 30 most recent
                sorted_activities = sorted(
                    activities, key=lambda x: x.get("start_date", ""), reverse=True
                )[:MAX_NB_ACTIVITIES]
                recent_activity_ids = {activity["id"] for activity in sorted_activities}

            # Filter images to only include those from recent activities
            for img_url in self.coordinator.data["images"]:
                if img_url.get("activity_id") in recent_activity_ids:
                    self._urls[md5(img_url["url"].encode()).hexdigest()] = img_url

            # Sort by date and limit to max number of images
            self._urls = dict(
                sorted(self._urls.items(), key=lambda item: item[1]["date"])[
                    -CONF_MAX_NB_IMAGES:
                ]
            )
            await self._store_pickle_urls()

    async def async_added_to_hass(self):
        """Handle entity being added to Home Assistant."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )
        await self._update_urls()

    def _handle_coordinator_update(self) -> None:
        self.hass.async_create_task(self._update_urls())
        self.async_write_ha_state()


async def _return_default_img():
    try:
        async with aiohttp.ClientSession() as session, session.get(
            url=_DEFAULT_IMAGE_URL, timeout=10
        ) as img_response:
            if img_response.status == 200:
                return await img_response.read()
    except aiohttp.ClientError as err:
        _LOGGER.error(f"Error fetching default image: {err}")
    return None
