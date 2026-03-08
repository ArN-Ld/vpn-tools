#!/usr/bin/env python3

"""
Database of correct coordinates for Mullvad server locations.
This is used instead of relying on potentially incorrect coordinates from Mullvad's output.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Tuple


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

