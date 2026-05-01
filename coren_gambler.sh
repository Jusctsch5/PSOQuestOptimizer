#!/usr/bin/env sh
# Run Coren EV CLI from the repository root (Git Bash / WSL / Unix).
set -e
cd "$(dirname "$0")"
exec python coren_gambler.py "$@"
