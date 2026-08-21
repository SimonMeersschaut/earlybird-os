# Heads-Up
# You must have X11 or Wayland running before Electron will work, even after you install libgbm1.
sudo apt -y install xorg

# Install Libraries
sudo apt update
sudo apt install -y \
  libatk1.0-0 \
  libatk-bridge2.0-0 \
  libgtk-3-0 \
  libnss3 \
  libxss1 \
  libasound2 \
  libgconf-2-4 \
  libxtst6 \
  libx11-xcb1 \
  libgbm1

# Libraries for input drivers (Touch screen)
sudo apt install -y \
  xserver-xorg-input-evdev \
  xserver-xorg-input-libinput


# Install python packages
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

sudo apt install -y unclutter # for hiding the mouse

./services.sh

# sudo usermod -aG tty,video earlybird
# sudo usermod -aG video,input,render,tty earlybird
# sudo dpkg-reconfigure xserver-xorg-legacy # select anybody (for terminal usage)