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
chromium-browser --autoplay-policy=no-user-gesture-required --kiosk http://localhost:5000
```