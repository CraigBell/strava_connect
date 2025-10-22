[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

# Strava Connect

Strava Connect links your Strava account with Home Assistant so you can monitor fresh activities, long-term stats, photo highlights, and a live gear catalog—complete with Stryd pod ↔ shoe mapping—without ever polling the API.

## Highlights

- Recent activity sensors with distance, duration, heart-rate, and device data for every tracked sport.
- Summary statistics (recent, year-to-date, all-time) for run, ride, swim, and more.
- Dynamic shoes catalog sensor exposing gear distance, retired status, and Strava gear links.
- Optional Stryd pod helpers that resolve each pod to the shoe you select via `input_select`.
- Webhook-driven updates to keep data current while respecting Strava limits.

## Installation

Install through [HACS](https://hacs.xyz/) by adding `CraigBell/strava_connect`, download the integration, restart Home Assistant, and configure it from **Settings → Devices & Services** using your Strava API credentials. The integration domain remains `ha_strava`.

## Release Spotlight

- **v0.13** – Delivers athlete gear sync, the `ha_strava.set_activity_gear` write service, and guardrails for OAuth scopes and rate limits.
