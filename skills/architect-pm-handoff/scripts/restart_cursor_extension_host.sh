#!/bin/zsh
set -euo pipefail

if [[ "${1:-}" == "--dry-run" ]]; then
  print "Would invoke Cursor command: Developer: Restart Extension Host"
  exit 0
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  print -u2 "Automatic Extension Host recovery is supported only on macOS."
  exit 2
fi

if ! pgrep -x "Cursor" >/dev/null 2>&1; then
  print -u2 "Cursor is not running; cannot restart its Extension Host."
  exit 3
fi

osascript <<'APPLESCRIPT'
tell application "Cursor" to activate
delay 0.5
tell application "System Events"
  keystroke "p" using {command down, shift down}
  delay 0.5
  keystroke "Developer: Restart Extension Host"
  delay 0.8
  key code 36
end tell
APPLESCRIPT

# Give the replacement Extension Host time to initialize before probing it.
sleep 6

