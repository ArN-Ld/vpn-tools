#!/usr/bin/env python3
"""Backward-compatible CLI entrypoint for Mullvad speed tests."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vpn_tools.mullvad_speed_test import *  # noqa: F401,F403


if __name__ == "__main__":
    main()
