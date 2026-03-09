# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Changed
- `format_mtr_results()` in `display_manager.py` now shows "Ping" or "MTR" dynamically based on hop count (`hops == 0` → ping fallback path), and omits the hops field when zero.

### Fixed
- Corrected `README.md` mtr diagnosis: replaced inaccurate "macOS Tahoe kernel regression" language with the actual root cause (Homebrew `mtr-packet` SUID bit owned by installing user, not root) and the exact fix commands.

---

## [1.1.0] - 2026-03-09
### Added
- Added `requirements-dev.txt` to separate development dependencies from runtime dependencies.
- Added `MAINTENANCE.md` and `PROJECT_AUDIT.md` to formalize maintenance and technical review.
- Added GitHub Actions CI workflow in `.github/workflows/ci.yml`.
- Added regression tests for non-interactive execution and geocode fallback.
- Organized project structure with `src/vpn_tools/`, `docs/`, `tests/unit/` directories.
- Created `runtime/` directory for all logs, database, and cache files.
- Added Dependabot configuration (`.github/dependabot.yml`) for automated dependency updates.
- Added security policy (`SECURITY.md`) with vulnerability reporting guidelines and security best practices.
- Added fork-safe upstream review routine in `docs/MAINTENANCE.md` and helper script `scripts/upstream_review.sh`.
- Added repository governance templates: `.github/CODEOWNERS`, issue templates, and PR template.
- Added case-insensitive city-only location resolution using Mullvad coordinates database.
- Added missing Mullvad city coordinates from the official server list (Buenos Aires, Fortaleza, Kansas City, Malmö).
- Added machine-readable JSON status protocol (`--machine-readable` flag) for structured IPC with GUI frontends.
- Added `_run_ping_fallback()` method as automatic fallback when `mtr` is unavailable or broken (e.g. macOS 26 Tahoe). Parses `ping -c N -q` summary for average latency and packet loss.
- Added `mtr_ping_fallback` and `mtr_failed` JSON status events emitted when the MTR step degrades.

### Changed
- Removed OpenVPN mode and simplified speed tests to WireGuard-only flow (Mullvad removed OpenVPN relays in January 2026).
- Removed CLI protocol selection (`--protocol`) and related branching logic.
- Fixed non-interactive behavior so command execution still runs without UI animation.
- Disabled interactive prompts in non-interactive mode.
- Added a deterministic geocoding fallback path using `--default-lat` and `--default-lon`.
- Updated `README.md` examples to use `mullvad_speed_test.py` consistently.
- Reduced `requirements.txt` to runtime dependencies only.
- Added automation flags: `--countdown-seconds` and `--no-open-results`.
- Reorganized project from flat structure to modular package layout.
- Moved all runtime artifacts (logs, DB, cache) to `runtime/` directory to keep root clean.
- Updated paths in code and documentation to reflect new structure.
- Updated CI actions to `actions/checkout@v6` and `actions/setup-python@v6`.
- Enabled GitHub Issues and auto-merge support in repository settings.
- Expanded `CONTINENT_MAPPING` with all Mullvad country codes previously missing: `si`, `sk`, `al`, `hr`, `rs`, `ee`, `bg`, `cy`, `il`, `tr`, `ua`, `lv`, `lt`, `lu`, `is`, `md`, `ba`, `me`, `mk`, `ae`, `qa`, `sa` and others — eliminates "Unknown" continent display for any current Mullvad relay.
- `_run_mtr()` no longer invokes `sudo` directly. Strategy: (1) `mtr` without sudo, (2) `sudo -n mtr` (non-interactive, no prompt), (3) `_run_ping_fallback()`. No password prompt can appear in any code path.
- `calibration_test` JSON status events now include a `continent` field.
- `mtr_running` JSON status is emitted only when `download_speed > 0` (skips non-viable servers).

### Improved
- Reduced CPU load during connection polling by decoupling visual updates (10Hz) from subprocess status checks (2Hz), cutting subprocess spawns by 5×.
- Removed unnecessary spinner thread from server data parsing (instant operation no longer wrapped in threading overhead).
- Replaced O(n²) linear scans in summary tables with O(1) hostname-to-server dict lookups.
- Cached terminal width in `display_manager.py` to eliminate repeated syscalls in tight animation loops.
- Fixed `load_geo_modules` `lru_cache` to no longer key on UI instance (proper cache behavior).
- Wrapped results file handle in try/finally to prevent resource leak on exception.
- Changed bare `except:` to `except Exception:` in connection polling to allow Ctrl+C interruption.
- Added `stdin=subprocess.DEVNULL` to all `subprocess.Popen` and `subprocess.run` calls in `display_manager.py`, preventing any subprocess (including `sudo`) from reading the terminal or blocking on a password prompt.

### Fixed
- Fixed a regression where non-interactive mode could skip command execution (`spinner` and command wrapper were no-op).
- Fixed automation flow to avoid blocking prompts after CLI parsing.
- Added explicit least-privilege workflow permissions in `.github/workflows/ci.yml` (`contents: read`).
- Removed plaintext logging of precise reference location and coordinates in `src/vpn_tools/mullvad_speed_test.py`.
- Enabled required signed commits on protected `main` branch.
- Fixed `sudo mtr` prompting for password when launched from a non-TTY context (GUI app, subprocess pipe). Root cause: missing `stdin=DEVNULL` on all subprocess calls.

### Known Compatibility Issues
- **macOS Homebrew mtr 0.96**: `brew install mtr` sets the SUID bit on `mtr-packet` but leaves it owned by the installing user (not root). When `mtr` spawns `mtr-packet`, the SUID bit forces `euid` to the file owner (non-root), causing `socket(SOCK_RAW)` to fail with `EPERM`. This is not a macOS kernel restriction — raw sockets work fine under root. Fix: `sudo chown root:wheel $(brew --prefix)/Cellar/mtr/0.96/sbin/mtr-packet && sudo chmod 4755 $(brew --prefix)/Cellar/mtr/0.96/sbin/mtr-packet`. The `_run_ping_fallback()` path is triggered automatically when unfixed.

## [2025-09-14]
### Added
- Added `ui/display_manager.py` and migrated terminal UI helpers into a dedicated module.
- Added server coordinate files `coordinates.json` and `coordinates.example.json`.
- Added continent lookup optimizations and consolidated logging helpers.

### Changed
- Major refactor of `mullvad_speed_test.py` with modularized helpers and improved server-selection logic.
- Improved spinner/progress behavior and formatting of server output.
- Updated geolocation and coordinate-cache handling.
- Introduced multiple UI/typing/refactoring improvements via PRs #2 to #32.

### Fixed
- Fixed coordinate loading error handling in `mullvad_coordinates.py`.
- Reverted and reworked server hostname/icon formatting changes for display stability.

## [2025-04-11]
### Changed
- Added RANDOM setting and fixed a deprecation warning in upstream branch history.

## [2025-03-05]
### Added
- Initial repository setup and first Mullvad tester implementation.
- Added base modules: `mullvad_speed_test.py`, `mullvad_coordinates.py`, `README.md`, and `requirements.txt`.
