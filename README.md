[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/CraigBell/strava_connect?color=41BDF5&style=for-the-badge)](https://github.com/CraigBell/strava_connect/releases/latest)
[![Integration Usage](https://img.shields.io/badge/dynamic/json?color=41BDF5&style=for-the-badge&logo=home-assistant&label=usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.ha_strava.total)](https://analytics.home-assistant.io/)
[![Maintained by Craig Bell](https://img.shields.io/badge/Maintained%20by-Craig%20Bell-41BDF5.svg?style=for-the-badge)](https://thepossibilitypartnership.com/)

# Strava Connect for Home Assistant

> Strava Connect – A Home Assistant integration for Strava data (unofficial) maintained by Craig Bell.

Strava Connect keeps your Home Assistant instance in sync with Strava: it streams recent activities, detailed stats, athlete gear history, a dynamic shoes catalog, and optional Stryd pod ↔ shoe mappings using Home Assistant helpers—all delivered through webhook-driven updates that respect Strava rate limits.

## Features

- **Recent activity sensors** with rich metrics, device details, location data, and optional photo carousel camera.
- **Summary statistics** for recent (4-week), year-to-date, and all-time totals across multiple sport types.
- **Gear awareness** including a live shoes catalog sensor, Strava gear metadata, and friendly Strava gear links.
- **Stryd companion tooling**: map Bluetooth pods to shoes via `input_select` helpers and surface the resolved pairings as catalog attributes.
- **Webhook-first architecture** that avoids polling and stays within Strava API quotas.

## MVP Features

- Dynamic **Shoes Catalog** sensor with normalized gear metadata and pod helper attributes.
- Two optional `input_select` helpers for maintaining Stryd pod ↔ shoe assignments without conflicts.
- New Home Assistant service `ha_strava.set_activity_gear` to update historical activities with the right shoe.
- Enforced Strava OAuth scopes with automatic reauthorization prompts when permissions shrink.

## Installation (HACS)

1. Make sure your Home Assistant instance is reachable from the internet (required for Strava webhooks).
2. Add this repository (`CraigBell/strava_connect`) as a custom integration in [HACS](https://hacs.xyz/).
3. Download **Strava Connect**, restart Home Assistant, and add the integration from **Settings → Devices & Services**.
4. Supply your Strava API `Client ID` and `Client Secret`, then approve the authorization prompt.

> **Note:** The integration domain remains `ha_strava`, so existing entity IDs and automations continue to work.

## What's New

- **v0.14** – Ensures the Strava auth flow explicitly requests the full gear read/write scope set so shoes and activity updates work immediately after install.

## Documentation & Support

- Full configuration details, options, and contribution guidelines are available in the [project wiki](https://github.com/CraigBell/strava_connect/wiki).
- Issues and feature requests: [GitHub Issues](https://github.com/CraigBell/strava_connect/issues).
- Community discussion: join the [Home Assistant forums](https://community.home-assistant.io/) and search for _Strava Connect_.

## Service: `ha_strava.set_activity_gear`

Assign the correct shoe to a Strava activity directly from Home Assistant. Provide either a `shoe_id` or a `shoe_name` that exists in the shoes catalog sensor.

```yaml
service: ha_strava.set_activity_gear
data:
  activity_id: "1234567890"
  shoe_name: "Nike Pegasus 40"
```

On success the integration fires an event `ha_strava.activity_gear_set` which you can use for automations.

## Required Strava Scopes

Authorize with the full scope string to unlock gear read/write support:

```
read,read_all,profile:read_all,activity:read_all,activity:write
```

If any scope is missing, the integration blocks gear writes and prompts for reauthorization via the Home Assistant UI.

## Troubleshooting

- **Missing shoes or bikes?** Reauthorize with the `profile:read_all` scope.
- **403 when setting gear?** Ensure the app has `activity:write`; reauthorize if necessary.
- **429 rate limit warnings?** Strava quota was reached—wait a few minutes before retrying.
- **Service cannot find your shoe name?** Confirm the shoe exists in the Shoes Catalog sensor and that the name matches exactly (case sensitive).

## Topics

home-assistant · strava · integration · fitness · running · cycling

<img src="https://raw.githubusercontent.com/CraigBell/strava_connect/main/img/api_logo_pwrdBy_strava_stack_light.png" width="240">
