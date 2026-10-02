#!/usr/bin/env bash
# Commit state/ (or the paths given) if it changed, then push, rebasing onto
# anything pushed meanwhile (the daily brief can commit state/alerts.json
# minutes before a heartbeat).
#
# usage: scripts/commit-state.sh <commit-message-file> [path ...]
set -euo pipefail

msg_file="${1:-}"
shift || true
paths=("${@:-state/}")
branch="${GITHUB_REF_NAME:-main}"

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

git add "${paths[@]}"
if git diff --cached --quiet; then
  echo "${paths[*]} unchanged, nothing to commit"
  exit 0
fi

msg="heartbeat: update state"
if [[ -n "$msg_file" && -s "$msg_file" ]]; then
  msg="$(cat "$msg_file")"
fi
git commit -q -m "$msg"

for attempt in 1 2 3 4 5; do
  if ! git pull -q --rebase origin "$branch"; then
    # Both sides edited the same lines (usually Claude rewrote alerts.json
    # while this run marked an alert fired). Theirs is newer: drop this
    # run's state change. The next run re-checks against the new file.
    git rebase --abort || true
    echo "::warning::${paths[*]} conflicts with a newer commit; this run's change was dropped"
    exit 1
  fi
  if git push -q origin "HEAD:$branch"; then
    echo "pushed: $msg"
    exit 0
  fi
  sleep $((attempt * 2))
done
echo "::error::could not push state after 5 attempts"
exit 1
