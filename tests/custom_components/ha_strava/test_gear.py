"""Tests for gear helper utilities."""

import pytest

from custom_components.ha_strava.gear import (
    enforce_mutual_exclusivity,
    normalize_shoe,
    resolve_shoes_for_pod,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            {
                "id": "gear123",
                "name": "Daily Trainer",
                "brand_name": "BrandA",
                "model_name": "ModelX",
                "distance": 1234.56,
                "retired": True,
                "primary": False,
            },
            {
                "id": "gear123",
                "name": "Daily Trainer",
                "brand": "BrandA",
                "model": "ModelX",
                "distance_m": 1234,
                "retired": True,
                "primary": False,
                "strava_url": "https://www.strava.com/gear/gear123",
            },
        ),
        (
            {
                "id": None,
                "name": "Tempo Shoe",
                "brand_name": "BrandB",
                "model_name": "ModelY",
                "distance": "invalid",
                "retired": False,
                "primary": True,
            },
            {
                "id": None,
                "name": "Tempo Shoe",
                "brand": "BrandB",
                "model": "ModelY",
                "distance_m": 0,
                "retired": False,
                "primary": True,
                "strava_url": None,
            },
        ),
    ],
)
def test_normalize_shoe_returns_json_safe_payload(raw, expected):
    """normalize_shoe should return a JSON-safe payload."""
    assert normalize_shoe(raw) == expected


def test_resolve_shoes_for_pod_matches_by_name():
    """resolve_shoes_for_pod should return the matching shoe dictionary."""
    shoes = [{"name": "Daily Trainer"}, {"name": "Tempo Shoe"}]
    result = resolve_shoes_for_pod("pod_1", shoes, "Tempo Shoe")
    assert result == {"name": "Tempo Shoe"}


@pytest.mark.parametrize("selection", ["Unknown", None, ""])
def test_resolve_shoes_for_pod_returns_none_when_missing(selection):
    """resolve_shoes_for_pod should return None if the selection is not found."""
    shoes = [{"name": "Daily Trainer"}]
    assert resolve_shoes_for_pod("pod_1", shoes, selection) is None


@pytest.mark.parametrize(
    ("pod1", "pod2", "expected"),
    [
        ("Daily Trainer", "Daily Trainer", ("Daily Trainer", None)),
        ("Daily Trainer", "Tempo Shoe", ("Daily Trainer", "Tempo Shoe")),
        (None, "Tempo Shoe", (None, "Tempo Shoe")),
        ("Daily Trainer", None, ("Daily Trainer", None)),
    ],
)
def test_enforce_mutual_exclusivity_handles_duplicates(pod1, pod2, expected):
    """Mutual exclusivity logic should only clear conflicting selections."""
    assert enforce_mutual_exclusivity(pod1, pod2) == expected
