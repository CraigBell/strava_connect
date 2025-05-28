# pylint: disable=too-many-arguments, protected-access, redefined-outer-name, too-many-positional-arguments, fixme
"""Tests for the sensor platform of the Strava Home Assistant integration."""

from unittest.mock import MagicMock

import pytest
from homeassistant.const import (  # UnitOfSpeed, # Removed as no speed tests yet
    UnitOfLength,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.util.unit_system import METRIC_SYSTEM, US_CUSTOMARY_SYSTEM

from custom_components.ha_strava.const import (
    CONF_ACTIVITY_TYPE_RIDE,
    CONF_ACTIVITY_TYPE_RUN,
    CONF_ACTIVITY_TYPE_SWIM,
    CONF_DISTANCE_UNIT_OVERRIDE,
    CONF_DISTANCE_UNIT_OVERRIDE_DEFAULT,
    CONF_DISTANCE_UNIT_OVERRIDE_IMPERIAL,
    CONF_DISTANCE_UNIT_OVERRIDE_METRIC,
    CONF_SENSOR_ACTIVITY_COUNT,
    CONF_SENSOR_CALORIES,
    CONF_SENSOR_DEFAULT,
    CONF_SENSOR_DISTANCE,
    CONF_SENSOR_ELEVATION,
    CONF_SENSOR_HEART_RATE_AVG,
    CONF_SENSOR_MOVING_TIME,
    CONF_SENSOR_PACE,
    CONF_SENSOR_POWER,
    CONF_SUMMARY_ALL,
    CONF_SUMMARY_RECENT,
    CONF_SUMMARY_YTD,
    UNIT_BEATS_PER_MINUTE,
    UNIT_KILO_CALORIES,
    UNIT_PACE_MINUTES_PER_KILOMETER,
    UNIT_PACE_MINUTES_PER_MILE,
)
from custom_components.ha_strava.sensor import (
    StravaStatsSensor,
    StravaSummaryStatsSensor,
)


@pytest.fixture
def mock_hass_metric():
    """Fixture for a mock HomeAssistant object with metric units."""
    hass = MagicMock()
    hass.config.units = METRIC_SYSTEM
    return hass


@pytest.fixture
def mock_hass_imperial():
    """Fixture for a mock HomeAssistant object with imperial units."""
    hass = MagicMock()
    hass.config.units = (
        US_CUSTOMARY_SYSTEM  # US_CUSTOMARY_SYSTEM is often used for imperial in HA
    )
    return hass


def create_summary_sensor(
    hass, activity_type, metric, summary_type, initial_data=None, config_override=None
):
    """Helper function to create and configure a StravaSummaryStatsSensor for testing."""
    sensor = StravaSummaryStatsSensor(activity_type, metric, summary_type)
    sensor.hass = hass
    sensor._data = initial_data if initial_data else {}

    # Mock config_entry for distance unit override
    mock_config_entry = MagicMock()
    if config_override:
        mock_config_entry.options = {CONF_DISTANCE_UNIT_OVERRIDE: config_override}
    else:
        mock_config_entry.options = {
            CONF_DISTANCE_UNIT_OVERRIDE: CONF_DISTANCE_UNIT_OVERRIDE_DEFAULT
        }

    # Simulate how config_entry might be accessed if needed by set_distance_units
    # This part is tricky as set_distance_units directly accesses hass.config_entries
    # For now, we'll assume set_distance_units is called and it correctly sets _is_unit_metric
    # A more robust mock would involve patching hass.config_entries.async_entries

    if hass.config.units == METRIC_SYSTEM:
        sensor._is_unit_metric_default = True
        sensor._is_unit_metric = True
    else:
        sensor._is_unit_metric_default = False
        sensor._is_unit_metric = False

    if config_override == CONF_DISTANCE_UNIT_OVERRIDE_METRIC:
        sensor._is_unit_metric = True
    elif config_override == CONF_DISTANCE_UNIT_OVERRIDE_IMPERIAL:
        sensor._is_unit_metric = False

    return sensor


# Test cases for StravaSummaryStatsSensor
# Distance


@pytest.mark.parametrize(
    "activity_type, summary_type",
    [
        (CONF_ACTIVITY_TYPE_RIDE, CONF_SUMMARY_RECENT),
        (CONF_ACTIVITY_TYPE_RUN, CONF_SUMMARY_YTD),
        (CONF_ACTIVITY_TYPE_SWIM, CONF_SUMMARY_ALL),
    ],
)
@pytest.mark.parametrize(
    ("config_override", "expected_unit", "conversion_factor"),
    [
        (
            CONF_DISTANCE_UNIT_OVERRIDE_DEFAULT,
            UnitOfLength.KILOMETERS,
            1,
        ),  # Default metric
        (CONF_DISTANCE_UNIT_OVERRIDE_METRIC, UnitOfLength.KILOMETERS, 1),
        (CONF_DISTANCE_UNIT_OVERRIDE_IMPERIAL, UnitOfLength.MILES, 0.621371),
    ],
)
def test_summary_sensor_distance(
    mock_hass_metric,
    mock_hass_imperial,
    activity_type,
    summary_type,
    config_override,
    expected_unit,
    conversion_factor,
):
    """Test distance calculation and unit for StravaSummaryStatsSensor."""
    hass_to_use = (
        mock_hass_metric
        if expected_unit == UnitOfLength.KILOMETERS
        else mock_hass_imperial
    )
    if config_override == CONF_DISTANCE_UNIT_OVERRIDE_METRIC:  # Override to metric
        hass_to_use = mock_hass_metric
    elif (
        config_override == CONF_DISTANCE_UNIT_OVERRIDE_IMPERIAL
    ):  # Override to imperial
        hass_to_use = mock_hass_imperial

    sensor = create_summary_sensor(
        hass_to_use,
        activity_type,
        CONF_SENSOR_DISTANCE,
        summary_type,
        initial_data={CONF_SENSOR_DISTANCE: 10000},  # 10000 meters
        config_override=config_override,
    )

    # Manually call set_distance_units or ensure _is_unit_metric is correctly set by create_summary_sensor
    # create_summary_sensor now attempts to set this based on hass and override
    # sensor.set_distance_units() # This would require more complex mocking of config_entries

    assert sensor.native_unit_of_measurement == expected_unit
    # native_value for distance is in km (if metric) or miles (if imperial)
    # Input data is 10000m = 10km
    expected_value = (
        10.0 * conversion_factor if expected_unit == UnitOfLength.MILES else 10.0
    )
    if (
        expected_unit == UnitOfLength.KILOMETERS
        and config_override == CONF_DISTANCE_UNIT_OVERRIDE_DEFAULT
        and hass_to_use.config.units != METRIC_SYSTEM
    ):
        # If default override and HASS is imperial, it should convert to miles
        expected_value = 10.0 * 0.621371
        assert sensor.native_unit_of_measurement == UnitOfLength.MILES

    actual_value = sensor.native_value
    assert actual_value == pytest.approx(expected_value, rel=1e-2)


# Elevation
@pytest.mark.parametrize(
    "activity_type, summary_type",
    [
        (CONF_ACTIVITY_TYPE_RIDE, CONF_SUMMARY_RECENT),
        (CONF_ACTIVITY_TYPE_RUN, CONF_SUMMARY_ALL),
        # Swim doesn't have elevation summary
    ],
)
@pytest.mark.parametrize(
    ("config_override", "expected_unit", "conversion_factor"),
    [
        (CONF_DISTANCE_UNIT_OVERRIDE_DEFAULT, UnitOfLength.METERS, 1),  # Default metric
        (CONF_DISTANCE_UNIT_OVERRIDE_METRIC, UnitOfLength.METERS, 1),
        (CONF_DISTANCE_UNIT_OVERRIDE_IMPERIAL, UnitOfLength.FEET, 3.28084),
    ],
)
def test_summary_sensor_elevation(
    mock_hass_metric,
    mock_hass_imperial,
    activity_type,
    summary_type,
    config_override,
    expected_unit,
    conversion_factor,
):
    """Test elevation calculation and unit for StravaSummaryStatsSensor."""
    hass_to_use = (
        mock_hass_metric if expected_unit == UnitOfLength.METERS else mock_hass_imperial
    )
    if config_override == CONF_DISTANCE_UNIT_OVERRIDE_METRIC:
        hass_to_use = mock_hass_metric
    elif config_override == CONF_DISTANCE_UNIT_OVERRIDE_IMPERIAL:
        hass_to_use = mock_hass_imperial

    sensor = create_summary_sensor(
        hass_to_use,
        activity_type,
        CONF_SENSOR_ELEVATION,
        summary_type,
        initial_data={CONF_SENSOR_ELEVATION: 100},  # 100 meters
        config_override=config_override,
    )

    assert sensor.native_unit_of_measurement == expected_unit
    expected_value = (
        100.0 * conversion_factor if expected_unit == UnitOfLength.FEET else 100.0
    )
    if (
        expected_unit == UnitOfLength.METERS
        and config_override == CONF_DISTANCE_UNIT_OVERRIDE_DEFAULT
        and hass_to_use.config.units != METRIC_SYSTEM
    ):
        # If default override and HASS is imperial, it should convert to feet
        expected_value = 100.0 * 3.28084
        assert sensor.native_unit_of_measurement == UnitOfLength.FEET

    actual_value = sensor.native_value
    assert actual_value == pytest.approx(expected_value, rel=1e-2)


# Moving Time


@pytest.mark.parametrize(
    "activity_type, summary_type",
    [
        (CONF_ACTIVITY_TYPE_RIDE, CONF_SUMMARY_YTD),
        (CONF_ACTIVITY_TYPE_RUN, CONF_SUMMARY_RECENT),
        (CONF_ACTIVITY_TYPE_SWIM, CONF_SUMMARY_ALL),
    ],
)
def test_summary_sensor_moving_time(mock_hass_metric, activity_type, summary_type):
    """Test moving time for StravaSummaryStatsSensor."""
    sensor = create_summary_sensor(
        mock_hass_metric,
        activity_type,
        CONF_SENSOR_MOVING_TIME,
        summary_type,
        initial_data={CONF_SENSOR_MOVING_TIME: 3600},  # 3600 seconds
    )
    assert sensor.native_unit_of_measurement == UnitOfTime.SECONDS
    assert sensor.native_value == 3600


# Activity Count


@pytest.mark.parametrize(
    "activity_type, summary_type",
    [
        (CONF_ACTIVITY_TYPE_RIDE, CONF_SUMMARY_ALL),
        (CONF_ACTIVITY_TYPE_RUN, CONF_SUMMARY_YTD),
        (CONF_ACTIVITY_TYPE_SWIM, CONF_SUMMARY_RECENT),
    ],
)
def test_summary_sensor_activity_count(mock_hass_metric, activity_type, summary_type):
    """Test activity count for StravaSummaryStatsSensor."""
    sensor = create_summary_sensor(
        mock_hass_metric,
        activity_type,
        CONF_SENSOR_ACTIVITY_COUNT,
        summary_type,
        initial_data={CONF_SENSOR_ACTIVITY_COUNT: 10},
    )
    assert sensor.native_unit_of_measurement is None
    assert sensor.native_value == 10


# TODO: Test icon property for various sensor types
# TODO: Test name property
# TODO: Test capability_attributes
# TODO: Test event handlers and data updates (more complex, might need more mocking)
# TODO: Test async_setup_entry to ensure correct sensor creation (integration-like)


def create_activity_sensor(
    hass, activity_index, sensor_index, initial_data=None, config_override=None
):
    """Helper function to create and configure a StravaStatsSensor for testing."""
    sensor = StravaStatsSensor(activity_index, sensor_index)
    sensor.hass = hass
    sensor._data = initial_data if initial_data else {}

    mock_config_entry = MagicMock()
    if config_override:
        mock_config_entry.options = {CONF_DISTANCE_UNIT_OVERRIDE: config_override}
    else:
        mock_config_entry.options = {
            CONF_DISTANCE_UNIT_OVERRIDE: CONF_DISTANCE_UNIT_OVERRIDE_DEFAULT
        }

    if hass.config.units == METRIC_SYSTEM:
        sensor._is_unit_metric_default = True
        sensor._is_unit_metric = True
    else:
        sensor._is_unit_metric_default = False
        sensor._is_unit_metric = False

    if config_override == CONF_DISTANCE_UNIT_OVERRIDE_METRIC:
        sensor._is_unit_metric = True
    elif config_override == CONF_DISTANCE_UNIT_OVERRIDE_IMPERIAL:
        sensor._is_unit_metric = False

    # Call get_metric to set sensor._metric, which is needed by some properties
    sensor.get_metric()  # This will use sensor_index to set self._metric
    return sensor


# Test cases for StravaStatsSensor

# Test Distance (sensor_index maps to CONF_SENSOR_DISTANCE)


@pytest.mark.parametrize("activity_index", [0, 1])
@pytest.mark.parametrize(
    "config_override, expected_unit, conversion_factor",
    [
        (CONF_DISTANCE_UNIT_OVERRIDE_DEFAULT, UnitOfLength.KILOMETERS, 1),
        (CONF_DISTANCE_UNIT_OVERRIDE_METRIC, UnitOfLength.KILOMETERS, 1),
        (CONF_DISTANCE_UNIT_OVERRIDE_IMPERIAL, UnitOfLength.MILES, 0.621371),
    ],
)
def test_activity_sensor_distance(
    mock_hass_metric,
    mock_hass_imperial,
    activity_index,
    config_override,
    expected_unit,
    conversion_factor,
):
    """Test distance calculation and unit for StravaStatsSensor."""
    hass_to_use = (
        mock_hass_metric
        if expected_unit == UnitOfLength.KILOMETERS
        else mock_hass_imperial
    )
    if config_override == CONF_DISTANCE_UNIT_OVERRIDE_METRIC:
        hass_to_use = mock_hass_metric
    elif config_override == CONF_DISTANCE_UNIT_OVERRIDE_IMPERIAL:
        hass_to_use = mock_hass_imperial

    # Assuming sensor_index 3 maps to CONF_SENSOR_DISTANCE based on CONF_SENSOR_DEFAULT
    # CONF_SENSOR_DEFAULT = { ..., 'sensor_3': CONF_SENSOR_DISTANCE, ...}
    # sensor_index is 0-based, so sensor_index 3 -> 'sensor_3'
    sensor_index_for_distance = 3
    sensor = create_activity_sensor(
        hass_to_use,
        activity_index,
        sensor_index_for_distance,
        initial_data={CONF_SENSOR_DISTANCE: 15000},  # 15000 meters
        config_override=config_override,
    )

    assert sensor.native_unit_of_measurement == expected_unit
    expected_value = (
        15.0 * conversion_factor if expected_unit == UnitOfLength.MILES else 15.0
    )
    if (
        expected_unit == UnitOfLength.KILOMETERS
        and config_override == CONF_DISTANCE_UNIT_OVERRIDE_DEFAULT
        and hass_to_use.config.units != METRIC_SYSTEM
    ):
        expected_value = 15.0 * 0.621371
        assert sensor.native_unit_of_measurement == UnitOfLength.MILES

    actual_value = sensor.native_value
    assert actual_value == pytest.approx(expected_value, rel=1e-2)


# Test Pace (sensor_index maps to CONF_SENSOR_PACE)


@pytest.mark.parametrize("activity_index", [0])
@pytest.mark.parametrize(
    "config_override, expected_unit, expected_pace_value_str",
    [
        (
            CONF_DISTANCE_UNIT_OVERRIDE_DEFAULT,
            UNIT_PACE_MINUTES_PER_KILOMETER,
            "5:00 min/km",
        ),
        (
            CONF_DISTANCE_UNIT_OVERRIDE_METRIC,
            UNIT_PACE_MINUTES_PER_KILOMETER,
            "5:00 min/km",
        ),
        (
            CONF_DISTANCE_UNIT_OVERRIDE_IMPERIAL,
            UNIT_PACE_MINUTES_PER_MILE,
            "8:02 min/mi",
        ),
    ],
)
def test_activity_sensor_pace(
    mock_hass_metric,
    mock_hass_imperial,
    activity_index,
    config_override,
    expected_unit,
    expected_pace_value_str,
):
    """Test pace calculation and unit for StravaStatsSensor."""
    hass_to_use = mock_hass_metric
    # Determine if HASS should be imperial for this test case
    if config_override == CONF_DISTANCE_UNIT_OVERRIDE_IMPERIAL:
        hass_to_use = mock_hass_imperial
    elif (
        config_override == CONF_DISTANCE_UNIT_OVERRIDE_DEFAULT
        and hass_to_use.config.units != METRIC_SYSTEM
    ):
        # This case implies HASS default units are imperial.
        # If mock_hass_metric.config.units were US_CUSTOMARY_SYSTEM,
        # then hass_to_use should be mock_hass_imperial.
        # However, mock_hass_metric is metric by default, so this branch as-is with mock_hass_metric
        # won't make hass_to_use imperial. The expected_unit from parametrize
        # correctly anticipates min/km for this default HASS (metric) + default override scenario.
        # If a test case for (default HASS imperial + default override) is needed,
        # a new mock_hass_imperial_default would be more explicit.
        pass

    # Dynamically find sensor_index for CONF_SENSOR_PACE
    sensor_list_values = list(CONF_SENSOR_DEFAULT.values())
    try:
        sensor_index_for_pace = sensor_list_values.index(CONF_SENSOR_PACE)
    except ValueError:
        pytest.fail(
            f"CONF_SENSOR_PACE ('{CONF_SENSOR_PACE}') not found in CONF_SENSOR_DEFAULT.values()"
        )

    # Base data: 1000m in 300s = 300 s/km pace
    # For imperial: 1000m = 0.621371 miles. Pace = 300s / 0.621371 miles = 482.803 s/mile
    initial_metric_data = {
        CONF_SENSOR_DISTANCE: 1000,  # meters
        CONF_SENSOR_MOVING_TIME: 300,  # seconds
    }

    sensor = create_activity_sensor(
        hass_to_use,
        activity_index,
        sensor_index_for_pace,
        initial_data=initial_metric_data,
        config_override=config_override,
    )

    assert sensor.native_unit_of_measurement == expected_unit
    actual_value = sensor.native_value
    assert actual_value == expected_pace_value_str


# Test a simple sensor like Heart Rate (sensor_index for CONF_SENSOR_HEART_RATE_AVG)
@pytest.mark.parametrize("activity_index", [0])
def test_activity_sensor_heart_rate(mock_hass_metric, activity_index):
    """Test heart rate sensor for StravaStatsSensor."""
    # sensor_index 8 -> 'sensor_8' -> CONF_SENSOR_HEART_RATE_AVG
    sensor_index_for_hr = 8
    sensor = create_activity_sensor(
        mock_hass_metric,
        activity_index,
        sensor_index_for_hr,
        initial_data={CONF_SENSOR_HEART_RATE_AVG: 150},
    )
    assert sensor.native_unit_of_measurement == UNIT_BEATS_PER_MINUTE
    assert sensor.native_value == 150


# Test Power (sensor_index for CONF_SENSOR_POWER)


@pytest.mark.parametrize("activity_index", [0])
def test_activity_sensor_power(mock_hass_metric, activity_index):
    """Test power sensor for StravaStatsSensor."""
    # sensor_index 6 -> 'sensor_6' -> CONF_SENSOR_POWER
    sensor_index_for_power = 6
    sensor = create_activity_sensor(
        mock_hass_metric,
        activity_index,
        sensor_index_for_power,
        initial_data={CONF_SENSOR_POWER: 200},
    )
    assert sensor.native_unit_of_measurement == UnitOfPower.WATT
    assert sensor.native_value == 200


# Test Calories (sensor_index for CONF_SENSOR_CALORIES)


@pytest.mark.parametrize("activity_index", [0])
def test_activity_sensor_calories(mock_hass_metric, activity_index):
    """Test calories sensor for StravaStatsSensor."""
    # sensor_index 7 -> 'sensor_7' -> CONF_SENSOR_CALORIES
    sensor_index_for_calories = 7
    sensor = create_activity_sensor(
        mock_hass_metric,
        activity_index,
        sensor_index_for_calories,
        initial_data={CONF_SENSOR_CALORIES: 500},
    )
    assert sensor.native_unit_of_measurement == UNIT_KILO_CALORIES
    assert sensor.native_value == 500
