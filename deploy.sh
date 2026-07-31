#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${REMOTE_HOST:-infra}"
REMOTE_APP_DIR="${REMOTE_APP_DIR:-/srv/apps/app-portal}"
REMOTE_BRANCH="${REMOTE_BRANCH:-}"
REMOTE_SSH_KEY_PATH="${REMOTE_SSH_KEY_PATH:-}"
SSH_ARGS=(-o BatchMode=yes -o PasswordAuthentication=no)

if [[ -n "$REMOTE_SSH_KEY_PATH" ]]; then
  SSH_ARGS+=(-i "$REMOTE_SSH_KEY_PATH" -o IdentitiesOnly=yes)
fi

git rev-parse --is-inside-work-tree >/dev/null

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Local git working directory is not clean. Commit, stash, or remove changes before deploying." >&2
  git status --short >&2
  exit 1
fi

LOCAL_BRANCH="$(git branch --show-current)"

if [[ -z "$LOCAL_BRANCH" ]]; then
  echo "Cannot deploy from a detached HEAD. Check out a branch first." >&2
  exit 1
fi

REMOTE_BRANCH="${REMOTE_BRANCH:-$LOCAL_BRANCH}"

git push origin "$LOCAL_BRANCH"

ssh "${SSH_ARGS[@]}" "$REMOTE_HOST" "cd '$REMOTE_APP_DIR' && \
  git fetch origin '$REMOTE_BRANCH' && \
  git checkout '$REMOTE_BRANCH' && \
  git pull --ff-only origin '$REMOTE_BRANCH' && \
  docker compose up -d --build --remove-orphans && \
  docker compose ps"
