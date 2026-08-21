#!/bin/sh

exec 2>&1
set -x

echo "Checking if the server is online."
until /usr/bin/curl --silent --fail http://127.0.0.1:8000/ >/dev/null; do
    /usr/bin/sleep 1
    echo "Server not found."
done
echo "Server found. Starting webbrowser"

# exec /usr/bin/chromium --kiosk --no-first-run --disable-session-crashed-bubble http://localhost:8000/
unclutter -idle 0 -root &
exec /usr/bin/chromium --no-sandbox --kiosk --incognito --no-first-run --disable-session-crashed-bubble --force-first-run --kiosk-printing --hide-scrollbars --touch-events=enabled http://localhost:8000/