#!/bin/sh
# Get the absolute path of the script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Launch Terminal with absolute path to executable
osascript -e "tell application \"Terminal\"
    do script quoted form of \"${SCRIPT_DIR}/crystaldba\"
end tell"
