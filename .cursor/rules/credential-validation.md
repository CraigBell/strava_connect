---
description: Credential validation and uniqueness enforcement for multi-user Strava integration
globs:
  [
    "custom_components/ha_strava/config_flow.py",
    "custom_components/ha_strava/__init__.py",
  ]
alwaysApply: false
---

# Credential Validation and Uniqueness

This file defines patterns for ensuring each Strava user has unique credentials and proper validation in the ha_strava Home Assistant custom component.

## Core Requirements

### Unique Credentials Per User

- Each user MUST have their own unique Strava app credentials (client_id, client_secret)
- No credential sharing between users is allowed
- Credential uniqueness must be validated during setup
- Each user's OAuth2 session is completely isolated

## Credential Validation Patterns

### Config Flow Validation

```python
async def async_step_user(self, user_input=None):
    """Validate that Strava app credentials are unique across all users."""
    data_schema = {
        vol.Required(CONF_CLIENT_ID): str,
        vol.Required(CONF_CLIENT_SECRET): str,
        vol.Required(CONF_PHOTOS, default=self._import_photos_from_strava): bool,
    }

    if user_input is not None:
        client_id = user_input[CONF_CLIENT_ID]

        # Validate credential uniqueness
        validation_error = await self._validate_credential_uniqueness(client_id)
        if validation_error:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(data_schema),
                errors={"base": validation_error}
            )

        # Proceed with OAuth2 flow for unique credentials
        self._import_photos_from_strava = user_input[CONF_PHOTOS]
        return await self._setup_oauth_implementation(user_input)

    return self.async_show_form(step_id="user", data_schema=vol.Schema(data_schema))

async def _validate_credential_uniqueness(self, client_id: str) -> str | None:
    """Validate that client_id is unique across all existing users."""
    # Check if these credentials are already in use by another user
    for entry in self.hass.config_entries.async_entries(DOMAIN):
        if entry.data.get(CONF_CLIENT_ID) == client_id:
            return "credentials_already_used"

    # Additional validation: check if client_id format is valid
    if not self._is_valid_client_id_format(client_id):
        return "invalid_client_id_format"

    return None

def _is_valid_client_id_format(self, client_id: str) -> bool:
    """Validate client_id format (Strava client IDs are typically numeric)."""
    try:
        int(client_id)
        return len(client_id) >= 4  # Minimum reasonable length
    except ValueError:
        return False
```

### OAuth2 Implementation Setup

```python
async def _setup_oauth_implementation(self, user_input: dict):
    """Set up OAuth2 implementation for unique credentials."""
    try:
        # Register the OAuth2 implementation with unique credentials
        config_entry_oauth2_flow.async_register_implementation(
            self.hass,
            DOMAIN,
            config_entry_oauth2_flow.LocalOAuth2Implementation(
                self.hass,
                DOMAIN,
                user_input[CONF_CLIENT_ID],  # Unique per user
                user_input[CONF_CLIENT_SECRET],  # Unique per user
                OAUTH2_AUTHORIZE,
                OAUTH2_TOKEN,
            ),
        )

        # Log successful credential registration
        _LOGGER.info(f"Registered OAuth2 implementation for client_id: {user_input[CONF_CLIENT_ID]}")

        return await self.async_step_pick_implementation()

    except Exception as err:
        _LOGGER.error(f"Failed to register OAuth2 implementation: {err}")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(data_schema),
            errors={"base": "oauth_setup_failed"}
        )
```

### Entry Creation with Credential Validation

```python
async def async_oauth_create_entry(self, data: dict) -> dict:
    """Create an entry with validated unique credentials."""
    # Double-check credential uniqueness before creating entry
    client_id = self.flow_impl.client_id

    for entry in self.hass.config_entries.async_entries(DOMAIN):
        if entry.data.get(CONF_CLIENT_ID) == client_id:
            _LOGGER.error(f"Credential conflict detected for client_id: {client_id}")
            return self.async_abort(reason="credentials_already_used")

    # Fetch athlete info to get unique user identifier
    headers = {
        "Authorization": f"Bearer {data['token']['access_token']}",
    }
    async with aiohttp.ClientSession() as session, session.get(
        "https://www.strava.com/api/v3/athlete", headers=headers
    ) as response:
        if response.status != 200:
            return self.async_abort(reason="cannot_connect")
        athlete_info = await response.json()

    athlete_id = athlete_info["id"]
    await self.async_set_unique_id(str(athlete_id))
    self._abort_if_unique_id_configured()

    title = f"Strava: {athlete_info.get('firstname', '')} {athlete_info.get('lastname', '')}".strip()

    # Store unique credentials in entry data
    data[CONF_CALLBACK_URL] = f"{get_url(self.hass, allow_internal=False, allow_ip=False)}/api/strava/webhook"
    data[CONF_CLIENT_ID] = self.flow_impl.client_id  # Unique per user
    data[CONF_CLIENT_SECRET] = self.flow_impl.client_secret  # Unique per user
    data[CONF_PHOTOS] = self._import_photos_from_strava

    _LOGGER.info(f"Created Strava integration for user {athlete_id} with client_id: {client_id}")
    return self.async_create_entry(title=title, data=data)
```

## Error Handling and User Feedback

### Error Messages for Credential Issues

```python
# Translation strings for credential validation errors
TRANSLATION_STRINGS = {
    "credentials_already_used": "These Strava app credentials are already in use by another user. Each user must have their own unique Strava app credentials.",
    "invalid_client_id_format": "Invalid Strava client ID format. Please check your Strava app credentials.",
    "oauth_setup_failed": "Failed to set up OAuth2 authentication. Please check your credentials and try again.",
    "credential_conflict_detected": "A credential conflict was detected during setup. Please use different Strava app credentials.",
}
```

### Validation Error Handling

```python
async def _handle_credential_validation_error(self, error_type: str) -> dict:
    """Handle credential validation errors with appropriate user feedback."""
    error_messages = {
        "credentials_already_used": {
            "title": "Credentials Already in Use",
            "description": "These Strava app credentials are already configured for another user. Each user must have their own unique Strava app credentials.",
            "suggestion": "Please create a new Strava app or use different credentials for this user."
        },
        "invalid_client_id_format": {
            "title": "Invalid Client ID",
            "description": "The provided Strava client ID format is invalid.",
            "suggestion": "Please check your Strava app credentials and ensure the client ID is correct."
        },
        "oauth_setup_failed": {
            "title": "OAuth Setup Failed",
            "description": "Failed to set up OAuth2 authentication with the provided credentials.",
            "suggestion": "Please verify your Strava app credentials and try again."
        }
    }

    error_info = error_messages.get(error_type, {
        "title": "Validation Error",
        "description": "An error occurred during credential validation.",
        "suggestion": "Please check your credentials and try again."
    })

    _LOGGER.warning(f"Credential validation failed: {error_info['description']}")

    return self.async_show_form(
        step_id="user",
        data_schema=vol.Schema(self._get_credential_schema()),
        errors={"base": error_type},
        description_placeholders=error_info
    )
```

## Webhook Registration with Unique Credentials

### Per-User Webhook Registration

```python
async def renew_webhook_subscription(hass: HomeAssistant, entry: ConfigEntry):
    """Register webhook subscription for user with unique credentials."""
    try:
        ha_host = get_url(hass, allow_internal=False, allow_ip=False)
    except NoURLAvailableError:
        _LOGGER.error("Home Assistant instance does not have a public URL")
        return

    callback_url = f"{ha_host}/api/strava/webhook"
    websession = async_get_clientsession(hass, verify_ssl=False)

    # Use user-specific credentials for webhook management
    client_id = entry.data[CONF_CLIENT_ID]
    client_secret = entry.data[CONF_CLIENT_SECRET]

    _LOGGER.debug(f"Managing webhook subscription for user {entry.unique_id} with client_id: {client_id}")

    try:
        # Get existing subscriptions for this user's app only
        async with websession.get(
            WEBHOOK_SUBSCRIPTION_URL,
            params={
                "client_id": client_id,  # User-specific
                "client_secret": client_secret,  # User-specific
            },
        ) as response:
            response.raise_for_status()
            subscriptions = await response.json()

        # Clean up old subscriptions for this user's app
        for sub in subscriptions:
            if sub["callback_url"] != callback_url:
                _LOGGER.debug(f"Deleting outdated webhook subscription for user {entry.unique_id}: {sub['id']}")
                await self._delete_webhook_subscription(websession, sub["id"], client_id, client_secret)

        # Create new subscription if needed
        if not any(sub["callback_url"] == callback_url for sub in subscriptions):
            await self._create_webhook_subscription(websession, entry, callback_url)
            _LOGGER.info(f"Created webhook subscription for user {entry.unique_id}")

    except aiohttp.ClientError as err:
        _LOGGER.error(f"Error managing webhook subscriptions for user {entry.unique_id}: {err}")
```

## Testing Credential Validation

### Test Credential Uniqueness

```python
async def test_credential_uniqueness_validation(hass: HomeAssistant):
    """Test that duplicate credentials are properly rejected."""
    # Create first user with credentials
    user1_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="12345",
        data={"client_id": "shared_client", "client_secret": "shared_secret"}
    )
    user1_entry.add_to_hass(hass)

    # Try to create second user with same credentials
    config_flow = OAuth2FlowHandler()
    config_flow.hass = hass

    result = await config_flow.async_step_user({
        "client_id": "shared_client",  # Same as user1
        "client_secret": "shared_secret"  # Same as user1
    })

    # Should show error about credentials already in use
    assert result["type"] == "form"
    assert "credentials_already_used" in result["errors"]["base"]

async def test_valid_credential_format(hass: HomeAssistant):
    """Test that valid credential formats are accepted."""
    config_flow = OAuth2FlowHandler()
    config_flow.hass = hass

    # Test valid numeric client_id
    result = await config_flow.async_step_user({
        "client_id": "12345",  # Valid format
        "client_secret": "valid_secret"
    })

    # Should proceed to OAuth2 flow
    assert result["type"] == "external"

async def test_invalid_credential_format(hass: HomeAssistant):
    """Test that invalid credential formats are rejected."""
    config_flow = OAuth2FlowHandler()
    config_flow.hass = hass

    # Test invalid client_id format
    result = await config_flow.async_step_user({
        "client_id": "abc",  # Invalid format (too short, non-numeric)
        "client_secret": "valid_secret"
    })

    # Should show format error
    assert result["type"] == "form"
    assert "invalid_client_id_format" in result["errors"]["base"]
```

## Security Considerations

### Credential Storage Security

```python
# Credentials are stored securely in Home Assistant's config entry system
# No logging of sensitive credential data
_LOGGER.info(f"Registered OAuth2 implementation for client_id: {client_id}")  # OK - client_id is not sensitive
_LOGGER.error(f"OAuth setup failed for client_id: {client_id}")  # OK - client_id is not sensitive

# NEVER log client_secret
# _LOGGER.debug(f"Using client_secret: {client_secret}")  # NEVER DO THIS
```

### Credential Validation Security

```python
async def _validate_credential_uniqueness(self, client_id: str) -> str | None:
    """Validate credential uniqueness securely."""
    # Sanitize input to prevent injection attacks
    if not client_id or len(client_id) > 50:  # Reasonable length limit
        return "invalid_client_id_format"

    # Check uniqueness without exposing other users' data
    for entry in self.hass.config_entries.async_entries(DOMAIN):
        if entry.data.get(CONF_CLIENT_ID) == client_id:
            _LOGGER.warning(f"Duplicate client_id detected: {client_id}")
            return "credentials_already_used"

    return None
```

## Migration and Upgrade Considerations

### Handling Existing Shared Credentials

```python
async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate existing entries to enforce credential uniqueness."""
    version = config_entry.version

    if version == 1:
        # Check if this entry has shared credentials
        client_id = config_entry.data.get(CONF_CLIENT_ID)

        # Find other entries with same credentials
        duplicate_entries = [
            entry for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.entry_id != config_entry.entry_id
            and entry.data.get(CONF_CLIENT_ID) == client_id
        ]

        if duplicate_entries:
            _LOGGER.warning(f"Found {len(duplicate_entries)} entries with shared credentials for client_id: {client_id}")
            # Mark entry as requiring credential update
            new_data = {**config_entry.data}
            new_data["_requires_credential_update"] = True

            return {"version": 2, "data": new_data}

    return None
```

## Best Practices

### Credential Management

1. **Always validate uniqueness** before creating new entries
2. **Never log sensitive credential data** (client_secret)
3. **Use secure storage** provided by Home Assistant config entries
4. **Provide clear error messages** to users about credential requirements
5. **Test credential validation** thoroughly with various scenarios

### User Experience

1. **Clear messaging** about the need for unique credentials
2. **Helpful error messages** with suggestions for resolution
3. **Validation feedback** during the setup process
4. **Documentation** about creating Strava apps for multiple users

### Security

1. **Input validation** to prevent injection attacks
2. **Rate limiting** on credential validation attempts
3. **Secure credential storage** using Home Assistant's built-in mechanisms
4. **Audit logging** for credential management actions
