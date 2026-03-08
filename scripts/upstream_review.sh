#!/usr/bin/env bash
set -euo pipefail

# Quarterly fork-safe upstream review helper.
# This script does not merge anything automatically.

UPSTREAM_REMOTE="${1:-upstream}"
TARGET_BRANCH="${2:-main}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: run this script inside a git repository." >&2
  exit 1
fi

echo "==> Fetching remotes"
git fetch --all --prune

echo
echo "==> Ahead/behind vs ${UPSTREAM_REMOTE}/${TARGET_BRANCH}"
git rev-list --left-right --count HEAD..."${UPSTREAM_REMOTE}/${TARGET_BRANCH}" | awk '{print "ahead=" $1 ", behind=" $2}'

echo
echo "==> Commits you are missing from upstream"
git log --oneline --decorate HEAD.."${UPSTREAM_REMOTE}/${TARGET_BRANCH}" || true

echo
echo "==> Files touched by missing upstream commits"
git diff --name-only HEAD..."${UPSTREAM_REMOTE}/${TARGET_BRANCH}" | sort -u || true

echo
echo "==> Recommendation"
echo "1) Cherry-pick only critical security/bugfix commits on a temp branch."
echo "2) Run tests: python3 -m pytest tests/ -q"
echo "3) Merge temp branch into main only if checks pass."
