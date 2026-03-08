# Maintenance Guide

## Goals
- Keep changes traceable.
- Keep runtime stable in interactive and automation modes.
- Prevent regressions in CLI behavior and output formatting.

## Standard Update Workflow
1. Sync with remote:
   - `git fetch --all --prune`
   - `git checkout main && git pull --ff-only`
2. Create a branch for each logical change.
3. Update documentation and changelog in the same branch.
4. Run validation checks before merge.

## Required Files to Update Per Change
- `docs/CHANGELOG.md`: add an entry under `[Unreleased]`.
- `README.md`: update usage when CLI behavior changes.
- `requirements.txt` / `requirements-dev.txt`: keep runtime and dev deps separated.

## Recommended Validation Commands
- Syntax check:
  - `python -m py_compile mullvad_speed_test.py mullvad_coordinates.py src/vpn_tools/mullvad_speed_test.py src/vpn_tools/mullvad_coordinates.py src/vpn_tools/ui/display_manager.py`
- Lint/type/tests (if configured in environment):
  - `flake8 .`
  - `mypy src/vpn_tools/mullvad_speed_test.py src/vpn_tools/ui/display_manager.py`
  - `pytest -q`

## Release Checklist
1. Move `[Unreleased]` entries in `docs/CHANGELOG.md` to a dated section.
2. Confirm `README.md` examples are executable as written.
3. Verify non-interactive mode:
   - `python mullvad_speed_test.py --non-interactive --location "Paris, France" --default-lat 48.8566 --default-lon 2.3522 --max-servers 1`
4. Tag release and push.

## Logging and Artifacts
- All runtime artifacts are stored in the `runtime/` directory (logs, database, cache).
- The `runtime/` directory is gitignored to keep the repository clean.
- Sample output logs can be kept in docs for documentation purposes if needed.
