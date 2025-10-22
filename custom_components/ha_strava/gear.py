"""Gear helpers for Strava Connect."""

from __future__ import annotations

from typing import Sequence, Tuple

GEAR_BASE_URL = "https://www.strava.com/gear"


def _safe_int(value: object) -> int:
    """Best-effort conversion to int, defaulting to 0."""
    if value is None:
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def normalize_shoe(raw: dict | None) -> dict:
    """Normalize a raw Strava shoe payload into a JSON-safe dictionary."""
    if not raw:
        return {
            "id": None,
            "name": None,
            "brand": None,
            "model": None,
            "distance_m": 0,
            "retired": False,
            "primary": False,
            "strava_url": None,
        }

    gear_id = raw.get("id")
    return {
        "id": gear_id,
        "name": raw.get("name"),
        "brand": raw.get("brand_name"),
        "model": raw.get("model_name"),
        "distance_m": _safe_int(raw.get("distance")),
        "retired": bool(raw.get("retired")),
        "primary": bool(raw.get("primary")),
        "strava_url": f"{GEAR_BASE_URL}/{gear_id}" if gear_id else None,
    }


def normalize_bike(raw: dict | None) -> dict:
    """Normalize a raw Strava bike payload."""
    if not raw:
        return {
            "id": None,
            "name": None,
            "brand": None,
            "model": None,
            "distance_m": 0,
            "primary": False,
            "retired": False,
            "frame_type": None,
            "strava_url": None,
        }

    gear_id = raw.get("id")
    return {
        "id": gear_id,
        "name": raw.get("name"),
        "brand": raw.get("brand_name"),
        "model": raw.get("model_name"),
        "distance_m": _safe_int(raw.get("distance")),
        "primary": bool(raw.get("primary")),
        "retired": bool(raw.get("retired")),
        "frame_type": raw.get("frame_type"),
        "strava_url": f"{GEAR_BASE_URL}/{gear_id}" if gear_id else None,
    }


def resolve_shoes_for_pod(
    pod_key: str, shoes: Sequence[dict], selected_name: str | None
) -> dict | None:
    """Resolve a shoe selection by name for the given pod."""
    if not selected_name:
        return None

    return next(
        (shoe for shoe in shoes if shoe.get("name") == selected_name),
        None,
    )


def enforce_mutual_exclusivity(
    pod1_selection: str | None, pod2_selection: str | None
) -> Tuple[str | None, str | None]:
    """Ensure two pod selections don't point to the same shoe."""
    if pod1_selection and pod2_selection and pod1_selection == pod2_selection:
        return pod1_selection, None

    return pod1_selection, pod2_selection
