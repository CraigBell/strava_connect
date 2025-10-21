"""Utilities for working with Strava gear metadata."""

from __future__ import annotations

from typing import Iterable, Mapping

from .const import STRAVA_GEAR_BASE_URL


def normalize_shoe(gear: Mapping[str, object]) -> dict:
    """Return a JSON-serialisable representation of a Strava shoe entry."""
    raw_id = gear.get("id")
    shoe_id = str(raw_id).strip() if raw_id is not None else None
    raw_distance = gear.get("distance") or 0
    try:
        distance_value = float(raw_distance)
    except (TypeError, ValueError):
        distance_value = 0
    distance = int(distance_value)
    return {
        "id": shoe_id or None,
        "name": gear.get("name"),
        "brand": gear.get("brand_name"),
        "model": gear.get("model_name"),
        "distance_m": distance,
        "retired": bool(gear.get("retired", False)),
        "primary": bool(gear.get("primary", False)),
        "strava_url": f"{STRAVA_GEAR_BASE_URL}{shoe_id}" if shoe_id else None,
    }


def resolve_shoes_for_pod(
    pod_name: str, shoes: Iterable[Mapping[str, object]], selected: str | None
) -> dict | None:
    """Return the matching shoe dictionary by friendly name, if available."""
    if not selected:
        return None

    for shoe in shoes:
        if shoe.get("name") == selected:
            return dict(shoe)
    return None


def enforce_mutual_exclusivity(
    pod1: str | None, pod2: str | None
) -> tuple[str | None, str | None]:
    """Ensure two pod selections do not reference the same shoe."""
    if pod1 and pod2 and pod1 == pod2:
        return pod1, None
    return pod1, pod2
