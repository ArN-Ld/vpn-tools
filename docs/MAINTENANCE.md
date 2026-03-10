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

## Automated Dependency Updates

Dependabot is configured in `.github/dependabot.yml` to automatically check for updates:
- **Python packages** (requirements.txt, requirements-dev.txt): Checked weekly on Mondays
- **GitHub Actions**: Checked weekly on Mondays

When updates are available, Dependabot creates pull requests automatically with:
- Labels: `dependencies`, `python` or `github-actions`
- Commit prefix: `deps:` for Python, `ci:` for Actions
- Assigned to: ArN-LaB for review

### Reviewing Dependabot PRs
1. Check the changelog/release notes of the updated package
2. Verify CI passes (syntax check + tests)
3. For major version updates, test manually if needed
4. Merge when confident the update is safe

## Repository Governance Baseline

The repository should keep the following settings enabled:
- Branch protection on `main` with required checks (`test`, `Analyze (python)`, `Analyze (actions)`)
- Required pull request review (minimum 1 approval)
- Required conversation resolution
- Enforce admins
- Required signed commits on `main`
- Auto-delete branches on merge
- Auto-merge enabled

Repository contribution scaffolding:
- `.github/CODEOWNERS`
- `.github/ISSUE_TEMPLATE/bug_report.yml`
- `.github/ISSUE_TEMPLATE/feature_request.yml`
- `.github/ISSUE_TEMPLATE/config.yml`
- `.github/pull_request_template.md`

## Quarterly Upstream Review (Fork-Safe)

Goal: stay aware of upstream fixes without forcing destructive merges into a diverged fork.

### Frequency
- Run once per quarter.
- Run immediately for critical upstream security advisories.

### Procedure
1. Update references:
  - `git fetch --all --prune`
2. Measure divergence:
  - `git rev-list --left-right --count HEAD...upstream/main`
3. Inspect missing upstream commits:
  - `git log --oneline HEAD..upstream/main`
  - `git diff --name-only HEAD...upstream/main`
4. Apply only relevant patches on a temporary branch:
  - `git checkout -b upstream-review-YYYYQX`
  - `git cherry-pick <commit_sha>` (security/bugfix only)
5. Validate:
  - `python3 -m py_compile src/vpn_tools/*.py src/vpn_tools/ui/*.py`
  - `python3 -m pytest tests/ -q`
6. Merge to `main` only if validation passes; otherwise drop the temp branch.

### Helper Script
- Use `scripts/upstream_review.sh` for a quick non-destructive review summary.
- Example: `bash scripts/upstream_review.sh upstream main`

---

## Known Compatibility Issues

### mtr ≤ 0.96 — macOS 26 Tahoe (as of 2026-03-09)

**Status**: Active, unresolved upstream.

**Symptom**: `mtr` (and `mtr-packet`) fails to open raw sockets even when invoked as root:
```
mtr-packet: Failure to open IPv4 sockets
mtr-packet: Failure to open IPv6 sockets
mtr: Failure to start mtr-packet: Invalid argument
```

**Affected configuration**:
- macOS 26.x (Tahoe) — `sw_vers ProductVersion: 26.x`
- mtr 0.96 via Homebrew (`brew info mtr` → `0.96`)
- Apple Silicon (M-series) confirmed; Intel status unknown

**Root cause**: Apple changed raw socket privilege handling in the Tahoe kernel. `mtr-packet` can no longer open `AF_INET`/`AF_INET6` raw sockets regardless of effective UID.

**Workaround (current)**: `_run_ping_fallback()` is triggered automatically after both `mtr` and `sudo -n mtr` fail. Uses `ping -c N -q` to measure average latency and packet loss. Hop count is reported as 0 to signal fallback mode to callers.

**Resolution path**:
1. Monitor [mtr releases](https://github.com/traviscross/mtr) — a fix likely requires adopting the `Network Extension` entitlement or switching to `libpcap`.
2. Monitor [Homebrew mtr formula](https://formulae.brew.sh/formula/mtr) for a patched bottle.
3. When a fixed version ships: `brew upgrade mtr`, then verify with:
   ```bash
   mtr -n -c 3 -r 1.1.1.1; echo "exit: $?"   # should exit 0
   ```
