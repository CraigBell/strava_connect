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

## Installation (HACS)

1. Make sure your Home Assistant instance is reachable from the internet (required for Strava webhooks).
2. Add this repository (`CraigBell/strava_connect`) as a custom integration in [HACS](https://hacs.xyz/).
3. Download **Strava Connect**, restart Home Assistant, and add the integration from **Settings → Devices & Services**.
4. Supply your Strava API `Client ID` and `Client Secret`, then approve the authorization prompt.

> **Note:** The integration domain remains `ha_strava`, so existing entity IDs and automations continue to work.

## What's New

- **v0.12** – Introduced the Stryd pod ↔ shoe helper workflow and the new dynamic shoes catalog sensor, making gear management first class inside Home Assistant.

## Documentation & Support

- Full configuration details, options, and contribution guidelines are available in the [project wiki](https://github.com/CraigBell/strava_connect/wiki).
- Issues and feature requests: [GitHub Issues](https://github.com/CraigBell/strava_connect/issues).
- Community discussion: join the [Home Assistant forums](https://community.home-assistant.io/) and search for _Strava Connect_.

## Topics

home-assistant · strava · integration · fitness · running · cycling

<img src="https://raw.githubusercontent.com/CraigBell/strava_connect/main/img/api_logo_pwrdBy_strava_stack_light.png" width="240">
