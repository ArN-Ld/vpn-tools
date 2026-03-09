# Project Audit (2026-03-08)

## Scope
Deep analysis of architecture, automation reliability, and maintainability for:
- `mullvad_speed_test.py`
- `ui/display_manager.py`
- `mullvad_coordinates.py`
- project docs and dependency files

## Fixes Applied
1. Non-interactive execution reliability:
- `DisplayManager` now keeps execution methods active in non-interactive mode.
- Spinner/command wrappers no longer turn into no-op execution paths.

2. Automation safety:
- Interactive customization and countdown now run only in interactive mode.
- Geocode failure now supports deterministic fallback with `--default-lat` and `--default-lon`.
- In non-interactive mode without fallback coordinates, explicit error is raised instead of hanging prompts.

3. Maintenance hygiene:
- Runtime dependencies split from dev dependencies.
- Runtime artifacts ignored in git.
- Changelog and maintenance process documented.
- CI workflow added for syntax and tests.
- Regression tests added for non-interactive execution and geocode fallback.
- Automation flags added: `--countdown-seconds` and `--no-open-results`.

## High-Value Improvement Axes
1. Add tests for CLI and non-interactive mode:
- unit tests for argument parsing and dependency checks.
- tests for geocode fallback behavior and no-prompt guarantees.
- tests for server selection invariants.

2. Improve error modeling:
- replace broad `except Exception` blocks with targeted exceptions.
- return typed error states where practical.

3. Reduce side effects in constructors:
- `MullvadTester.__init__` currently performs network/database/actions.
- move heavy initialization to explicit `initialize()` for easier testing.

4. Improve command execution abstraction:
- unify subprocess calls (`run_command`, `run_command_with_spinner`, raw `subprocess.*`) behind one adapter.
- centralize timeout and retry policy.

5. Strengthen data persistence:
- add schema versioning/migrations for SQLite.
- add integrity checks and recovery path for corrupted DB/cache.

6. CI/CD baseline:
- add CI workflow for `py_compile`, lint, and tests on pull requests.

## Recommended Next Fixes
1. Extend `tests/` coverage to include command parsing edge-cases and server selection invariants.

2. Introduce a structured config file (`.toml`) for default thresholds and scoring weights.

3. Add lightweight database migration/versioning for schema evolution.

## Risk Areas To Monitor
- External command fragility (`mullvad`, `mtr`, `speedtest-cli`) and parsing assumptions.
  - **mtr 0.96 / macOS Tahoe**: mtr cannot open raw sockets on macOS 26.x even as root. Auto-fallback to `ping` is active. Revisit when Homebrew ships mtr > 0.96.
- Unicode rendering inconsistencies in mixed terminals.
- Long-running commands and timeout behavior under slow systems.
