"""Tests for gear helper utilities."""

from custom_components.ha_strava.gear import (
    enforce_mutual_exclusivity,
    normalize_shoe,
    resolve_shoes_for_pod,
)


def test_normalize_shoe_returns_json_safe_payload():
    """normalize_shoe should retain required fields and format distance."""
    raw = {
        "id": "gear123",
        "name": "Daily Trainer",
        "brand_name": "BrandA",
        "model_name": "ModelX",
        "distance": 1234.56,
        "retired": True,
        "primary": False,
    }
    normalized = normalize_shoe(raw)

    assert normalized == {
        "id": "gear123",
        "name": "Daily Trainer",
        "brand": "BrandA",
        "model": "ModelX",
        "distance_m": 1234,
        "retired": True,
        "primary": False,
        "strava_url": "https://www.strava.com/gear/gear123",
    }


def test_resolve_shoes_for_pod_matches_by_name():
    """resolve_shoes_for_pod should return the matching shoe dictionary."""
    shoes = [{"name": "Daily Trainer"}, {"name": "Tempo Shoe"}]
    result = resolve_shoes_for_pod("pod_1", shoes, "Tempo Shoe")
    assert result == {"name": "Tempo Shoe"}


def test_resolve_shoes_for_pod_returns_none_when_missing():
    """resolve_shoes_for_pod should return None if the selection is not found."""
    shoes = [{"name": "Daily Trainer"}]
    assert resolve_shoes_for_pod("pod_1", shoes, "Unknown") is None
    assert resolve_shoes_for_pod("pod_1", shoes, None) is None


def test_enforce_mutual_exclusivity_handles_duplicates():
    """Mutual exclusivity should clear the second pod when both selections match."""
    pod1, pod2 = enforce_mutual_exclusivity("Daily Trainer", "Daily Trainer")
    assert pod1 == "Daily Trainer"
    assert pod2 is None

    pod1, pod2 = enforce_mutual_exclusivity("Daily Trainer", "Tempo Shoe")
    assert pod1 == "Daily Trainer"
    assert pod2 == "Tempo Shoe"
