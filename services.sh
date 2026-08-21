# Copy service to systemd
sudo cp -f /home/earlybird/earlybird-os/deploy/earlybird-kiosk.service /etc/systemd/system/
sudo cp -f /home/earlybird/earlybird-os/deploy/earlybird-server.service /etc/systemd/system/

# Disable first
sudo systemctl disable earlybird-kiosk.service
sudo systemctl disable earlybird-server.service

# Enable service
sudo systemctl enable earlybird-kiosk.service
sudo systemctl enable earlybird-server.service

chmod +x deploy/start-server.sh
chmod +x deploy/start-kiosk.sh

# Reload systemd configuration from disk
sudo systemctl daemon-reload

sudo systemctl restart earlybird-kiosk.service
sudo systemctl restart earlybird-server.service