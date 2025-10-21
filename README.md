[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/craibo/ha_strava?color=41BDF5&style=for-the-badge)](https://github.com/craibo/ha_strava/releases/latest)
[![Integration Usage](https://img.shields.io/badge/dynamic/json?color=41BDF5&style=for-the-badge&logo=home-assistant&label=usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.ha_strava.total)](https://analytics.home-assistant.io/)

# Strava Connect for Home Assistant

Strava Connect keeps your Home Assistant instance in sync with Strava: it streams recent activities, detailed stats, athlete gear history, a dynamic shoes catalog, and optional Stryd pod ↔ shoe mappings using Home Assistant helpers—all delivered through webhook-driven updates that respect Strava rate limits.

## Features

- **Recent activity sensors** with rich metrics, device details, location data, and optional photo carousel camera.
- **Summary statistics** for recent (4-week), year-to-date, and all-time totals across multiple sport types.
- **Gear awareness** including a live shoes catalog sensor, Strava gear metadata, and friendly Strava gear links.
- **Stryd companion tooling**: map Bluetooth pods to shoes via `input_select` helpers and surface the resolved pairings as catalog attributes.
- **Webhook-first architecture** that avoids polling and stays within Strava API quotas.

## Installation (HACS)

1. Make sure your Home Assistant instance is reachable from the internet (required for Strava webhooks).
2. Add this repository (`craibo/ha_strava`) as a custom integration in [HACS](https://hacs.xyz/).
3. Download **Strava Connect**, restart Home Assistant, and add the integration from **Settings → Devices & Services**.
4. Supply your Strava API `Client ID` and `Client Secret`, then approve the authorization prompt.

> **Note:** The integration domain remains `ha_strava`, so existing entity IDs and automations continue to work.

## What's New

- **v0.12** – Introduced the Stryd pod ↔ shoe helper workflow and the new dynamic shoes catalog sensor, making gear management first class inside Home Assistant.

## Documentation & Support

- Full configuration details, options, and contribution guidelines are available in the [repository wiki](https://github.com/craibo/ha_strava/wiki).
- Issues and feature requests: [GitHub Issues](https://github.com/craibo/ha_strava/issues).
- Community discussion: join the [Home Assistant forums](https://community.home-assistant.io/) and search for _Strava Connect_.

<img src="https://raw.githubusercontent.com/craibo/ha_strava/main/img/api_logo_pwrdBy_strava_stack_light.png" width="240">
