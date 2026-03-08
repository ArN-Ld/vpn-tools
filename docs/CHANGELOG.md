# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]
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

### Changed
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

### Improved
- Reduced CPU load during connection polling by decoupling visual updates (10Hz) from subprocess status checks (2Hz), cutting subprocess spawns by 5×.
- Removed unnecessary spinner thread from server data parsing (instant operation no longer wrapped in threading overhead).
- Replaced O(n²) linear scans in summary tables with O(1) hostname-to-server dict lookups.
- Cached terminal width in `display_manager.py` to eliminate repeated syscalls in tight animation loops.
- Fixed `load_geo_modules` `lru_cache` to no longer key on UI instance (proper cache behavior).
- Wrapped results file handle in try/finally to prevent resource leak on exception.
- Changed bare `except:` to `except Exception:` in connection polling to allow Ctrl+C interruption.

### Fixed
- Fixed a regression where non-interactive mode could skip command execution (`spinner` and command wrapper were no-op).
- Fixed automation flow to avoid blocking prompts after CLI parsing.
- Added explicit least-privilege workflow permissions in `.github/workflows/ci.yml` (`contents: read`).
- Removed plaintext logging of precise reference location and coordinates in `src/vpn_tools/mullvad_speed_test.py`.
- Enabled required signed commits on protected `main` branch.

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
