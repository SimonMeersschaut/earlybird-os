#!/bin/sh

# Redirect stdout and stderr so it appears in systemd journal / console
exec 1>&2
set -x

# turn off the backlight
echo 1 | sudo tee /sys/class/backlight/10-0045/bl_power

export DISPLAY=:0
export XAUTHORITY=/home/earlybird/.Xauthority

echo "Checking if the server is online..."
until /usr/bin/curl --silent --fail http://127.0.0.1:8000/ >/dev/null; do
    /usr/bin/sleep 1
    echo "Server not found, retrying..."
done
echo "Server online! Launching Chromium..."

# Hide mouse cursor
unclutter -idle 0 -root &

# Launch Chromium
exec /usr/bin/chromium \
  --no-sandbox \
  --kiosk \
  --incognito \
  --no-first-run \
  --disable-session-crashed-bubble \
  --force-first-run \
  --kiosk-printing \
  --hide-scrollbars \
  --touch-events=enabled \
  http://127.0.0.1:8000/