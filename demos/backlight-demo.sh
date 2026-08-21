# Set brightness (0-255)
echo 0 | sudo tee /sys/class/backlight/10-0045/brightness

# Power on
echo 0 | sudo tee /sys/class/backlight/10-0045/bl_power
# Power off
echo 1 | sudo tee /sys/class/backlight/10-0045/bl_power