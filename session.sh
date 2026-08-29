#!/usr/bin/env bash

set -euo pipefail

SESSION_NAME="${1:-db}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$ROOT_DIR"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Error: required command not found: %s\n' "$1" >&2
    exit 1
  fi
}

require_directory() {
  if [[ ! -d "$1" ]]; then
    printf 'Error: directory not found: %s\n' "$1" >&2
    exit 1
  fi
}

require_command tmux
require_command nvim
require_command codex

require_directory "$PROJECT_DIR"

# Attach if the session is already running.
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  caffeinate -dims tmux attach-session -t "$SESSION_NAME"
  exit 0
fi

#
# Create the session first.
#
# Window: dev
#
# ┌─────────────────────┬─────────────────────┐
# │                     │ shell               │
# │ Codex               ├─────────────────────┤
# │                     │ knowledge shell     │
# └─────────────────────┴─────────────────────┘
#
caffeinate -dims \
tmux new-session \
  -d \
  -s "$SESSION_NAME" \
  -n "dev" \
  -c "$PROJECT_DIR"

# Start Codex in the left pane.
tmux send-keys \
  -t "$SESSION_NAME:dev.0" \
  "clear" \
  Enter

# Create the top-right shell.
tmux split-window \
  -t "$SESSION_NAME:dev.0" \
  -h \
  -c "$PROJECT_DIR"

tmux send-keys \
  -t "$SESSION_NAME:dev.1" \
  "clear" \
  Enter

# Split the right pane vertically.
tmux split-window \
  -t "$SESSION_NAME:dev.1" \
  -v \
  -c "$PROJECT_DIR"

tmux send-keys \
  -t "$SESSION_NAME:dev.2" \
  "clear" \
  Enter

#
# Window: editor
#

tmux new-window \
  -t "$SESSION_NAME" \
  -n "editor" \
  -c "$PROJECT_DIR"

tmux send-keys \
  -t "$SESSION_NAME:editor.0" \
  "nvim" \
  Enter

#
# Open the dev window with Codex selected.
#

tmux select-window -t "$SESSION_NAME:dev"
tmux select-pane -t "$SESSION_NAME:dev.0"

tmux attach-session -t "$SESSION_NAME"
