---
description: Code quality standards and style guidelines for the ha_strava project
globs: ["custom_components/ha_strava/**/*.py", "tests/**/*.py"]
alwaysApply: false
---

# Code Quality Standards

This file defines the code quality standards and style guidelines for the ha_strava project, based on the existing setup.cfg configuration and project patterns.

## Code Formatting

### Black Configuration

- **Line Length**: 120 characters maximum
- **Profile**: Black formatting standard
- **Exclusions**: E203, F541 (compatible with Black)

### Import Organization

- Use `isort` with Black profile
- Group imports: standard library, third-party, local imports
- Sort imports alphabetically within groups

```python
# Standard library imports
import json
import logging
from datetime import datetime as dt
from http import HTTPStatus

# Third-party imports
import aiohttp
import voluptuous as vol
from homeassistant.components.sensor import SensorEntity

# Local imports
from .const import DOMAIN, CONF_SENSOR_DISTANCE
from .coordinator import StravaDataUpdateCoordinator
```

## Type Hints

### Required Type Hints

- All function parameters
- All return types
- Class attributes where beneficial
- Use `from __future__ import annotations` for forward references

```python
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

async def fetch_activities(
    self,
    athlete_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Fetch activities from Strava API."""
    pass

@property
def device_info(self) -> Optional[Dict[str, Any]]:
    """Return device information."""
    pass
```

## Logging Standards

### Logger Setup

```python
import logging

_LOGGER = logging.getLogger(__name__)
```

### Log Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General information about program execution
- **WARNING**: Something unexpected happened but the program is still working
- **ERROR**: A serious problem occurred

### Logging Patterns

```python
# Debug logging for detailed flow
_LOGGER.debug("Fetching activities for athlete %s", athlete_id)

# Info logging for important events
_LOGGER.info("Successfully updated %d activities", len(activities))

# Warning logging for recoverable issues
_LOGGER.warning("Webhook received for unknown user: %s", owner_id)

# Error logging for serious issues
_LOGGER.error("Error communicating with API: %s", err)
```

### Security Considerations

- Never log sensitive data (tokens, API keys, personal information)
- Use parameterized logging to avoid string formatting issues
- Log only necessary information for debugging

## Error Handling

### Exception Handling Patterns

```python
try:
    response = await self.oauth_session.async_request(method="GET", url=url)
    response.raise_for_status()
    data = await response.json()
except aiohttp.ClientError as err:
    _LOGGER.error("API request failed: %s", err)
    raise UpdateFailed(f"Error communicating with API: {err}") from err
except json.JSONDecodeError as err:
    _LOGGER.error("Invalid JSON response: %s", err)
    raise UpdateFailed("Invalid response format") from err
```

### Custom Exceptions

```python
class StravaAPIError(Exception):
    """Base exception for Strava API errors."""
    pass

class StravaAuthenticationError(StravaAPIError):
    """Authentication failed with Strava API."""
    pass
```

## Async/Await Patterns

### Proper Async Usage

```python
# Use async/await consistently
async def async_update_data(self) -> Dict[str, Any]:
    """Update data from API."""
    try:
        await self.oauth_session.async_ensure_token_valid()
        activities = await self._fetch_activities()
        return {"activities": activities}
    except Exception as err:
        raise UpdateFailed(f"Update failed: {err}") from err

# Use async context managers
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        data = await response.json()
```

## Function and Method Design

### Method Naming

- Use descriptive, self-documenting method names
- Prefix private methods with underscore
- Use async prefix for async methods

```python
# Good method names
async def async_fetch_activities(self) -> List[Dict[str, Any]]:
    """Fetch activities from Strava API."""
    pass

def _process_activity_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process raw activity data into sensor format."""
    pass

@property
def device_info(self) -> Dict[str, Any]:
    """Return device information for entity registry."""
    pass
```

### Method Documentation

- Use docstrings for all public methods
- Include parameter descriptions
- Include return value descriptions
- Include any exceptions that might be raised

```python
async def async_fetch_activities(
    self,
    athlete_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Fetch activities from Strava API for a specific athlete.

    Args:
        athlete_id: The Strava athlete ID
        limit: Maximum number of activities to fetch (default: 10)

    Returns:
        List of activity dictionaries

    Raises:
        UpdateFailed: If API request fails
        StravaAuthenticationError: If authentication fails
    """
    pass
```

## Constants and Configuration

### Constants Management

- Define all constants in `const.py`
- Use descriptive constant names
- Group related constants together
- Use UPPER_CASE for constants

```python
# Domain and basic configuration
DOMAIN = "ha_strava"
CONFIG_ENTRY_TITLE = "Strava"

# API endpoints
STRAVA_ACTIVITY_BASE_URL = "https://www.strava.com/activities/"
STRAVA_ACTHLETE_BASE_URL = "https://www.strava.com/dashboard"

# Configuration keys
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_PHOTOS = "conf_photos"

# Sensor definitions
CONF_SENSORS = {
    CONF_SENSOR_DISTANCE: {"icon": "mdi:map-marker-distance"},
    CONF_SENSOR_ELEVATION: {"icon": "mdi:elevation-rise"},
}
```

## Pylint Configuration

### Disabled Rules

- `format` - Handled by Black
- `logging-fstring-interpolation` - Use parameterized logging
- `f-string-without-interpolation` - Use regular strings when no interpolation

### Enabled Rules

- `use-symbolic-message-instead` - Use symbolic message names

### Line Length

- Maximum 120 characters (consistent with Black)

## Testing Standards

### Test File Organization

- Mirror the source code structure in tests
- Use descriptive test names
- Group related tests in classes

```python
class TestStravaCoordinator:
    """Test cases for StravaDataUpdateCoordinator."""

    async def test_fetch_activities_success(self):
        """Test successful activity fetching."""
        pass

    async def test_fetch_activities_api_error(self):
        """Test API error handling during activity fetching."""
        pass
```

### Test Naming

- Use descriptive test method names
- Include the scenario being tested
- Use `test_` prefix for all test methods

## Performance Considerations

### Efficient Data Processing

- Use list comprehensions where appropriate
- Avoid unnecessary API calls
- Cache frequently accessed data
- Use appropriate data structures

### Memory Management

- Clean up resources properly
- Use context managers for file operations
- Avoid storing large objects in memory unnecessarily

## Security Best Practices

### Input Validation

- Validate all external inputs
- Sanitize data before processing
- Use proper type checking

### API Security

- Never log sensitive information
- Use secure HTTP methods
- Implement proper error handling for authentication failures
- Validate API responses before processing
