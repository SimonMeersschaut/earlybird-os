# Copy service to systemd
sudo cp -f /home/earlybird/earlybird-os/deploy/earlybird-kiosk.service /etc/systemd/system/
sudo cp -f /home/earlybird/earlybird-os/deploy/earlybird-server.service /etc/systemd/system/
sudo cp -f /home/earlybird/earlybird-os/deploy/earlybird-llama.service /etc/systemd/system/

# Disable first
sudo systemctl disable earlybird-kiosk.service
sudo systemctl disable earlybird-server.service
sudo systemctl disable earlybird-llama.service

# Enable service
sudo systemctl enable earlybird-kiosk.service
sudo systemctl enable earlybird-server.service
sudo systemctl enable earlybird-llama.service

chmod +x start-server.sh
chmod +x start-kiosk.sh
chmod +x start-llama.sh

# Reload systemd configuration from disk
./restart.sh