# Raspberry Pi kiosk startup

Raspberry Pi OS Lite needs an X server before Chromium can run. Install the
runtime packages on the Pi:

```bash
sudo apt update
sudo apt install -y xserver-xorg xinit chromium curl
```

The files in `deploy/` run the Python server on `127.0.0.1:8000` and launch
Chromium full-screen in kiosk mode on the first local console. The included
units use the `earlybird` user and `/home/earlybird/earlybird-os`; edit those
values in both unit files if your username or checkout path differs.

```bash
sudo install -m 0644 deploy/earlybird.service /etc/systemd/system/earlybird.service
sudo install -m 0644 deploy/earlybird-kiosk.service /etc/systemd/system/earlybird-kiosk.service
sudo install -m 0755 deploy/start-kiosk.sh /usr/local/bin/earlybird-start-kiosk

sudo systemctl daemon-reload
sudo systemctl enable --now earlybird.service
sudo systemctl enable --now earlybird-kiosk.service
```

The kiosk service starts X on `tty1`, waits until the local server responds,
and then opens Chromium at `http://127.0.0.1:8000/`. Inspect boot failures with:

```bash
systemctl status earlybird.service earlybird-kiosk.service
journalctl -u earlybird.service -u earlybird-kiosk.service -b
```
# Earlybird OS

Minimal alarm clock UI foundation served by Python's standard library.

## Run locally

```powershell
python run.py
```

The first calendar check authenticates with Google Calendar using `credentials.json` and stores the read-only token in `token.json`. The calendar is refreshed every ten minutes. All-day events are ignored; the first timed event tomorrow determines the alarm.

Open http://127.0.0.1:8000 in a browser. Stop the server with `Ctrl+C`.

Run the focused test suite with:

```powershell
python -m pytest
```

```bash
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
pip install phue
```

```bash
chromium --autoplay-policy=no-user-gesture-required --kiosk http://localhost:8000/
```