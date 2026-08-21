#!/bin/sh

echo "Starting server."
. venv/bin/activate
echo "Activated virtual environment."
echo "Starting at http://earlybird:8000/"
/usr/bin/python3 -u /home/earlybird/earlybird-os/run.py --host 127.0.0.1 --port 8000