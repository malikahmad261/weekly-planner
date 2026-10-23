#!/usr/bin/env bash
# Keep data in step with GitHub.
#
#   scripts/sync.sh start          pull the latest main before reading or changing anything
#   scripts/sync.sh "message"      validate, regenerate views, commit and push to main
#
# Data changes always go straight to main: every session (phone, web,
# scheduled brief) reads from there.
set -uo pipefail
cd "$(dirname "$0")/.."

fetch() {
  for wait in 2 4 8 16; do
    git fetch -q origin main && return 0
    sleep "$wait"
  done
  echo "✗ couldn't reach GitHub" >&2
  return 1
}

if [ "${1:-}" = "start" ]; then
  fetch || exit 1
  git rebase -q --autostash origin/main || { git rebase --abort; echo "✗ local changes conflict with main" >&2; exit 1; }
  echo "✓ up to date with main ($(git log -1 --format=%h))"
  exit 0
fi

msg="${1:?usage: scripts/sync.sh start | scripts/sync.sh \"commit message\"}"
python3 -m planner validate >/dev/null || { python3 -m planner validate; exit 1; }
python3 -m planner views >/dev/null
git add -A config data views
if git diff --cached --quiet; then
  echo "✓ nothing to save"
  exit 0
fi
git commit -q -m "$msg"

for wait in 2 4 8 16; do
  if git push -q origin HEAD:main 2>/dev/null; then
    echo "✓ saved: $msg"
    exit 0
  fi
  fetch || exit 1
  if ! git rebase -q origin/main >/dev/null 2>&1; then
    conflicted=$(git diff --name-only --diff-filter=U)
    if echo "$conflicted" | grep -qv '^views/'; then
      git rebase --abort
      echo "✗ conflict in: $conflicted" >&2
      echo "  Run 'scripts/sync.sh start', re-apply the change, then save again." >&2
      exit 1
    fi
    # views/ are generated: take either side, then rebuild them below.
    git checkout -q --ours -- views/ && git add views/
    GIT_EDITOR=true git rebase --continue >/dev/null || { git rebase --abort; exit 1; }
  fi
  python3 -m planner views >/dev/null
  git add views
  git diff --cached --quiet || git commit -q -m "Regenerate views"
  sleep "$wait"
done
echo "✗ push failed after 4 tries" >&2
exit 1
