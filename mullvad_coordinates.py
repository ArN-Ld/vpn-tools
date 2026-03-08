#!/usr/bin/env python3
"""Backward-compatible import bridge for coordinate lookups."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vpn_tools.mullvad_coordinates import *  # noqa: F401,F403
