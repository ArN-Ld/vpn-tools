#!/usr/bin/env python3

"""
Database of correct coordinates for Mullvad server locations.
This is used instead of relying on potentially incorrect coordinates from Mullvad's output.
"""

import json
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _load_coordinates() -> Dict[str, Tuple[float, float]]:
    """Load coordinates from a JSON file with an in-memory cache."""

    data_dir = Path(__file__).with_name("data")
    data_file = data_dir / "coordinates.json"
    if not data_file.exists():
        # Fallback to an example file if provided
        data_file = data_dir / "coordinates.example.json"

    if data_file.exists():
        try:
            with data_file.open() as f:
                data = json.load(f)
            return {key: tuple(value) for key, value in data.items()}
        except (json.JSONDecodeError, OSError) as e:
            logging.error("Failed to load coordinates from %s: %s", data_file, e)
            pass

    return {}


# Cache coordinates at import time
COORDINATES: Dict[str, Tuple[float, float]] = _load_coordinates()


def _normalize_location(value: str) -> str:
    """Normalize location strings for case-insensitive matching."""
    compact = " ".join(value.strip().split())
    return re.sub(r"\s*,\s*", ", ", compact)


def _build_location_index() -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """Create indexes for full location and city-only lookups."""
    full_location_index: Dict[str, str] = {}
    city_index: Dict[str, List[str]] = defaultdict(list)

    for canonical_name in COORDINATES:
        normalized_key = _normalize_location(canonical_name).lower()
        full_location_index[normalized_key] = canonical_name

        city_name = canonical_name.split(",", 1)[0].strip().lower()
        city_index[city_name].append(canonical_name)

    for city_name in city_index:
        city_index[city_name].sort()

    return full_location_index, dict(city_index)


FULL_LOCATION_INDEX, CITY_INDEX = _build_location_index()


def get_coordinates(city: str, country: str) -> Tuple[float, float]:
    """
    Get the correct coordinates for a given city and country.

    Args:
        city: The city name
        country: The country name

    Returns:
        A tuple of (latitude, longitude)
    """
    location_key = f"{city}, {country}"
    return COORDINATES.get(location_key, (0.0, 0.0))


def resolve_location_input(location: str) -> Tuple[Optional[str], Optional[Tuple[float, float]], List[str]]:
    """Resolve user input to a canonical Mullvad location and coordinates.

    Supports:
    - Full location input (`City, Country`) case-insensitively
    - City-only input (`City`) case-insensitively

    Returns:
        (canonical_location, coords, matches)
    """
    normalized_input = _normalize_location(location)
    if not normalized_input:
        return None, None, []

    exact_match = FULL_LOCATION_INDEX.get(normalized_input.lower())
    if exact_match:
        return exact_match, COORDINATES[exact_match], [exact_match]

    city_token = normalized_input.split(",", 1)[0].strip().lower()
    city_matches = CITY_INDEX.get(city_token, [])
    if city_matches:
        chosen_location = city_matches[0]
        return chosen_location, COORDINATES[chosen_location], city_matches

    return None, None, []

