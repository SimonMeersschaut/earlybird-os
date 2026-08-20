#!/bin/sh
set -eu

until /usr/bin/curl --silent --fail http://127.0.0.1:8000/ >/dev/null; do
    /usr/bin/sleep 1
done

exec /usr/bin/chromium --kiosk --no-first-run --disable-session-crashed-bubble http://localhost:8000/